from typing import Optional, Tuple, List

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.problem import Problem
from app.models.review_log import ReviewLog
from app.schemas.problem import (
    ProblemCreate,
    ProblemResponse,
    ProblemStatus,
    ProblemUpdate,
)
from app.services.problem_mapper import to_problem_response
from app.services.scheduler_service import DEFAULT_EASE_FACTOR, scheduler
from app.utils.time import utc_now

ENUM_FIELDS = frozenset({"difficulty", "status"})


def get_owned_problem(db: Session, user_id: str, problem_id: str) -> Optional[Problem]:
    return (
        db.query(Problem)
        .filter(Problem.id == problem_id, Problem.user_id == user_id)
        .first()
    )


class ProblemService:
    @classmethod
    def create_problem(
        cls, db: Session, user_id: str, problem_in: ProblemCreate
    ) -> ProblemResponse:
        created_at = utc_now()
        initial_rating = problem_in.initial_struggle_rating

        if initial_rating:
            schedule = scheduler.calculate_next_schedule(
                rating=initial_rating,
                current_interval=1,
                ease_factor=DEFAULT_EASE_FACTOR,
                repetitions=0,
                reviewed_at=created_at,
            )
        else:
            schedule = None

        problem = Problem(
            user_id=user_id,
            url=problem_in.url,
            title=problem_in.title,
            topic=problem_in.topic,
            difficulty=problem_in.difficulty.value,
            notes=problem_in.notes,
            solution_or_hints=problem_in.solution_or_hints,
            content_html=problem_in.content_html,
            status=ProblemStatus.ACTIVE.value,
            current_interval_days=schedule.interval_days if schedule else 1,
            ease_factor=schedule.ease_factor if schedule else DEFAULT_EASE_FACTOR,
            repetitions=schedule.repetitions if schedule else 0,
            last_struggle_rating=initial_rating.value if initial_rating else None,
            last_reviewed_at=created_at if initial_rating else None,
            next_review_due=schedule.next_review_due if schedule else created_at,
            created_at=created_at,
            updated_at=created_at,
        )
        db.add(problem)
        db.flush()

        if initial_rating:
            db.add(
                ReviewLog(
                    problem_id=problem.id,
                    user_id=user_id,
                    struggle_rating=initial_rating.value,
                    scheduled_days=schedule.interval_days,
                    notes="Initial registration review",
                    reviewed_at=created_at,
                )
            )

        db.commit()
        db.refresh(problem)
        return to_problem_response(problem, now=created_at)

    @classmethod
    def get_problem(
        cls, db: Session, user_id: str, problem_id: str
    ) -> Optional[ProblemResponse]:
        problem = get_owned_problem(db, user_id, problem_id)
        return to_problem_response(problem) if problem else None

    @classmethod
    def list_problems(
        cls,
        db: Session,
        user_id: str,
        topic: Optional[str] = None,
        difficulty: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        due_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[ProblemResponse]]:
        query = db.query(Problem).filter(Problem.user_id == user_id)

        if topic:
            query = query.filter(Problem.topic.ilike(f"%{topic}%"))
        if difficulty:
            query = query.filter(Problem.difficulty == difficulty)
        if status:
            query = query.filter(Problem.status == status)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Problem.title.ilike(pattern),
                    Problem.topic.ilike(pattern),
                    Problem.notes.ilike(pattern),
                )
            )

        now = utc_now()
        if due_only:
            query = query.filter(Problem.next_review_due <= now)

        total = query.count()
        rows = (
            query.order_by(Problem.next_review_due.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return total, [to_problem_response(row, now=now) for row in rows]

    @classmethod
    def update_problem(
        cls,
        db: Session,
        user_id: str,
        problem_id: str,
        problem_update: ProblemUpdate,
    ) -> Optional[ProblemResponse]:
        problem = get_owned_problem(db, user_id, problem_id)
        if not problem:
            return None

        for field, value in problem_update.model_dump(exclude_unset=True).items():
            if value is None:
                continue
            setattr(problem, field, value.value if field in ENUM_FIELDS else value)

        problem.updated_at = utc_now()
        db.commit()
        db.refresh(problem)
        return to_problem_response(problem)

    @classmethod
    def delete_problem(cls, db: Session, user_id: str, problem_id: str) -> bool:
        problem = get_owned_problem(db, user_id, problem_id)
        if not problem:
            return False

        db.delete(problem)
        db.commit()
        return True


problem_service = ProblemService()