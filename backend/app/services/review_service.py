from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.review_log import ReviewLog
from app.schemas.problem import ProblemResponse, ProblemStatus
from app.schemas.review import ReviewCreate
from app.services.problem_mapper import to_problem_response
from app.services.problem_service import get_owned_problem
from app.services.scheduler_service import scheduler
from app.utils.time import utc_now

MASTERY_INTERVAL_DAYS = 30


class ReviewService:
    @classmethod
    def submit_review(
        cls,
        db: Session,
        user_id: str,
        problem_id: str,
        review_in: ReviewCreate,
        reviewed_at: Optional[datetime] = None,
    ) -> Optional[Tuple[ReviewLog, ProblemResponse]]:
        problem = get_owned_problem(db, user_id, problem_id)
        if not problem:
            return None

        reviewed_at = reviewed_at or utc_now()
        schedule = scheduler.calculate_next_schedule(
            rating=review_in.struggle_rating,
            current_interval=problem.current_interval_days,
            ease_factor=problem.ease_factor,
            repetitions=problem.repetitions,
            reviewed_at=reviewed_at,
        )

        problem.current_interval_days = schedule.interval_days
        problem.ease_factor = schedule.ease_factor
        problem.repetitions = schedule.repetitions
        problem.last_struggle_rating = review_in.struggle_rating.value
        problem.last_reviewed_at = reviewed_at
        problem.next_review_due = schedule.next_review_due
        problem.updated_at = reviewed_at

        if (
            schedule.interval_days >= MASTERY_INTERVAL_DAYS
            and problem.status == ProblemStatus.ACTIVE.value
        ):
            problem.status = ProblemStatus.MASTERED.value

        review_log = ReviewLog(
            problem_id=problem.id,
            user_id=user_id,
            struggle_rating=review_in.struggle_rating.value,
            scheduled_days=schedule.interval_days,
            notes=review_in.notes,
            reviewed_at=reviewed_at,
        )
        db.add(review_log)
        db.commit()
        db.refresh(problem)
        db.refresh(review_log)

        return review_log, to_problem_response(problem, now=reviewed_at)

    @classmethod
    def get_review_history(
        cls, db: Session, user_id: str, problem_id: str
    ) -> List[ReviewLog]:
        if not get_owned_problem(db, user_id, problem_id):
            return []

        return (
            db.query(ReviewLog)
            .filter(ReviewLog.problem_id == problem_id, ReviewLog.user_id == user_id)
            .order_by(ReviewLog.reviewed_at.desc())
            .all()
        )


review_service = ReviewService()