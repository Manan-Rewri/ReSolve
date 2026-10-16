"""
LeetCode Fetch and Import Schemas.
Defines schemas for requesting and receiving LeetCode question data.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class LeetCodeFetchRequest(BaseModel):
    """Payload to fetch a question from LeetCode."""
    title_or_url: str = Field(
        ...,
        min_length=1,
        description="LeetCode problem title, slug, or full URL (e.g. 'Two Sum', '3Sum', or 'https://leetcode.com/problems/two-sum/')"
    )


class LeetCodeQuestionData(BaseModel):
    """Extracted LeetCode problem data."""
    frontend_id: str = Field(..., description="Problem number on LeetCode e.g. '1'")
    title: str = Field(..., description="Official problem title e.g. 'Two Sum'")
    title_slug: str = Field(..., description="URL slug e.g. 'two-sum'")
    url: str = Field(..., description="Full LeetCode URL")
    difficulty: str = Field(..., description="Easy, Medium, or Hard")
    topic: str = Field(..., description="Primary topic e.g. Arrays, Dynamic Programming")
    all_topics: List[str] = Field(default_factory=list, description="All associated LeetCode tags")
    content_html: str = Field(..., description="Full problem statement HTML with examples and constraints")
    content_text: Optional[str] = Field(None, description="Plain text representation of the question")
    hints: List[str] = Field(default_factory=list, description="Official LeetCode problem hints")
    sample_test_case: Optional[str] = Field(None, description="Default sample test case")


class LeetCodeSuggestion(BaseModel):
    """A single autocomplete suggestion shown in the search bar dropdown."""
    frontend_id: str = Field(..., description="Problem number on LeetCode e.g. '1'")
    title: str = Field(..., description="Problem title e.g. 'Two Sum'")
    title_slug: str = Field(..., description="URL slug e.g. 'two-sum'")
    difficulty: str = Field(..., description="Easy, Medium, or Hard")
    topic: Optional[str] = Field(None, description="Primary topic tag, if any")
