"""The practice scheduler, over the API.

The server owns the rules — the memory curve, when a problem comes back, when
it leaves the sheet — so there is one implementation of the schedule rather
than two that drift apart.

The state lives in Supabase (or the JSON fallback when the project is not
configured). The browser asks for it, rates a problem, and gets the card back;
it never recomputes a schedule and never writes a table directly.
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_user_id
from app.core import problems as catalogue
from app.core import scheduler, store
from app.schemas.practice import (
    ImportRequest,
    ImportResponse,
    PreviewRequest,
    QueueResponse,
    RemovedResponse,
    ScheduleRequest,
    ScheduleResponse,
    SolvedRequest,
    SolvedResponse,
    StateResponse,
    VeryEasyRequest,
)

router = APIRouter(tags=["practice"])


def _now(at: datetime | None) -> datetime:
    return at or datetime.now(UTC)


def _require_problem(slug: str) -> None:
    try:
        catalogue.get_problem(slug)
    except catalogue.ProblemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such problem.",
        ) from exc


@router.get("/practice/state", response_model=StateResponse)
async def practice_state(user_id: Annotated[str, Depends(get_user_id)]) -> StateResponse:
    """Everything the store holds for this user."""
    return StateResponse(**store.read(user_id))


@router.post("/practice/schedule", response_model=ScheduleResponse)
async def schedule_review(
    payload: ScheduleRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> ScheduleResponse:
    """Apply a rating and save the card that comes out the other side.

    The problem's tag is not an input: the rating is the only evidence the
    scheduler uses. The slug is looked up only to refuse one that does not
    exist.

    The previous card is read from the server, not trusted from the client, so
    two tabs cannot rewind each other's schedule.
    """
    _require_problem(payload.slug)

    now = _now(payload.at)
    previous = store.card(user_id, payload.slug)
    card = scheduler.schedule(previous, payload.slug, payload.rating, now)

    store.record_review(user_id, card, payload.rating, now)

    return ScheduleResponse(
        card=card,
        graduated=scheduler.has_graduated(card),
    )


@router.post("/practice/preview", response_model=ScheduleResponse)
async def preview_review(payload: PreviewRequest) -> ScheduleResponse:
    """Apply a rating to a card the caller holds, and store nothing.

    No user is required. Nothing is read and nothing is written, so there is
    nothing to protect: the answer is a pure function of the request and the
    catalogue.
    """
    _require_problem(payload.slug)

    card = scheduler.schedule(
        payload.card,
        payload.slug,
        payload.rating,
        _now(payload.at),
    )
    return ScheduleResponse(card=card, graduated=scheduler.has_graduated(card))


@router.get("/practice/queue", response_model=QueueResponse)
async def practice_queue(
    user_id: Annotated[str, Depends(get_user_id)],
    at: datetime | None = None,
) -> QueueResponse:
    """The problems that are due, most forgotten first.

    This is the queue. A problem that has graduated is never returned.

    The ones that are not due yet come back separately, so you can practise
    ahead of the schedule without pretending they were due.
    """
    now = _now(at)
    cards = [
        scheduler.Card(**raw)
        for raw in store.read(user_id).get("cards", {}).values()
        if isinstance(raw, dict)
    ]
    due = scheduler.next_due(cards, now)
    upcoming = scheduler.next_upcoming(cards, now)
    return QueueResponse(
        slugs=[card.slug for card in due],
        upcoming=[card.slug for card in upcoming],
    )


@router.post("/practice/solved", response_model=SolvedResponse)
async def mark_solved(
    payload: SolvedRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> SolvedResponse:
    """Record whether a problem has been got fully right."""
    _require_problem(payload.slug)
    return SolvedResponse(solved=store.set_solved(user_id, payload.slug, payload.solved))


@router.post("/practice/very-easy", response_model=RemovedResponse)
async def mark_very_easy(
    payload: VeryEasyRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> RemovedResponse:
    """Very easy: this problem does not belong in the practice sheet.

    That is a decision, not a schedule, so the card is removed rather than
    pushed years out. The solved tick stays, because solving a problem and
    scheduling it are different things.
    """
    _require_problem(payload.slug)
    store.remove_card(user_id, payload.slug)
    return RemovedResponse(removed=True)


@router.post("/practice/import", response_model=ImportResponse)
async def import_local_state(
    payload: ImportRequest,
    user_id: Annotated[str, Depends(get_user_id)],
) -> ImportResponse:
    """Move a browser's localStorage bucket into the store, once.

    The browser calls this the first time it signs in after the switch. An
    account that already has rows refuses the import, so a second attempt
    cannot duplicate the review log.
    """
    try:
        store.import_state(user_id, payload.model_dump(mode="json"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return ImportResponse(
        imported=True,
        cards=len(payload.cards),
        solved=len(payload.solved),
        reviews=len(payload.history),
    )
