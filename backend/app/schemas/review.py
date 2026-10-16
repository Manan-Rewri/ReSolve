from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.problem import ProblemResponse, StruggleRating


class ReviewCreate(BaseModel):
    struggle_rating: StruggleRating = Field(
        ..., description="How difficult the problem was during revision"
    )
    notes: Optional[str] = Field(
        None, description="Optional notes from this revision session"
    )


class ReviewResponse(BaseModel):
    id: str
    problem_id: str
    user_id: str
    struggle_rating: str
    scheduled_days: int
    notes: Optional[str] = None
    reviewed_at: datetime
    next_review_due: datetime
    updated_problem: Optional[ProblemResponse] = None

    model_config = {"from_attributes": True}