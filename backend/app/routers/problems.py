from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.leetcode import (
    LeetCodeFetchRequest,
    LeetCodeQuestionData,
    LeetCodeSuggestion,
)
from app.schemas.problem import (
    Difficulty,
    ProblemCreate,
    ProblemListResponse,
    ProblemResponse,
    ProblemStatus,
    ProblemUpdate,
)
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services.analytics_service import analytics_service
from app.services.leetcode_service import leetcode_service
from app.services.problem_service import problem_service
from app.services.review_service import review_service

router = APIRouter(prefix="/problems", tags=["Problems"])

NOT_FOUND = "Problem not found or you do not have permission to access it."


@router.post(
    "",
    response_model=ProblemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a new problem",
    description="Saves a new LeetCode or DSA problem with an optional initial struggle rating.",
)
def create_problem(
    problem_in: ProblemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return problem_service.create_problem(
        db=db,
        user_id=current_user.id,
        problem_in=problem_in,
    )


@router.get(
    "",
    response_model=ProblemListResponse,
    summary="List saved problems",
    description="Returns the user's saved problems with optional filters.",
)
def list_problems(
    topic: Optional[str] = Query(None, description="Filter by topic (substring match)"),
    difficulty: Optional[Difficulty] = Query(None, description="Filter by difficulty"),
    status_filter: Optional[ProblemStatus] = Query(None, alias="status", description="Filter by status"),
    search: Optional[str] = Query(None, description="Search across title, topic and notes"),
    due_only: bool = Query(False, description="Filter to only problems currently due for review"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total, items = problem_service.list_problems(
        db=db,
        user_id=current_user.id,
        topic=topic,
        difficulty=difficulty.value if difficulty else None,
        status=status_filter.value if status_filter else None,
        search=search,
        due_only=due_only,
        skip=skip,
        limit=limit,
    )
    return ProblemListResponse(total=total, items=items)


@router.post(
    "/fetch-leetcode",
    response_model=LeetCodeQuestionData,
    summary="Fetch LeetCode problem from title or URL",
    description="Fetches the full question description, difficulty, topics and hints.",
)
async def fetch_leetcode(payload: LeetCodeFetchRequest):
    return await leetcode_service.fetch_problem(payload.title_or_url)


@router.get(
    "/search",
    response_model=List[LeetCodeSuggestion],
    summary="Search LeetCode problems (autocomplete)",
    description="Returns matching LeetCode problems for the search-bar dropdown.",
)
async def search_leetcode(
    q: str = Query(..., min_length=1, max_length=100, description="Title, number, or keyword"),
    limit: int = Query(8, ge=1, le=20, description="Maximum suggestions to return"),
):
    return await leetcode_service.search_suggestions(q, limit=limit)


@router.get(
    "/daily-practice",
    response_model=List[ProblemResponse],
    summary="Get daily practice revision queue",
    description="Arranges problems for daily revision, prioritised by struggle rating.",
)
def get_daily_practice(
    topic: Optional[str] = Query(None, description="Optional topic filter"),
    due_only: bool = Query(False, description="Filter to only problems due for review"),
    limit: int = Query(50, ge=1, le=100, description="Max problems to practice"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return analytics_service.get_daily_practice_queue(
        db=db,
        user_id=current_user.id,
        topic=topic,
        due_only=due_only,
        limit=limit,
    )


@router.get(
    "/{problem_id}",
    response_model=ProblemResponse,
    summary="Get single problem",
    description="Retrieves a problem by its ID. Users can only access their own problems.",
)
def get_problem(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    problem = problem_service.get_problem(db=db, user_id=current_user.id, problem_id=problem_id)
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return problem


@router.put(
    "/{problem_id}",
    response_model=ProblemResponse,
    summary="Update problem",
    description="Updates title, topic, difficulty, notes, solutions or status.",
)
def update_problem(
    problem_id: str,
    problem_update: ProblemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = problem_service.update_problem(
        db=db,
        user_id=current_user.id,
        problem_id=problem_id,
        problem_update=problem_update,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)
    return updated


@router.delete(
    "/{problem_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete problem",
    description="Deletes a saved problem and all of its revision history.",
)
def delete_problem(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not problem_service.delete_problem(
        db=db, user_id=current_user.id, problem_id=problem_id
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)


@router.post(
    "/{problem_id}/review",
    response_model=ReviewResponse,
    summary="Submit a revision review",
    description="Records a revision session and reschedules the next review.",
)
def submit_review(
    problem_id: str,
    review_in: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = review_service.submit_review(
        db=db,
        user_id=current_user.id,
        problem_id=problem_id,
        review_in=review_in,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)

    review_log, problem = result
    return ReviewResponse(
        id=review_log.id,
        problem_id=review_log.problem_id,
        user_id=review_log.user_id,
        struggle_rating=review_log.struggle_rating,
        scheduled_days=review_log.scheduled_days,
        notes=review_log.notes,
        reviewed_at=review_log.reviewed_at,
        next_review_due=problem.next_review_due,
        updated_problem=problem,
    )


@router.get(
    "/{problem_id}/reviews",
    response_model=List[ReviewResponse],
    summary="Get problem revision history",
    description="Returns all historical review sessions for a problem.",
)
def get_problem_reviews(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    problem = problem_service.get_problem(
        db=db, user_id=current_user.id, problem_id=problem_id
    )
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=NOT_FOUND)

    return [
        ReviewResponse(
            id=log.id,
            problem_id=log.problem_id,
            user_id=log.user_id,
            struggle_rating=log.struggle_rating,
            scheduled_days=log.scheduled_days,
            notes=log.notes,
            reviewed_at=log.reviewed_at,
            next_review_due=problem.next_review_due,
        )
        for log in review_service.get_review_history(
            db=db, user_id=current_user.id, problem_id=problem_id
        )
    ]