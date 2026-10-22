from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.scheduler import Card

#: The rating the user gives an attempt.
#:
#: Three of them, and no `easy`: "I did not need to practise this again" is
#: not a schedule, it is a decision not to add the problem to the sheet at all,
#: and it belongs to the Learn page rather than to the scheduler.
Rating = Literal["medium", "hard", "extreme"]


class ReviewEvent(BaseModel):
    """One graded review. The dashboard reads these; the scheduler never does."""

    slug: str
    rating: Rating
    at: datetime


class StateResponse(BaseModel):
    """Everything the store holds for one user."""

    cards: dict[str, dict] = Field(default_factory=dict)
    sheet: list[str] = Field(default_factory=list)
    solved: list[str] = Field(default_factory=list)
    history: list[ReviewEvent] = Field(default_factory=list)


class ScheduleRequest(BaseModel):
    """Apply a rating to a card."""

    slug: str = Field(min_length=1, max_length=100)
    rating: Rating
    #: When the review happened. Defaults to now.
    at: datetime | None = None


class ScheduleResponse(BaseModel):
    card: Card
    #: True when the problem has left the practice sheet for good.
    graduated: bool


class PreviewRequest(BaseModel):
    """Apply a rating to a card the caller holds, without storing anything.

    The state now lives in Supabase, so this endpoint is mostly a pure
    scheduler check. It is kept because it is the cheapest way to ask "what
    would this rating do?" without writing a review.
    """

    slug: str = Field(min_length=1, max_length=100)
    rating: Rating
    #: The card as the client last saw it. `None` means a first attempt.
    card: Card | None = None
    #: When the review happened. Defaults to now.
    at: datetime | None = None


class QueueResponse(BaseModel):
    #: The slugs that are due, soonest first.
    slugs: list[str]
    #: The slugs in the sheet that are not due yet, soonest first. You can
    #: practise ahead of the schedule, the way Anki's custom study does.
    upcoming: list[str] = []


class SolvedRequest(BaseModel):
    """Record whether a problem has been got fully right."""

    slug: str = Field(min_length=1, max_length=100)
    solved: bool = True


class SolvedResponse(BaseModel):
    solved: bool


class VeryEasyRequest(BaseModel):
    """Take a problem out of the practice sheet. It is not a schedule."""

    slug: str = Field(min_length=1, max_length=100)


class RemovedResponse(BaseModel):
    removed: bool


class ImportRequest(BaseModel):
    """A browser's localStorage bucket, uploaded once.

    The names match `practice-store.ts` exactly so the client can send its
    state without translating it.
    """

    cards: dict[str, Card] = Field(default_factory=dict)
    solved: list[str] = Field(default_factory=list)
    history: list[ReviewEvent] = Field(default_factory=list)


class ImportResponse(BaseModel):
    imported: bool
    cards: int
    solved: int
    reviews: int
