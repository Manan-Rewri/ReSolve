"""The memory curve.

This is the part of ReSolve that is not a LeetCode clone.

## One number per card

Every card carries a **stability**, in days: the time at which your chance of
still recalling the problem has decayed to **90%**.

    recall(t) = 0.9 ** (t / stability)

A card is scheduled for exactly `t = stability` — the moment it reaches the
edge of forgetting. Nothing else in the product decides when a problem comes
back.

## Three rules

A review updates stability by exactly one of three factors:

| Rating    | What it means            | Stability          |
| --------- | ------------------------ | ------------------ |
| `medium`  | solved it, but it was work | **x 2** (at least a day) |
| `hard`    | barely got there          | **x 0.5** (at least ten minutes) |
| `extreme` | read the solution         | **reset** to ten minutes, counts a lapse |

A clean solve says the memory is stronger than we thought, so it lasts twice
as long. A shaky solve says it is weaker than we thought, so it lasts half as
long — the card comes back sooner until a clean pass raises the estimate.
Reading the solution is not a retrieval at all, so the estimate is replaced.

The **first** review has no estimate to update, so it sets one: a clean first
solve is back tomorrow, a shaky one in six hours, and one that needed the
solution in ten minutes.

## Retirement

When a clean solve pushes stability to **90 days (three months)**, the card
retires: it has lasted the longest interval the product schedules, so it
leaves the practice sheet. Nothing retires by accident — only a `medium` can
retire a card, and only after it has doubled its way to three months.

If a retired problem is attempted again and rated `hard` or `extreme`, it
comes back: the estimate was wrong, so it starts over.

## The problem's difficulty is not an input

The Easy / Medium / Hard tag on a problem is a community label. It says
nothing about how hard that problem was *for you*, and using it to set a
ceiling would conflate two different axes (see `AGENTS.md` §2). The rating is
the only evidence this scheduler trusts. A problem tagged Hard that you keep
solving cleanly retires just like an Easy one; a problem tagged Easy that you
keep fumbling stays on your sheet for as long as it needs to.

Pure logic: a card, a rating, and the card that comes out the other side. No
I/O and no clock of its own — the caller passes the time in, so it is all
testable.
"""

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel

Rating = Literal["medium", "hard", "extreme"]

#: The shortest interval the scheduler will ever set: ten minutes.
MIN_STABILITY = timedelta(minutes=10)

#: The interval a first clean solve gets: one day.
FIRST_CLEAN = timedelta(days=1)

#: The interval a first shaky solve gets: six hours.
FIRST_SHAKY = timedelta(hours=6)

#: A clean solve multiplies stability by this.
CLEAN_GROWTH = 2.0

#: A shaky solve multiplies stability by this.
SHAKY_GROWTH = 0.5

#: A card that reaches this stability retires: three months.
RETIRE_AFTER = timedelta(days=90)

#: The card states, matching the glossary in AGENTS.md.
State = Literal["new", "learning", "review", "graduated"]


class Card(BaseModel):
    """The per-(user, problem) scheduler record."""

    slug: str
    state: State = "new"
    #: Days until recall is predicted to fall to 90%. The interval.
    stability_days: float = FIRST_CLEAN.total_seconds() / 86_400
    #: When the problem comes back.
    due_at: datetime
    #: How many times it has been reviewed.
    reps: int = 0
    #: How many times the solution was read instead of the problem solved.
    lapses: int = 0
    last_rating: Rating | None = None
    last_reviewed_at: datetime | None = None


def _days(value: timedelta) -> float:
    return value.total_seconds() / 86_400


def _timedelta(days: float) -> timedelta:
    return timedelta(days=days)


def first_stability(rating: str) -> float:
    """The estimate the first review establishes, before any history exists."""
    if rating == "extreme":
        return _days(MIN_STABILITY)
    if rating == "hard":
        return _days(FIRST_SHAKY)
    return _days(FIRST_CLEAN)


def schedule(card: Card | None, slug: str, rating: str, now: datetime) -> Card:
    """Apply a rating and return the card that comes out the other side."""
    if rating not in ("medium", "hard", "extreme"):
        raise ValueError(
            f"Unknown rating {rating!r}. Expected medium, hard or extreme."
        )

    reps = (card.reps if card else 0) + 1
    lapses = card.lapses if card else 0
    previous = card.stability_days if card else None

    if rating == "extreme":
        stability = _days(MIN_STABILITY)
        lapses += 1
    elif previous is None:
        # The first review has nothing to scale, so it establishes the estimate.
        stability = first_stability(rating)
    elif rating == "hard":
        stability = max(previous * SHAKY_GROWTH, _days(MIN_STABILITY))
    else:  # medium
        stability = max(previous * CLEAN_GROWTH, _days(FIRST_CLEAN))

    # A retired card that comes back shaky starts over rather than halving an
    # estimate that only looks large because it was never tested again.
    if card is not None and card.state == "graduated" and rating != "medium":
        stability = first_stability(rating)

    interval = _timedelta(stability)
    graduated = rating == "medium" and interval >= RETIRE_AFTER

    if graduated:
        state: State = "graduated"
    elif interval < FIRST_CLEAN:
        state = "learning"
    else:
        state = "review"

    return Card(
        slug=slug,
        state=state,
        stability_days=round(stability, 6),
        due_at=now + interval,
        reps=reps,
        lapses=lapses,
        last_rating=rating,  # type: ignore[arg-type]
        last_reviewed_at=now,
    )


def recall(card: Card, now: datetime) -> float:
    """The predicted chance the user still remembers this, between 0 and 1.

    At `due_at` this is 0.9; each stability-period beyond that multiplies it by
    0.9 again. This is what the queue orders on: the most forgotten first.
    """
    if card.last_reviewed_at is None or card.stability_days <= 0:
        return 1.0

    elapsed = (now - card.last_reviewed_at).total_seconds() / 86_400
    return 0.9 ** (elapsed / card.stability_days)


def is_due(card: Card, now: datetime) -> bool:
    """Is this problem due for practice?"""
    return card.state != "graduated" and card.due_at <= now


def has_graduated(card: Card) -> bool:
    """Has the problem left the practice sheet for good?"""
    return card.state == "graduated"


def next_due(cards: list[Card], now: datetime) -> list[Card]:
    """The problems that are due, most forgotten first.

    Ordering on predicted recall rather than on the clock is deliberate: a card
    with a one-day interval that is two days late is in worse shape than a card
    with a thirty-day interval that is one day late, and the queue should say so.
    """
    due = [card for card in cards if is_due(card, now)]
    return sorted(due, key=lambda card: (recall(card, now), card.slug))


def next_upcoming(cards: list[Card], now: datetime) -> list[Card]:
    """The cards not due yet, the one closest to being forgotten first."""
    later = [card for card in cards if card.state != "graduated" and card.due_at > now]
    return sorted(later, key=lambda card: (recall(card, now), card.slug))


__all__ = [
    "CLEAN_GROWTH",
    "FIRST_CLEAN",
    "FIRST_SHAKY",
    "MIN_STABILITY",
    "RETIRE_AFTER",
    "SHAKY_GROWTH",
    "Card",
    "Rating",
    "State",
    "first_stability",
    "has_graduated",
    "is_due",
    "next_due",
    "next_upcoming",
    "recall",
    "schedule",
]
