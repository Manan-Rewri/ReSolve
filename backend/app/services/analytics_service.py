from datetime import timedelta
from typing import Dict, List, Optional

from sqlalchemy import case, or_
from sqlalchemy.orm import Session

from app.models.problem import Problem
from app.schemas.dashboard import DashboardResponse, UpcomingRevisionGroup
from app.schemas.problem import ProblemResponse, ProblemStatus, StruggleRating
from app.services.problem_mapper import (
    LAPSE_PRIORITY,
    LAPSE_RATINGS,
    PRIORITY_BY_RATING,
    to_problem_response,
)
from app.utils.time import as_utc, start_of_day, utc_now

UPCOMING_WINDOW_DAYS = 7
MASTERY_INTERVAL_DAYS = 30


def _priority_expression():
    """Mirror of practice_priority() as a SQL CASE so the DB can sort by it."""
    return case(
        (Problem.last_struggle_rating.in_(tuple(LAPSE_RATINGS)), LAPSE_PRIORITY),
        (Problem.last_struggle_rating == StruggleRating.HARD.value, PRIORITY_BY_RATING[StruggleRating.HARD.value]),
        (Problem.last_struggle_rating == StruggleRating.MEDIUM.value, PRIORITY_BY_RATING[StruggleRating.MEDIUM.value]),
        (Problem.last_struggle_rating == StruggleRating.EASY.value, PRIORITY_BY_RATING[StruggleRating.EASY.value]),
        else_=LAPSE_PRIORITY,
    )


class AnalyticsService:
    @classmethod
    def get_dashboard(cls, db: Session, user_id: str) -> DashboardResponse:
        now = utc_now()
        today_start = start_of_day(now)
        tomorrow_start = today_start + timedelta(days=1)
        window_end = today_start + timedelta(days=UPCOMING_WINDOW_DAYS)

        due_today: List[ProblemResponse] = []
        overdue: List[ProblemResponse] = []
        upcoming: Dict[str, List[ProblemResponse]] = {}
        by_topic: Dict[str, int] = {}
        by_difficulty: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        mastered = 0

        rows = db.query(Problem).filter(Problem.user_id == user_id).all()

        for row in rows:
            by_topic[row.topic] = by_topic.get(row.topic, 0) + 1
            by_difficulty[row.difficulty] = by_difficulty.get(row.difficulty, 0) + 1
            by_status[row.status] = by_status.get(row.status, 0) + 1

            if (
                row.status == ProblemStatus.MASTERED.value
                or row.current_interval_days >= MASTERY_INTERVAL_DAYS
            ):
                mastered += 1

            due_at = as_utc(row.next_review_due)
            if due_at < today_start:
                overdue.append(to_problem_response(row, now=now))
            elif due_at < tomorrow_start:
                due_today.append(to_problem_response(row, now=now))
            elif due_at < window_end:
                upcoming.setdefault(due_at.strftime("%Y-%m-%d"), []).append(
                    to_problem_response(row, now=now)
                )

        groups = [
            UpcomingRevisionGroup(due_date=date, count=len(items), problems=items)
            for date, items in sorted(upcoming.items())
        ]

        return DashboardResponse(
            total_saved_problems=len(rows),
            due_today_count=len(due_today),
            overdue_count=len(overdue),
            mastered_count=mastered,
            due_today=due_today,
            overdue=overdue,
            upcoming_revisions=groups,
            by_topic=by_topic,
            by_difficulty=by_difficulty,
            by_status=by_status,
        )

    @classmethod
    def get_daily_practice_queue(
        cls,
        db: Session,
        user_id: str,
        topic: Optional[str] = None,
        due_only: bool = False,
        limit: int = 50,
    ) -> List[ProblemResponse]:
        now = utc_now()
        query = db.query(Problem).filter(
            Problem.user_id == user_id,
            Problem.status == ProblemStatus.ACTIVE.value,
        )

        if due_only:
            query = query.filter(
                or_(
                    Problem.next_review_due <= now,
                    Problem.last_struggle_rating.is_(None),
                    Problem.repetitions == 0,
                )
            )

        if topic:
            query = query.filter(Problem.topic.ilike(f"%{topic}%"))

        rows = (
            query.order_by(
                _priority_expression().desc(),
                Problem.next_review_due.asc(),
            )
            .limit(limit)
            .all()
        )
        return [to_problem_response(row, now=now) for row in rows]


analytics_service = AnalyticsService()