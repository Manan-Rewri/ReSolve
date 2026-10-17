"""
Tests for turning a LeetCode stub into a runnable program.

Uses real LeetCode snippets recorded from the API, so the suite stays offline.
"""
from app.services.starter import (
    build_cpp_starter,
    build_python_starter,
    build_starters,
    example_to_stdin,
    parse_cpp_signature,
    parse_python_signature,
)

CPP_TWO_SUM = """class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {

    }
};"""

CPP_VALID_PARENTHESES = """class Solution {
public:
    bool isValid(string s) {

    }
};"""

PY_TWO_SUM = "class Solution:\n    def twoSum(self, nums: list[int], target: int) -> list[int]:\n        "

PY_VALID_PARENTHESES = "class Solution:\n    def isValid(self, s: str) -> bool:\n        "


def test_parses_cpp_signature_with_vector_and_scalar():
    signature = parse_cpp_signature(CPP_TWO_SUM)
    assert signature.method == "twoSum"
    assert [p.name for p in signature.parameters] == ["nums", "target"]
    assert [p.kind for p in signature.parameters] == ["int_vector", "int"]
    assert signature.returns == "int_vector"
    assert signature.supported


def test_parses_python_signature_skips_self():
    signature = parse_python_signature(PY_TWO_SUM)
    assert signature.method == "twoSum"
    assert [p.name for p in signature.parameters] == ["nums", "target"]
    assert signature.returns == "int_vector"
    assert signature.supported


def test_cpp_starter_gets_a_main_that_reads_one_line_per_parameter():
    starter = build_cpp_starter(CPP_TWO_SUM)
    assert starter is not None
    code = starter.code
    assert "#include <bits/stdc++.h>" in code
    assert "vector<int> twoSum(vector<int>& nums, int target)" in code
    assert "int main()" in code
    assert "Solution().twoSum(nums, target)" in code


def test_python_starter_is_importable_on_python_38():
    """Judge0 runs 3.8, where `list[int]` raises TypeError at import time."""
    starter = build_python_starter(PY_TWO_SUM)
    code = starter.code
    assert "list[int]" not in code
    assert "from typing import List" in code
    assert "List[int]" in code
    assert 'if __name__ == "__main__":' in code


def test_empty_cpp_body_gets_a_placeholder_return():
    """Without it the driver reads uninitialised memory and prints garbage."""
    code = build_cpp_starter(CPP_TWO_SUM).code
    assert "return {};" in code


def test_empty_python_body_gets_a_placeholder_return():
    """A def whose suite is only whitespace is an IndentationError."""
    assert "return []" in build_python_starter(PY_TWO_SUM).code
    assert "return False" in build_python_starter(PY_VALID_PARENTHESES).code


def test_driver_calls_the_method_exactly_once():
    """Inlining the call in a print loop would re-run mutating solutions."""
    code = build_cpp_starter(CPP_TWO_SUM).code
    assert code.count("Solution().twoSum(nums, target)") == 1
    assert "auto result =" in code


def test_bool_results_print_leetcode_style():
    cpp = build_cpp_starter(CPP_VALID_PARENTHESES).code
    assert '"true" : "false"' in cpp
    python = build_python_starter(PY_VALID_PARENTHESES).code
    assert 'print("true" if' in python


def test_unsupported_signature_yields_no_starter():
    """Linked-list parameters cannot be driven, so the caller must fall back."""
    linked_list = """class Solution {
public:
    ListNode* addTwoNumbers(ListNode* l1, ListNode* l2) {

    }
};"""
    assert build_cpp_starter(linked_list) is None


def test_matrix_parameter_yields_no_starter():
    matrix = """class Solution {
public:
    int numIslands(vector<vector<char>>& grid) {

    }
};"""
    assert build_cpp_starter(matrix) is None


def test_build_starters_prefers_the_modern_python_snippet():
    snippets = {"cpp": CPP_TWO_SUM, "python3": PY_TWO_SUM, "python": "legacy docstring stub"}
    starters = build_starters(snippets)
    assert set(starters) == {"cpp", "python"}
    assert "docstring" not in starters["python"].code


def test_build_starters_ignores_absent_or_unsupported_snippets():
    assert build_starters({}) == {}
    assert build_starters({"java": "class Solution {}", "ruby": ""}) == {}


def test_example_input_becomes_driver_standard_input():
    signature = parse_cpp_signature(CPP_TWO_SUM)
    assert example_to_stdin("nums = [2,7,11,15], target = 9", signature) == "2 7 11 15\n9"


def test_string_parameters_keep_their_brackets():
    """The generic frontend strip would turn '()[]{}' into nothing."""
    signature = parse_cpp_signature(CPP_VALID_PARENTHESES)
    assert example_to_stdin('s = "()[]{}"', signature) == "()[]{}"


def test_negative_and_empty_values_survive():
    signature = parse_cpp_signature(
        "class Solution { public: int f(vector<int>& a, int n) { } };"
    )
    assert example_to_stdin("a = [-2,-1,0], n = 3", signature) == "-2 -1 0\n3"
    assert example_to_stdin("a = [], n = 0", signature) == "\n0"


def test_unmappable_example_returns_none_rather_than_guessing():
    signature = parse_cpp_signature(CPP_TWO_SUM)
    assert example_to_stdin("", signature) is None


def test_char_vector_arguments_are_supported():
    """vector<char> appears in problems like String Compression."""
    snippet = "class Solution {\npublic:\n    int compress(vector<char>& chars) {\n\n    }\n};"
    starter = build_cpp_starter(snippet)
    assert starter is not None
    assert starter.signature.parameters[0].kind == "char_vector"
    assert example_to_stdin('chars = ["a","a","b"]', starter.signature) == "a a b"


def test_python_vector_split_binds_to_the_whole_conditional():
    """A missing paren here silently broke every Python vector argument."""
    code = build_python_starter(PY_TWO_SUM).code
    assert "list(map(int, (lines[0] if len(lines) > 0 else '').split()))" in code
