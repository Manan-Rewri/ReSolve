from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.schemas.problem import StruggleRating

MIN_EASE_FACTOR = 1.3
MAX_EASE_FACTOR = 3.5
DEFAULT_EASE_FACTOR = 2.5

LAPSE_EASE_PENALTY = 0.20
HARD_EASE_PENALTY = 0.15
EASY_EASE_BONUS = 0.15
HARD_INTERVAL_GROWTH = 1.2
EASY_INTERVAL_BONUS = 1.3


@dataclass
class ScheduleResult:
    interval_days: int
    ease_factor: float
    repetitions: int
    next_review_due: datetime


def _ramp(
    repetitions: int, current_interval: int, first: int, second: int, growth: float
) -> int:
    """First two successful reviews use fixed intervals, then grow by `growth`."""
    if repetitions <= 0:
        return first
    if repetitions == 1:
        return second
    return max(1, int(round(current_interval * growth)))


def _clamp_ease(ease_factor: float, delta: float, maximum: bool = False) -> float:
    adjusted = round(ease_factor + delta, 2)
    return (
        min(MAX_EASE_FACTOR, adjusted) if maximum else max(MIN_EASE_FACTOR, adjusted)
    )


class SpacedRepetitionScheduler:
    """Anki-inspired SM-2 scheduling tuned for DSA recall.

    A lapse ("Didn't find the solution?" / "Couldn't Write a Line") resets the
    streak to 1 day and drops ease. Hard grows the interval slowly and drops
    ease slightly. Medium is standard SM-2. Easy grows aggressively and rewards
    ease. Higher ease means longer future intervals.
    """

    @classmethod
    def calculate_next_schedule(
        cls,
        rating: StruggleRating,
        current_interval: int = 1,
        ease_factor: float = DEFAULT_EASE_FACTOR,
        repetitions: int = 0,
        reviewed_at: Optional[datetime] = None,
    ) -> ScheduleResult:
        reviewed_at = reviewed_at or datetime.now(timezone.utc)
        current_interval = max(1, current_interval)
        ease_factor = max(MIN_EASE_FACTOR, ease_factor)

        if rating in (
            StruggleRating.DIDNT_FIND_SOLUTION,
            StruggleRating.COULDNT_WRITE_A_LINE,
        ):
            new_repetitions, new_interval = 0, 1
            new_ease = _clamp_ease(ease_factor, -LAPSE_EASE_PENALTY)

        elif rating == StruggleRating.HARD:
            new_repetitions = repetitions + 1
            new_interval = _ramp(
                repetitions, current_interval, 1, 2, HARD_INTERVAL_GROWTH
            )
            new_ease = _clamp_ease(ease_factor, -HARD_EASE_PENALTY)

        elif rating == StruggleRating.MEDIUM:
            new_repetitions = repetitions + 1
            new_interval = _ramp(
                repetitions, current_interval, 1, 3, ease_factor
            )
            new_ease = ease_factor

        elif rating == StruggleRating.EASY:
            new_repetitions = repetitions + 1
            new_interval = _ramp(
                repetitions,
                current_interval,
                3,
                7,
                ease_factor * EASY_INTERVAL_BONUS,
            )
            new_ease = _clamp_ease(ease_factor, EASY_EASE_BONUS, maximum=True)

        else:
            new_repetitions = repetitions
            new_interval = current_interval
            new_ease = ease_factor

        return ScheduleResult(
            interval_days=new_interval,
            ease_factor=new_ease,
            repetitions=new_repetitions,
            next_review_due=reviewed_at + timedelta(days=new_interval),
        )


scheduler = SpacedRepetitionScheduler()