"""Turn a LeetCode stub into a complete, runnable program.

LeetCode hands out a stub containing only the class and the method signature:

    class Solution {
    public:
        vector<int> twoSum(vector<int>& nums, int target) {

        }
    };

That cannot run on its own - there is no main(). This module reads the
signature, works out what each parameter and the return value are, and appends a
driver that reads your Standard input, calls your method and prints the result
the way LeetCode formats it.

Only a limited set of types is supported. Anything outside it yields no starter
at all, so the caller falls back to a generic template rather than emitting code
that would not compile.

The same signature knowledge is used to turn LeetCode's labelled examples
(`nums = [2,7,11,15], target = 9`) into the raw Standard input the driver reads.
That has to happen here, not in the browser: a generic strip of brackets and
quotes would destroy string parameters such as s = "()[]{}".
"""
import re
from typing import Dict, List, NamedTuple, Optional, Tuple

# Supported type categories. A signature is only usable when every parameter and
# the return value map to one of these.
INT = "int"
DOUBLE = "double"
STRING = "string"
INT_VECTOR = "int_vector"
STRING_VECTOR = "string_vector"
CHAR_VECTOR = "char_vector"
BOOL = "bool"
VOID = "void"

CPP_TYPE_MAP = {
    "int": INT,
    "long long": INT,
    "double": DOUBLE,
    "float": DOUBLE,
    "string": STRING,
    "bool": BOOL,
    "void": VOID,
    "vector<int>": INT_VECTOR,
    "vector<string>": STRING_VECTOR,
    "vector<char>": CHAR_VECTOR,
}

# Python 3.9+ spells generic types list[int]; Judge0 runs Python 3.8, where that
# is a TypeError at import time. Snippets are rewritten to typing.List before
# anything else looks at them.
PYTHON_ANNOTATION_FIXES = (
    (re.compile(r"\blist\[(\w+)\]"), r"List[\1]"),
    (re.compile(r"\bOptional\[(\w+)\]"), r"Optional[\1]"),
    (re.compile(r"(\w+)\s*\|\s*None"), r"Optional[\1]"),
)

PYTHON_TYPE_MAP = {
    "int": INT,
    "float": DOUBLE,
    "str": STRING,
    "bool": BOOL,
    "None": VOID,
    "List[int]": INT_VECTOR,
    "List[str]": STRING_VECTOR,
    "List[chr]": STRING_VECTOR,
    "List": STRING_VECTOR,
}

CPP_SIGNATURE = re.compile(
    r"(?P<ret>[\w:]+(?:\s*<[^>]*>)?)\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)\s*\{",
    re.DOTALL,
)

PY_SIGNATURE = re.compile(
    r"def\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)\s*(?:->\s*(?P<ret>[^:]+))?:",
    re.DOTALL,
)

CPP_HEADER = "#include <bits/stdc++.h>\nusing namespace std;\n"

DRIVER_BANNER = "// ---- ReSolve driver: reads Standard input, calls your method ----"
PY_DRIVER_BANNER = "# ---- ReSolve driver: reads Standard input, calls your method ----"

# LeetCode ships an empty method body. Left as is, a C++ function declared to
# return a value has no return statement, so the driver reads uninitialised
# memory and prints garbage; a Python def whose suite is only whitespace is an
# IndentationError. These placeholders keep an untouched starter deterministic,
# and the user overwrites them with their own body.
CPP_PLACEHOLDER_RETURN = {
    INT_VECTOR: "{}",
    STRING_VECTOR: "{}",
    STRING: '""',
    BOOL: "false",
    INT: "0",
    DOUBLE: "0.0",
}

PYTHON_PLACEHOLDER_RETURN = {
    INT_VECTOR: "return []",
    STRING_VECTOR: "return []",
    STRING: 'return ""',
    BOOL: "return False",
    INT: "return 0",
    DOUBLE: "return 0.0",
}


class Parameter(NamedTuple):
    name: str
    kind: Optional[str]


class Signature(NamedTuple):
    method: str
    parameters: List[Parameter]
    returns: Optional[str]

    @property
    def supported(self) -> bool:
        if self.returns is None:
            return False
        return all(p.kind is not None for p in self.parameters)


class Starter(NamedTuple):
    """A runnable program plus the signature that shaped it."""

    code: str
    signature: Signature


def _normalise_type(raw: str) -> str:
    """Strips const/reference/pointer noise so types can be looked up."""
    cleaned = re.sub(r"\bconst\b", " ", raw.strip())
    cleaned = cleaned.replace("&", " ").replace("*", " ")
    return " ".join(cleaned.split())


def normalise_python_snippet(snippet: str) -> str:
    for pattern, replacement in PYTHON_ANNOTATION_FIXES:
        snippet = pattern.sub(replacement, snippet)
    return snippet


def parse_cpp_signature(code: str) -> Optional[Signature]:
    match = CPP_SIGNATURE.search(code)
    if not match:
        return None

    returns = CPP_TYPE_MAP.get(_normalise_type(match.group("ret")))
    parameters: List[Parameter] = []

    for chunk in match.group("params").strip().split(","):
        if not chunk.strip():
            continue
        parts = chunk.strip().split()
        if len(parts) < 2:
            return None
        param_type, param_name = " ".join(parts[:-1]), parts[-1]
        parameters.append(
            Parameter(param_name.lstrip("*&"), CPP_TYPE_MAP.get(_normalise_type(param_type)))
        )

    return Signature(match.group("name"), parameters, returns)


def parse_python_signature(code: str) -> Optional[Signature]:
    match = PY_SIGNATURE.search(normalise_python_snippet(code))
    if not match:
        return None

    returns = PYTHON_TYPE_MAP.get(_normalise_type(match.group("ret") or "None"))
    parameters: List[Parameter] = []

    for chunk in match.group("params").strip().split(","):
        if not chunk.strip() or chunk.strip().startswith("self"):
            continue
        if ":" not in chunk:
            return None
        # Python writes "name: Type", so the name comes first.
        param_name, annotation = chunk.split(":", 1)
        parameters.append(
            Parameter(param_name.strip(), PYTHON_TYPE_MAP.get(_normalise_type(annotation)))
        )

    return Signature(match.group("name"), parameters, returns)


def _fill_cpp_body(code: str, signature: Signature) -> str:
    """Replaces an empty stub body with a placeholder return statement."""
    placeholder = CPP_PLACEHOLDER_RETURN.get(signature.returns)
    match = CPP_SIGNATURE.search(code)
    if not placeholder or not match:
        return code

    body_start = code.index("{", match.end() - 1) + 1
    depth, index = 1, body_start
    while index < len(code) and depth:
        if code[index] == "{":
            depth += 1
        elif code[index] == "}":
            depth -= 1
            if depth == 0:
                break
        index += 1

    body = code[body_start:index]
    if body.strip():
        return code
    # Indent relative to the line the method signature started on, not to the
    # trailing whitespace, which LeetCode pads inconsistently.
    signature_indent = len(code[: match.start()].rsplit("\n", 1)[-1])
    indent = " " * (signature_indent + 4)
    return f"{code[:body_start]}\n{indent}return {placeholder};{body}{code[index:]}"


def _fill_python_body(code: str, signature: Signature) -> str:
    """Replaces an empty stub body so the module still parses."""
    match = PY_SIGNATURE.search(code)
    if not match:
        return code

    line_end = code.find("\n", match.end())
    line_end = len(code) if line_end == -1 else line_end

    # Leave a real body alone; only fill when just whitespace follows.
    following = code[line_end:].strip()
    if following and not following.startswith(("#", "def ", "@", "class ")):
        return code

    def_indent = len(code[: match.start()].rsplit("\n", 1)[-1])
    placeholder = PYTHON_PLACEHOLDER_RETURN.get(signature.returns, "pass")
    return f"{code[:line_end]}\n{' ' * (def_indent + 4)}{placeholder}{code[line_end:]}"


def _cpp_read_statements(signature: Signature) -> str:
    """One read statement per parameter, in signature order (one input line each)."""
    lines = ["    string line;"]
    for param in signature.parameters:
        if param.kind in (INT_VECTOR, STRING_VECTOR, CHAR_VECTOR):
            element = {INT_VECTOR: "int", STRING_VECTOR: "string", CHAR_VECTOR: "char"}[
                param.kind
            ]
            lines += [
                f"    vector<{element}> {param.name};",
                "    if (!getline(cin, line)) return 0;",
                "    {",
                "        istringstream values(line);",
                f"        {element} value;",
                "        while (values >> value)",
                f"            {param.name}.push_back(value);",
                "    }",
            ]
        elif param.kind == STRING:
            lines += [
                f"    string {param.name};",
                "    if (!getline(cin, line)) return 0;",
                # LeetCode examples quote strings; strip it so s = "abc" works.
                f'    {param.name} = line;',
                "    if ({0}.size() >= 2 && {0}.front() == '\"' && {0}.back() == '\"')".format(
                    param.name
                ),
                f"        {param.name} = {param.name}.substr(1, {param.name}.size() - 2);",
            ]
        else:
            kind = "double" if param.kind == DOUBLE else "int"
            lines += [
                f"    {kind} {param.name} = 0;",
                f"    if (getline(cin, line)) {{ istringstream v(line); v >> {param.name}; }}",
            ]
    return "\n".join(lines)


def _cpp_print_statement(signature: Signature, expression: str) -> str:
    # `expression` is bound to a variable first: inlining it into a loop would
    # call the user's method once per element, and methods that mutate their
    # argument (plusOne, removeDuplicates) would give wrong answers.
    result = "result"
    declare = f"    auto {result} = {expression};"
    if signature.returns in (INT_VECTOR, STRING_VECTOR, CHAR_VECTOR):
        return (
            f"{declare}\n"
            f"    for (size_t i = 0; i < {result}.size(); ++i) {{\n"
            "        if (i) cout << ' ';\n"
            f"        cout << {result}[i];\n"
            "    }\n"
            "    cout << '\\n';"
        )
    if signature.returns == STRING:
        return f"{declare}\n    cout << {result} << '\\n';"
    if signature.returns == BOOL:
        # Matches LeetCode, which prints true/false rather than 1/0.
        return f"{declare}\n    cout << ({result} ? \"true\" : \"false\") << '\\n';"
    if signature.returns == VOID:
        return f"    {expression};"
    return f"{declare}\n    cout << {result} << '\\n';"


def build_cpp_starter(snippet: str) -> Optional[Starter]:
    signature = parse_cpp_signature(snippet)
    if not signature or not signature.supported:
        return None

    arguments = ", ".join(p.name for p in signature.parameters)
    call = f"Solution().{signature.method}({arguments})"
    driver = "\n".join(
        [
            DRIVER_BANNER,
            "int main() {",
            "    ios::sync_with_stdio(false);",
            "    cin.tie(nullptr);",
            "",
            _cpp_read_statements(signature),
            "",
            _cpp_print_statement(signature, call),
            "    return 0;",
            "}",
            "",
        ]
    )
    body = _fill_cpp_body(snippet, signature)
    return Starter(f"{CPP_HEADER}\n{body.rstrip()}\n\n{driver}", signature)


def _python_read_statements(signature: Signature) -> List[str]:
    statements = ["lines = sys.stdin.read().splitlines()"]
    for index, param in enumerate(signature.parameters):
        # Parenthesised: without them `.split()` would bind to the else branch.
        line = f"(lines[{index}] if len(lines) > {index} else '')"
        if param.kind == INT_VECTOR:
            statements.append(f"{param.name} = list(map(int, {line}.split()))")
        elif param.kind in (STRING_VECTOR, CHAR_VECTOR):
            statements.append(f"{param.name} = list({line}.split())")
        elif param.kind == STRING:
            statements.append(f"{param.name} = {line}.strip().strip('\"').strip(\"'\")")
        elif param.kind == DOUBLE:
            statements.append(f"{param.name} = float({line})")
        else:
            statements.append(f"{param.name} = int({line})")
    return statements


def _python_print_statement(signature: Signature, expression: str) -> str:
    if signature.returns in (INT_VECTOR, STRING_VECTOR, CHAR_VECTOR):
        return f'print(" ".join(str(x) for x in {expression}))'
    if signature.returns == BOOL:
        # Matches LeetCode, which prints true/false rather than True/False.
        return f'print("true" if {expression} else "false")'
    if signature.returns == VOID:
        return expression
    return f"print({expression})"


def build_python_starter(snippet: str) -> Optional[Starter]:
    snippet = normalise_python_snippet(snippet)
    signature = parse_python_signature(snippet)
    if not signature or not signature.supported:
        return None

    arguments = ", ".join(p.name for p in signature.parameters)
    call = f"Solution().{signature.method}({arguments})"

    imports = ""
    if re.search(r"\b(List|Optional)\[", snippet):
        imports = "from typing import List, Optional\n\n\n"

    driver = "\n".join(
        [
            PY_DRIVER_BANNER,
            'if __name__ == "__main__":',
            "    import sys",
            "",
            *[f"    {line}" for line in _python_read_statements(signature)],
            "",
            f"    {_python_print_statement(signature, call)}",
            "",
        ]
    )
    body = _fill_python_body(snippet, signature)
    return Starter(f"{imports}{body.rstrip()}\n\n{driver}", signature)


BUILDERS = {"cpp": build_cpp_starter, "python": build_python_starter}

# LeetCode publishes two Python stubs; prefer the modern-annotation one.
PYTHON_SOURCE_ALIASES = ("python3", "python")


def build_starters(snippets: Dict[str, str]) -> Dict[str, Starter]:
    """Builds a runnable starter per supported language, skipping the rest.

    Keys are ReSolve language ids, so LeetCode's "python3" is stored as "python".
    """
    snippets = snippets or {}
    sources = {
        "cpp": [snippets.get("cpp")],
        "python": [snippets.get(alias) for alias in PYTHON_SOURCE_ALIASES],
    }

    starters: Dict[str, Starter] = {}
    for lang_slug, builder in BUILDERS.items():
        source = next((value for value in sources[lang_slug] if value), None)
        if not source:
            continue
        try:
            built = builder(source)
        except Exception:
            built = None
        if built:
            starters[lang_slug] = built
    return starters


def _split_assignments(example_input: str) -> List[Tuple[str, str]]:
    """Splits 'a = [1,2], b = 3' into [('a', '[1,2]'), ('b', '3')].

    Commas inside brackets or quotes do not separate assignments.
    """
    parts, depth, quoted, current = [], 0, False, ""
    for char in example_input:
        if char in "\"'":
            quoted = not quoted
        elif not quoted and char in "[{(":
            depth += 1
        elif not quoted and char in "]})":
            depth -= 1
        if char == "," and not quoted and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    parts.append(current)

    assignments = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        name, separator, value = part.partition("=")
        assignments.append((name.strip(), value.strip()) if separator else ("", part))
    return assignments


def _format_value(kind: Optional[str], raw: str) -> Optional[str]:
    """Renders one LeetCode literal in the layout the driver reads."""
    value = raw.strip()
    if kind in (INT_VECTOR, STRING_VECTOR, CHAR_VECTOR):
        inner = value.strip("[]()").strip()
        if not inner:
            return ""
        items = [item.strip().strip("\"'") for item in inner.split(",")]
        return " ".join(item for item in items if item)
    if kind == STRING:
        # Brackets and braces are meaningful inside a string, so only the
        # surrounding quotes come off.
        return value.strip().strip("\"'")
    if kind in (INT, DOUBLE, BOOL):
        cleaned = value.strip().strip("[]()").strip().strip("\"'")
        return cleaned or ("0" if kind != BOOL else "false")
    return None


def example_to_stdin(example_input: str, signature: Signature) -> Optional[str]:
    """Converts one labelled LeetCode example into raw driver input.

    Returns None when the example cannot be mapped onto the parameters, so the
    caller can fall back rather than feed the driver something wrong.
    """
    assignments = dict(_split_assignments(example_input or ""))
    if not assignments:
        return None

    lines = []
    for index, param in enumerate(signature.parameters):
        raw = assignments.get(param.name)
        if raw is None and index < len(assignments):
            raw = list(assignments.values())[index]
        if raw is None:
            return None
        formatted = _format_value(param.kind, raw)
        if formatted is None:
            return None
        lines.append(formatted)
    return "\n".join(lines)
