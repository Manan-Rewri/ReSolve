from typing import Dict, List

from pydantic import BaseModel

from app.schemas.problem import ProblemResponse


class UpcomingRevisionGroup(BaseModel):
    due_date: str  # YYYY-MM-DD
    count: int
    problems: List[ProblemResponse]


class DashboardResponse(BaseModel):
    total_saved_problems: int
    due_today_count: int
    overdue_count: int
    mastered_count: int
    due_today: List[ProblemResponse]
    overdue: List[ProblemResponse]
    upcoming_revisions: List[UpcomingRevisionGroup]
    by_topic: Dict[str, int]
    by_difficulty: Dict[str, int]
    by_status: Dict[str, int]