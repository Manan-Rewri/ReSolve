from datetime import datetime
from typing import Optional

from app.models.problem import Problem
from app.schemas.problem import ProblemResponse, StruggleRating
from app.utils.time import as_utc, start_of_day, utc_now

LAPSE_RATINGS = frozenset(
    {
        StruggleRating.DIDNT_FIND_SOLUTION.value,
        StruggleRating.COULDNT_WRITE_A_LINE.value,
    }
)

PRIORITY_BY_RATING = {
    StruggleRating.HARD.value: 3,
    StruggleRating.MEDIUM.value: 2,
    StruggleRating.EASY.value: 1,
}

LAPSE_PRIORITY = 4
FALLBACK_PRIORITY = 4


def practice_priority(last_struggle_rating: Optional[str]) -> int:
    """Daily-practice rank: 4 is most urgent, 1 is least. New and lapsed items are 4."""
    if last_struggle_rating in LAPSE_RATINGS:
        return LAPSE_PRIORITY
    return PRIORITY_BY_RATING.get(last_struggle_rating, FALLBACK_PRIORITY)


def to_problem_response(problem: Problem, now: Optional[datetime] = None) -> ProblemResponse:
    now = now or utc_now()
    due_at = as_utc(problem.next_review_due)

    return ProblemResponse(
        id=problem.id,
        user_id=problem.user_id,
        url=problem.url,
        title=problem.title,
        topic=problem.topic,
        difficulty=problem.difficulty,
        notes=problem.notes,
        solution_or_hints=problem.solution_or_hints,
        content_html=problem.content_html,
        status=problem.status,
        current_interval_days=problem.current_interval_days,
        ease_factor=problem.ease_factor,
        repetitions=problem.repetitions,
        last_struggle_rating=problem.last_struggle_rating,
        last_reviewed_at=problem.last_reviewed_at,
        next_review_due=problem.next_review_due,
        is_due=due_at <= now,
        is_overdue=due_at < start_of_day(now),
        practice_priority=practice_priority(problem.last_struggle_rating),
        created_at=problem.created_at,
        updated_at=problem.updated_at,
    )