from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class LeetCodeFetchRequest(BaseModel):
    """Payload to fetch a question from LeetCode."""

    title_or_url: str = Field(
        ...,
        min_length=1,
        description="LeetCode problem title, slug, or full URL (e.g. 'Two Sum', '3Sum', or 'https://leetcode.com/problems/two-sum/')",
    )


class LeetCodeExample(BaseModel):
    """A single Input/Output example parsed from the problem statement."""

    input: str = Field(..., description="Example input, collapsed to one line")
    output: str = Field("", description="Expected output for that input")
    stdin: Optional[str] = Field(
        None,
        description=(
            "Example input rendered in the layout the generated driver reads, "
            "ready to paste into the input box"
        ),
    )


class LeetCodeQuestionData(BaseModel):
    """Extracted LeetCode problem data."""

    frontend_id: str = Field(..., description="Problem number on LeetCode e.g. '1'")
    title: str = Field(..., description="Official problem title e.g. 'Two Sum'")
    title_slug: str = Field(..., description="URL slug e.g. 'two-sum'")
    url: str = Field(..., description="Full LeetCode URL")
    difficulty: str = Field(..., description="Easy, Medium, or Hard")
    topic: str = Field(..., description="Primary topic e.g. Arrays, Dynamic Programming")
    all_topics: List[str] = Field(
        default_factory=list, description="All associated LeetCode tags"
    )
    content_html: str = Field(
        ..., description="Full problem statement HTML with examples and constraints"
    )
    content_text: Optional[str] = Field(
        None, description="Plain text representation of the question"
    )
    hints: List[str] = Field(
        default_factory=list, description="Official LeetCode problem hints"
    )
    sample_test_case: Optional[str] = Field(None, description="Default sample test case")
    sample_expected_output: Optional[str] = Field(
        None, description="Expected output of the first example"
    )
    examples: List[LeetCodeExample] = Field(
        default_factory=list,
        description="Input/Output examples parsed from the statement",
    )
    starters: Dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Runnable starter per LeetCode language slug. Built from the official "
            "stub plus a generated driver, so the user only writes the method body. "
            "Languages whose signature cannot be driven are omitted."
        ),
    )


class LeetCodeSuggestion(BaseModel):
    """A single autocomplete suggestion shown in the search bar dropdown."""

    frontend_id: str = Field(..., description="Problem number on LeetCode e.g. '1'")
    title: str = Field(..., description="Problem title e.g. 'Two Sum'")
    title_slug: str = Field(..., description="URL slug e.g. 'two-sum'")
    difficulty: str = Field(..., description="Easy, Medium, or Hard")
    topic: Optional[str] = Field(None, description="Primary topic tag, if any")