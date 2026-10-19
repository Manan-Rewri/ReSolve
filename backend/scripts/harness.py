"""The C++ harness and the Judge0 client.

Shared by the scripts in this folder. The harness is the same one the API
uses: the problem's stored `prefix`, the user's function, and the problem's
stored `suffix` — which runs every case and prints the result after a marker.
"""

import base64
import json
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
DATA_FILE = BACKEND / "data" / "problems.json"

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
    """Compile and run on Judge0. Returns `(status_id, stdout, stderr)`.

    Base64 because a submission can carry any character: Judge0 answers HTTP
    400 "cannot be converted to UTF-8" on the plain path, which is
    indistinguishable from a real failure.
    """
    import httpx

    body = {
        "source_code": base64.b64encode(source.encode("utf-8")).decode("ascii"),
        "language_id": LANGUAGE_CXX,
        "stdin": base64.b64encode(b"").decode("ascii"),
    }
    response = httpx.post(
        JUDGE0_URL,
        params={"base64_encoded": "true", "wait": "true"},
        json=body,
        timeout=timeout,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Judge0 answered {response.status_code}: {response.text[:300]}")

    data = response.json()
    status_id = data.get("status", {}).get("id")
    if not isinstance(status_id, int):
        raise RuntimeError("Judge0 returned something unexpected.")

    def field(name: str) -> str:
        value = data.get(name)
        if not value:
            return ""
        try:
            return base64.b64decode(value, validate=True).decode("utf-8", "replace")
        except (ValueError, UnicodeDecodeError):
            return value

    return status_id, field("stdout"), field("stderr") or field("compile_output")


def split_outputs(stdout: str) -> list[str]:
    """One entry per case, in order."""
    if CASE_MARKER not in stdout:
        return []
    return [part.strip() for part in stdout.split(CASE_MARKER)[1:]]


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


def build_prefix() -> str:
    """The C++ that goes before the user's function."""
    return f"""#include <bits/stdc++.h>
using namespace std;
{PRINT_HELPERS}"""


def build_suffix(
    signature: str,
    params: list,
    cases: list[list[str]],
    print_param: str | None = None,
) -> str:
    """The C++ that goes after the user's function."""
    name = signature.split("(")[0].split()[-1]
    blocks = []
    for i, case in enumerate(cases):
        decls = "\n".join(
            f"    {params[j][0]} p{i}_{j} = {arg};" for j, arg in enumerate(case)
        )
        call = f"{name}(" + ", ".join(f"p{i}_{j}" for j in range(len(params))) + ")"
        if print_param:
            idx = [p[1] for p in params].index(print_param)
            body = f"        {call};\n        __print(p{i}_{idx});"
        else:
            body = f"        auto __r = {call};\n        __print(__r);"
        blocks.append(
            "    {\n"
            f"{decls}\n"
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
