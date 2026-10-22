"""The C++ harness and the Judge0 client.

Shared by the scripts in this folder. The harness is the same one the API
uses: the problem's stored `prefix`, the user's function, and the problem's
stored `suffix` — which runs every case and prints the result after a marker.
"""

import base64
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
DATA_FILE = ROOT / "supabase" / "seed" / "problems.json"

#: Marks the boundary between one case's output and the next, so a single run
#: carrying every case can be split apart again.
CASE_MARKER = "___CASE___"

JUDGE0_URL = "https://ce.judge0.com/submissions"
LANGUAGE_CXX = 54


def load() -> list[dict]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save(problems: list[dict]) -> None:
    DATA_FILE.write_text(json.dumps(problems, indent=2, ensure_ascii=False), encoding="utf-8")


def run(source: str, timeout: int = 60) -> tuple[int, str, str]:
    """Compile and run a program. Returns `(status_id, stdout, stderr)`.

    The local compiler is used when there is one, because the public Judge0
    instance takes thirty seconds a run and drops connections often. That is
    far too slow for measuring thousands of test cases. `run_judge0` forces
    the other path, and the two must agree: the catalogue's stored expected
    outputs are what Judge0 will produce when a user submits against them.
    """
    if Path(LOCAL_CXX).exists():
        return run_local(source, timeout)
    return run_judge0(source, timeout)


def run_judge0(source: str, timeout: int = 60, attempts: int = 4) -> tuple[int, str, str]:
    """Compile and run on Judge0. Returns `(status_id, stdout, stderr)`.

    Base64 because a submission can carry any character: Judge0 answers HTTP
    400 "cannot be converted to UTF-8" on the plain path, which is
    indistinguishable from a real failure.

    The public instance is shared and drops connections now and then, so a
    dropped connection is retried rather than taken as a failure. A run that
    never answers raises.
    """

    body = {
        "source_code": base64.b64encode(source.encode("utf-8")).decode("ascii"),
        "language_id": LANGUAGE_CXX,
        "stdin": base64.b64encode(b"").decode("ascii"),
    }

    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            import httpx

            response = httpx.post(
                JUDGE0_URL,
                params={"base64_encoded": "true", "wait": "true"},
                json=body,
                timeout=timeout,
            )
        except httpx.HTTPError as error:
            last_error = error
            time.sleep(1.5 * (attempt + 1))
            continue

        if response.status_code != 200:
            raise RuntimeError(
                f"Judge0 answered {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        status_id = data.get("status", {}).get("id")
        if not isinstance(status_id, int):
            raise RuntimeError("Judge0 returned something unexpected.")

        return status_id, _field(data, "stdout"), (
            _field(data, "stderr") or _field(data, "compile_output")
        )

    raise RuntimeError(f"Judge0 kept dropping the connection: {last_error}")


def _field(data: dict, name: str) -> str:
    """One field of a Judge0 answer, decoded if it was encoded."""
    value = data.get(name)
    if not value:
        return ""
    try:
        return base64.b64decode(value, validate=True).decode("utf-8", "replace")
    except (ValueError, UnicodeDecodeError):
        return value


def split_outputs(stdout: str) -> list[str]:
    """One entry per case, in order."""
    if CASE_MARKER not in stdout:
        return []
    return [part.strip() for part in stdout.split(CASE_MARKER)[1:]]


#: A local C++ compiler, used to measure expected outputs while a catalogue is
#: being built. The public Judge0 instance takes thirty seconds a run and
#: drops the connection often, which is far too slow for measuring thousands
#: of cases.
LOCAL_CXX = os.environ.get("RESOLVE_CXX", r"C:\w64devkit\bin\g++.exe")


def run_local(source: str, timeout: int = 60) -> tuple[int, str, str]:
    """Compile and run on this machine. Returns `(status_id, stdout, stderr)`.

    The status ids are Judge0's, so the two paths can be swapped freely:
    `3` is Accepted, `6` is a compilation error and `11` is a runtime error.
    """
    if not LOCAL_CXX or not Path(LOCAL_CXX).exists():
        raise RuntimeError(f"No local C++ compiler at {LOCAL_CXX!r}")

    with tempfile.TemporaryDirectory() as folder:
        source_path = Path(folder) / "main.cpp"
        binary_path = Path(folder) / "main.exe"
        source_path.write_text(source, encoding="utf-8")

        compile_result = subprocess.run(
            [
                LOCAL_CXX,
                "-std=c++17",
                "-O1",
                "-w",
                "-o",
                str(binary_path),
                str(source_path),
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if compile_result.returncode != 0:
            return 6, "", compile_result.stderr[:4000]

        try:
            run_result = subprocess.run(
                [str(binary_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return 5, "", "timed out"

        if run_result.returncode != 0:
            return 11, run_result.stdout, run_result.stderr[:4000]
        return 3, run_result.stdout, run_result.stderr
def program_for(problem: dict, cases: list[list[str]]) -> str:
    """The program that runs `cases` against the problem's reference solution.

    `cases` is a list of argument lists. When they are given, the suffix is
    rebuilt from them, so a case can be measured before it is stored.
    """
    if cases:
        suffix = build_suffix(
            problem["signature"],
            problem["params"],
            cases,
            problem.get("print_param"),
        )
    else:
        suffix = problem["suffix"]
    return f"{problem['prefix']}\n{problem['reference_solution']}\n{suffix}"


def build_prefix(structs: list[str] | None = None) -> str:
    """The C++ that goes before the user's function.

    `structs` names the node types the problem uses — `ListNode`, `TreeNode` —
    and the matching definitions, builders and printers are added. Without them
    a linked-list or tree problem cannot be expressed at all: there is no
    brace form that builds a list from `{1,2,3}`.
    """
    extra = ""
    for name in structs or []:
        extra += STRUCTS.get(name, "")

    return f"""#include <bits/stdc++.h>
using namespace std;
{extra}{PRINT_HELPERS}"""


def build_suffix(
    signature: str,
    params: list,
    cases: list[list[str]],
    print_param: str | None = None,
) -> str:
    """The C++ that goes after the user's function.

    A parameter that is a node pointer is built from a plain list of values:
    `ListNode*` from `{1,2,3}` and `TreeNode*` from a level order list where
    `null` marks an absent child. The list stays readable in the test case
    table, and the C++ that builds it is hidden in here.
    """
    name = signature.split("(")[0].split()[-1]
    blocks = []
    for i, case in enumerate(cases):
        decls = []
        for j, arg in enumerate(case):
            kind = params[j][0]
            decls.append(f"    {kind} p{i}_{j} = {argument_for(kind, arg)};")
        call = f"{name}(" + ", ".join(f"p{i}_{j}" for j in range(len(params))) + ")"
        if print_param:
            idx = [p[1] for p in params].index(print_param)
            body = f"        {call};\n        __print(p{i}_{idx});"
        else:
            body = f"        auto __r = {call};\n        __print(__r);"
        blocks.append(
            "    {\n"
            f"{chr(10).join(decls)}\n"
            f'        std::cout << "{CASE_MARKER}" << std::endl;\n'
            f"{body}\n"
            '        std::cout << std::endl;\n'
            "    }\n"
        )
    return f"""
int main() {{
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

{''.join(blocks)}
    return 0;
}}
"""


def argument_for(kind: str, arg: str) -> str:
    """The C++ expression that builds one argument.

    A node pointer is built by a helper, so the test case can just hold the
    values. A tree's absent child is written `null` in the test case and
    becomes the sentinel the builder knows about.
    """
    if kind == "ListNode*":
        return f"__mklist({arg})"
    if kind == "TreeNode*":
        return f"__mktree({arg.replace('null', '__NULL')})"
    return arg


PRINT_HELPERS = """
// A string prints with its quotes, so `[""]` is not the same as `[]`.
inline void __print(const std::string& value) { std::cout << '"' << value << '"'; }

// A bool prints as true/false, not 1/0: the statements say "Output: true",
// and a test case that disagrees with its own statement is worse than useless.
inline void __print(bool value) { std::cout << (value ? "true" : "false"); }

// A double keeps a decimal point, so a median of 2 shows as "2.0" and not "2".
inline void __print(double value) {
    std::ostringstream out;
    out << std::setprecision(12) << value;
    std::string text = out.str();
    if (text.find('.') == std::string::npos && text.find('e') == std::string::npos) {
        text += ".0";
    }
    std::cout << text;
}

template <typename T>
void __print(const T& value) { std::cout << value; }
template <typename T>
void __print(const std::vector<T>& v) {
    std::cout << "[";
    for (size_t i = 0; i < v.size(); ++i) {
        if (i) std::cout << ",";
        __print(v[i]);
    }
    std::cout << "]";
}
"""

#: The node types a problem can use, with the code that makes them expressible
#: in a test case.
#:
#: A linked list is written as a flat list of values. A tree is written in
#: level order, the way LeetCode serialises one, with `__NULL` marking an
#: absent child.
STRUCTS = {
    "ListNode": """
struct ListNode {
    int val;
    ListNode* next;
    ListNode(int v) : val(v), next(nullptr) {}
};

// Builds a list from a flat list of values.
static ListNode* __mklist(const std::vector<int>& v) {
    ListNode* head = nullptr;
    ListNode* tail = nullptr;
    for (int x : v) {
        if (!head) { head = tail = new ListNode(x); }
        else { tail->next = new ListNode(x); tail = tail->next; }
    }
    return head;
}

// Prints a list the way the statement shows it.
inline void __print(const ListNode* n) {
    std::cout << "[";
    for (const ListNode* p = n; p; p = p->next) {
        if (p != n) std::cout << ",";
        std::cout << p->val;
    }
    std::cout << "]";
}
// A pointer overload, so the template below never wins and prints an address.
inline void __print(ListNode* n) { __print((const ListNode*)n); }
""",
    "TreeNode": """
// The value that marks an absent child in a level-order tree literal.
const int __NULL = -1000000000;

struct TreeNode {
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int v) : val(v), left(nullptr), right(nullptr) {}
};

// Builds a tree from its level order. __NULL marks an absent child.
static TreeNode* __mktree(const std::vector<int>& v) {
    if (v.empty() || v[0] == __NULL) return nullptr;
    std::vector<TreeNode*> nodes;
    for (int x : v) {
        nodes.push_back(x == __NULL ? nullptr : new TreeNode(x));
    }
    for (size_t i = 0; i < nodes.size(); ++i) {
        if (!nodes[i]) continue;
        size_t left = 2 * i + 1;
        size_t right = 2 * i + 2;
        if (left < nodes.size()) nodes[i]->left = nodes[left];
        if (right < nodes.size()) nodes[i]->right = nodes[right];
    }
    return nodes[0];
}

// Prints a tree in level order, the way the statement shows it.
inline void __print(const TreeNode* n) {
    if (!n) { std::cout << "[]"; return; }
    std::vector<const TreeNode*> level{n};
    std::cout << "[";
    bool first = true;
    while (!level.empty()) {
        std::vector<const TreeNode*> next;
        for (const TreeNode* p : level) {
            if (!first) std::cout << ",";
            first = false;
            if (!p) { std::cout << "null"; next.push_back(nullptr); continue; }
            std::cout << p->val;
            next.push_back(p->left);
            next.push_back(p->right);
        }
        // A trailing row of nothing is not worth printing.
        bool any = false;
        for (const TreeNode* p : next) if (p) { any = true; break; }
        level = any ? next : std::vector<const TreeNode*>();
    }
    std::cout << "]";
}
// A pointer overload, so the template below never wins and prints an address.
inline void __print(TreeNode* n) { __print((const TreeNode*)n); }
""",
}

#: The value that marks an absent child in a level-order tree literal.
NULL_MARKER = -1000000000
