"""Practice sheets.

A sheet is a named set of LeetCode problem slugs. The search endpoint filters
suggestions down to the selected sheet, so the dropdown on the Home page scopes
results the way a practice sheet should.

SEED DATA: the lists below are a starting point, not an exhaustive mirror of any
published sheet. They are intentionally compact and use slugs that are stable and
easy to verify. Extend them as needed - adding a slug is the only change
required, no code elsewhere needs to move.
"""
from typing import Dict, FrozenSet, List, Optional

STRIVER_A2Z: FrozenSet[str] = frozenset(
    {
        # Arrays
        "two-sum",
        "best-time-to-buy-and-sell-stock",
        "maximum-subarray",
        "next-permutation",
        "rotate-array",
        "search-in-rotated-sorted-array",
        "square-root-of-a-number",
        "sort-colors",
        "move-zeroes",
        "book-allocation",
        "aggressive-cows",
        "painter-s-partition-problem",
        "valid-tic-tac-toe-state",
        # Binary search on the answer
        "split-array-largest-sum",
        "gas-station",
        "min-capacity-to-ship-packages-within-d-days",
        "koko-eating-bananas",
        # Two pointers
        "3sum",
        "trapping-rain-water",
        "container-with-most-water",
        "merge-intervals",
        "valid-palindrome",
        "valid-palindrome-ii",
        "remove-duplicates-from-sorted-array",
        "remove-nth-node-from-end-of-list",
        "median-of-two-sorted-arrays",
        # Strings
        "reverse-string",
        "valid-anagram",
        "valid-parentheses",
        "group-anagrams",
        "longest-substring-without-repeating-characters",
        "count-and-say",
        "string-to-integer-atoi",
        "longest-palindromic-substring",
        "implement-strstr",
        # Recursion and divide & conquer
        "reverse-array",
        "fibonacci-number",
        "factorial",
        "merge-sort",
        "quick-sort",
        "sudoku-solver",
        "n-queens",
        "word-search",
        "rat-in-a-maze",
        "flood-fill",
        # Bit manipulation
        "number-of-1-bits",
        "power-of-two",
        "counting-bits",
        "reverse-bits",
        "sum-of-two-integers",
        "add-two-numbers",
        "single-number",
        # Dynamic programming
        "climbing-stairs",
        "coin-change",
        "coin-change-ii",
        "target-sum",
        "partition-equal-subset-sum",
        "word-break",
        "word-break-ii",
        "edit-distance",
        "longest-increasing-subsequence",
        "longest-common-subsequence",
        "palindrome-partitioning",
        "decode-ways",
        "house-robber",
        "house-robber-ii",
        "unique-paths",
        "jump-game",
        "jump-game-ii",
        # Graphs
        "number-of-islands",
        "surrounded-regions",
        "course-schedule",
    }
)

LEETCODE_DSA: FrozenSet[str] = frozenset(
    {
        # Arrays and hashing
        "two-sum",
        "contains-duplicate",
        "product-of-array-except-self",
        "single-number",
        "majority-element",
        "majority-element-ii",
        "sort-colors",
        "rotate-array",
        "maximum-subarray",
        "maximum-product-subarray",
        "find-the-duplicate-number",
        "search-in-rotated-sorted-array",
        "3sum",
        "3sum-closest",
        "4sum",
        "container-with-most-water",
        # Linked list
        "reverse-linked-list",
        "linked-list-cycle",
        "merge-two-sorted-lists",
        "remove-nth-node-from-end-of-list",
        "remove-duplicates-from-sorted-list",
        "reorder-list",
        "add-two-numbers",
        "merge-k-sorted-lists",
        # Strings
        "reverse-string",
        "valid-palindrome",
        "valid-anagram",
        "valid-palindrome-ii",
        "valid-parentheses",
        "group-anagrams",
        "longest-substring-without-repeating-characters",
        "longest-palindromic-substring",
        "palindrome-partitioning",
        "count-and-say",
        "string-to-integer-atoi",
        "reverse-integer",
        # Stack and queue
        "min-stack",
        "valid-parentheses",
        "implement-queue-using-stacks",
        # Binary trees
        "maximum-depth-of-binary-tree",
        "same-tree",
        "invert-binary-tree",
        "binary-tree-inorder-traversal",
        "binary-tree-level-order-traversal",
        "binary-tree-level-order-traversal-ii",
        "binary-tree-zigzag-level-order-traversal",
        "validate-binary-search-tree",
        "kth-smallest-element-in-a-bst",
        "lowest-common-ancestor-of-a-binary-search-tree",
        "lowest-common-ancestor-of-a-binary-tree",
        "construct-binary-tree-from-preorder-and-inorder-traversal",
        "path-sum",
        "binary-tree-maximum-path-sum",
        # Dynamic programming
        "climbing-stairs",
        "coin-change",
        "coin-change-ii",
        "target-sum",
        "partition-equal-subset-sum",
        "word-break",
        "word-break-ii",
        "edit-distance",
        "longest-increasing-subsequence",
        "longest-common-subsequence",
        "decode-ways",
        "house-robber",
        "house-robber-ii",
        "unique-paths",
        "jump-game",
        "jump-game-ii",
        "subsets",
        "combination-sum",
        "subsets-ii",
        # Graphs
        "number-of-islands",
        "surrounded-regions",
        "course-schedule",
        "clone-graph",
        "pacific-atlantic-water-flow",
        # Design
        "lru-cache",
        "design-circular-queue",
    }
)

SHEETS: Dict[str, Dict[str, object]] = {
    "all": {
        "label": "All problems",
        "hint": "Every LeetCode problem",
        "slugs": None,
    },
    "striver": {
        "label": "Striver A2Z DSA",
        "hint": "Striver's step-wise DSA sheet",
        "slugs": STRIVER_A2Z,
    },
    "leetcode": {
        "label": "LeetCode DSA",
        "hint": "Core LeetCode DSA patterns",
        "slugs": LEETCODE_DSA,
    },
}

DEFAULT_SHEET = "all"


def known_sheet_ids() -> List[str]:
    return list(SHEETS)


def get_slugs(sheet_id: Optional[str]) -> Optional[FrozenSet[str]]:
    """Returns the slug allow-list for a sheet, or None meaning "no filter"."""
    sheet = SHEETS.get(sheet_id or DEFAULT_SHEET)
    if sheet is None:
        return None
    return sheet["slugs"]