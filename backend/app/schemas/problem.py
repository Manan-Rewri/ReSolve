from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Difficulty(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class StruggleRating(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"
    DIDNT_FIND_SOLUTION = "Didn't find the solution?"
    COULDNT_WRITE_A_LINE = "Couldn't Write a Line"  # Legacy alias kept for old rows.


class ProblemStatus(str, Enum):
    ACTIVE = "active"
    MASTERED = "mastered"
    ARCHIVED = "archived"


def _require_http_url(value: str) -> str:
    cleaned = value.strip()
    if not cleaned.startswith(("http://", "https://")):
        raise ValueError("Problem URL must start with http:// or https://")
    return cleaned


def _require_non_empty(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Field cannot be empty")
    return cleaned


class ProblemBase(BaseModel):
    url: str = Field(..., description="URL of the DSA / LeetCode problem")
    title: str = Field(..., min_length=1, max_length=255, description="Problem title")
    topic: str = Field(..., min_length=1, max_length=100, description="DSA topic e.g. Arrays, Trees, DP")
    difficulty: Difficulty = Field(..., description="Problem difficulty")
    notes: Optional[str] = Field(None, description="Personal thoughts, edge cases, learnings")
    solution_or_hints: Optional[str] = Field(None, description="Hints or personal solution code")
    content_html: Optional[str] = Field(None, description="Problem statement HTML from LeetCode")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return _require_http_url(value)

    @field_validator("title", "topic")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        return _require_non_empty(value)


class ProblemCreate(ProblemBase):
    initial_struggle_rating: Optional[StruggleRating] = Field(
        None, description="Struggle rating when first attempting the problem"
    )


class ProblemUpdate(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    topic: Optional[str] = None
    difficulty: Optional[Difficulty] = None
    notes: Optional[str] = None
    solution_or_hints: Optional[str] = None
    content_html: Optional[str] = None
    status: Optional[ProblemStatus] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: Optional[str]) -> Optional[str]:
        return _require_http_url(value) if value is not None else value


class ProblemResponse(ProblemBase):
    id: str
    user_id: str
    status: str
    current_interval_days: int
    ease_factor: float
    repetitions: int
    last_struggle_rating: Optional[str] = None
    last_reviewed_at: Optional[datetime] = None
    next_review_due: datetime
    is_due: bool = False
    is_overdue: bool = False
    practice_priority: int = Field(
        1, description="Daily-practice rank: 4 (most urgent) down to 1 (least)"
    )
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProblemListResponse(BaseModel):
    total: int
    items: List[ProblemResponse]