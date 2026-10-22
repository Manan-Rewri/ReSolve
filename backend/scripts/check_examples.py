"""Check the reference solutions against the worked examples in the statements.

Each problem's statement carries examples of the form:

    Input:  nums = [2, 7, 11, 15], target = 9
    Output: [0, 1]

The example is the ground truth. If the reference solution does not reproduce
it, then either the reference or the example is wrong, and the stored expected
outputs — which are measured from the reference — are wrong too.

This is the check that matters. The rest of the pipeline agrees with itself by
construction; this one compares against something written by hand.

    .\\.venv\\Scripts\\python.exe scripts\\check_examples.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import load, program_for, run, split_outputs


def split_top_level(text: str) -> list[str]:
    """Split on commas that are not inside brackets or quotes."""
    parts, depth, quoted, current = [], 0, False, []
    for ch in text:
        if ch == '"':
            quoted = not quoted
        elif not quoted and ch in "[{(":
            depth += 1
        elif not quoted and ch in "]})":
            depth -= 1
        if ch == "," and depth == 0 and not quoted:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def to_cpp_value(value: str, type_text: str) -> str:
    """Turn a human-written example value into a C++ initialiser."""
    value = value.strip()
    base = type_text.replace("&", "").strip()

    def quote(item: str, inner: str) -> str:
        item = item.strip()
        if inner == "string":
            return item if item.startswith('"') else f'"{item}"'
        if inner == "char":
            if len(item) >= 2 and item[0] in "\"'" and item[-1] == item[0]:
                item = item[1:-1]
            return f"'{item}'"
        return item

    if base == "vector<vector<char>>" and value.startswith("[") and value.endswith("]"):
        # A grid of characters is written two ways: as rows of quoted
        # characters (["A","B"]) or as rows of a plain string ("+.."). This
        # has to come before the general vector case, which would take the
        # rows as they are.
        rows = split_top_level(value[1:-1])
        built = []
        for row in rows:
            row = row.strip()
            if row.startswith("[") and row.endswith("]"):
                chars = []
                for item in split_top_level(row[1:-1]):
                    item = item.strip()
                    if len(item) >= 2 and item[0] in "\"'" and item[-1] == item[0]:
                        item = item[1:-1]
                    chars.append(f"'{item}'")
                built.append("{" + ",".join(chars) + "}")
            else:
                if len(row) >= 2 and row[0] in "\"'" and row[-1] == row[0]:
                    row = row[1:-1]
                built.append("{" + ",".join(f"'{c}'" for c in row) + "}")
        return "{" + ",".join(built) + "}"

    if base.startswith("vector<"):
        inner = base[len("vector<") : -1]
        if value.startswith("[") and value.endswith("]"):
            if inner.startswith("vector<"):
                rows = split_top_level(value[1:-1])
                return (
                    "{"
                    + ",".join(
                        to_cpp_value(r, inner) if r.startswith("[") else r for r in rows
                    )
                    + "}"
                )
            items = split_top_level(value[1:-1])
            return "{" + ",".join(quote(i, inner) for i in items) + "}"

    if base.endswith("*") and value.startswith("[") and value.endswith("]"):
        # A node pointer takes the list of its values: [1,2,3].
        items = split_top_level(value[1:-1])
        return "{" + ",".join(items) + "}"
    return value


def args_from_example(example_input: str, params: list) -> list[str]:
    """`nums = [2, 7], target = 9` -> ('{2,7}', '9'), in parameter order."""
    parts = split_top_level(example_input)
    named = {}
    for part in parts:
        if "=" in part:
            name, value = part.split("=", 1)
            named[name.strip()] = value.strip()

    args = []
    for index, (type_text, param_name) in enumerate(params):
        if param_name in named:
            args.append(to_cpp_value(named[param_name], type_text))
        else:
            args.append(to_cpp_value(parts[index], type_text))
    return args


def normalise(text: str) -> str:
    """Compare loosely: whitespace and brackets do not matter."""
    return re.sub(r"\s+", "", text or "").strip("[]")


def main() -> None:
    problems = load()
    checked = 0
    failures = []

    for problem in problems:
        params = [tuple(x) for x in problem["params"]]
        for number, example in enumerate(problem["examples"], 1):
            try:
                args = args_from_example(example["input"], params)
            except Exception as exc:
                failures.append((problem["slug"], f"example {number}: cannot parse ({exc})"))
                continue

            status_id, stdout, stderr = run(program_for(problem, [args]))
            if status_id != 3:
                failures.append((problem["slug"], f"example {number}: {stderr[:200]}"))
                continue

            outputs = split_outputs(stdout)
            if not outputs:
                failures.append((problem["slug"], f"example {number}: no output"))
                continue

            checked += 1
            if normalise(outputs[0]) != normalise(example["output"]):
                failures.append(
                    (
                        problem["slug"],
                        f"example {number}: statement says {example['output']!r}, "
                        f"reference says {outputs[0]!r}",
                    )
                )

    print(f"{checked} worked examples checked against the reference solutions")
    if failures:
        print(f"\n{len(failures)} MISMATCH:")
        for slug, why in failures:
            print(f"  {slug}: {why}")
        sys.exit(1)
    print("every example agrees with its reference solution")


if __name__ == "__main__":
    main()
