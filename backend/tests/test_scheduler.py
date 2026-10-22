"""Tests for the memory curve.

The rules are deliberately few, so the tests are about the rules and not about
particular interval numbers:

    medium  -> twice as long, at least a day
    hard    -> half as long, at least ten minutes
    extreme -> ten minutes, and counts a lapse
    retired -> three months of stability

"""

from datetime import datetime, timedelta

import pytest

from app.core.scheduler import (
    MIN_STABILITY,
    RETIRE_AFTER,
    Card,
    has_graduated,
    is_due,
    next_due,
    next_upcoming,
    recall,
    schedule,
)

NOW = datetime(2026, 10, 19, 9, 0, 0)
DAY = timedelta(days=1)
TEN_MINUTES = timedelta(minutes=10)


def test_a_first_clean_solve_comes_back_tomorrow() -> None:
    card = schedule(None, "two-sum", "medium", NOW)

    assert card.stability_days == 1.0
    assert card.due_at == NOW + DAY
    assert card.reps == 1
    assert card.state == "review"


def test_a_first_shaky_solve_comes_back_today() -> None:
    card = schedule(None, "two-sum", "hard", NOW)

    assert card.due_at == NOW + timedelta(hours=6)
    assert card.state == "learning"
    assert card.lapses == 0


def test_reading_the_solution_comes_back_in_ten_minutes() -> None:
    card = schedule(None, "two-sum", "extreme", NOW)

    assert card.due_at == NOW + TEN_MINUTES
    assert card.stability_days == pytest.approx(10 / (60 * 24), abs=1e-6)
    assert card.lapses == 1
    assert card.state == "learning"


def test_a_clean_solve_doubles_the_interval() -> None:
    card = schedule(None, "two-sum", "medium", NOW)
    card = schedule(card, "two-sum", "medium", NOW + DAY)
    assert card.due_at == NOW + DAY + DAY * 2

    card = schedule(card, "two-sum", "medium", NOW + DAY * 3)
    assert card.stability_days == 4.0
    assert card.reps == 3


def test_a_shaky_solve_halves_the_interval() -> None:
    card = Card(
        slug="two-sum",
        state="review",
        stability_days=16.0,
        due_at=NOW,
        reps=5,
        last_reviewed_at=NOW - timedelta(days=16),
    )

    card = schedule(card, "two-sum", "hard", NOW)

    assert card.stability_days == 8.0
    assert card.due_at == NOW + timedelta(days=8)
    assert card.state == "review"


def test_a_shaky_solve_never_goes_below_ten_minutes() -> None:
    card = schedule(None, "two-sum", "extreme", NOW)
    card = schedule(card, "two-sum", "hard", NOW + TEN_MINUTES)
    card = schedule(card, "two-sum", "hard", NOW + TEN_MINUTES * 2)

    assert card.stability_days == pytest.approx(10 / (60 * 24), abs=1e-6)
    assert card.due_at == NOW + TEN_MINUTES * 3


def test_a_clean_solve_never_comes_back_sooner_than_a_day() -> None:
    card = schedule(None, "two-sum", "extreme", NOW)
    card = schedule(card, "two-sum", "medium", NOW + TEN_MINUTES)

    assert card.stability_days == 1.0
    assert card.due_at == NOW + TEN_MINUTES + DAY


def test_the_problem_tag_is_not_an_input() -> None:
    # Two problems with different community tags, the same ratings, get the
    # same schedule: only the user's own rating moves the estimate.
    one = schedule(None, "an-easy-problem", "medium", NOW)
    two = schedule(None, "a-hard-problem", "medium", NOW)

    assert one.stability_days == two.stability_days
    assert one.due_at == two.due_at


def test_a_clean_solve_that_reaches_three_months_retires_the_card() -> None:
    card = schedule(None, "two-sum", "medium", NOW)
    answers = 1

    while not has_graduated(card) and answers < 20:
        card = schedule(card, "two-sum", "medium", NOW)
        answers += 1

    assert has_graduated(card)
    assert card.due_at - NOW >= RETIRE_AFTER
    assert answers == 8  # 1, 2, 4, 8, 16, 32, 64, then 128


def test_a_shaky_solve_never_retires_a_card() -> None:
    card = schedule(None, "two-sum", "medium", NOW)
    for _ in range(20):
        card = schedule(card, "two-sum", "hard", NOW)

    assert not has_graduated(card)
    assert card.state == "learning"


def test_a_retired_problem_is_never_due_again() -> None:
    card = Card(
        slug="two-sum",
        state="graduated",
        stability_days=128.0,
        due_at=NOW,
        reps=7,
        last_reviewed_at=NOW - timedelta(days=128),
    )

    assert not is_due(card, NOW + timedelta(days=3650))
    assert next_due([card], NOW + timedelta(days=3650)) == []
    assert next_upcoming([card], NOW) == []


def test_a_retired_problem_comes_back_if_you_read_the_solution() -> None:
    card = Card(
        slug="two-sum",
        state="graduated",
        stability_days=128.0,
        due_at=NOW,
        reps=7,
        last_reviewed_at=NOW - timedelta(days=128),
    )

    card = schedule(card, "two-sum", "extreme", NOW)

    assert not has_graduated(card)
    assert card.stability_days == pytest.approx(10 / (60 * 24), abs=1e-6)
    assert card.lapses == 1
    assert is_due(card, NOW + TEN_MINUTES)


def test_a_retired_problem_stays_retired_if_you_still_know_it() -> None:
    card = Card(
        slug="two-sum",
        state="graduated",
        stability_days=128.0,
        due_at=NOW,
        reps=7,
        last_reviewed_at=NOW - timedelta(days=128),
    )

    card = schedule(card, "two-sum", "medium", NOW)

    assert has_graduated(card)


def test_recall_starts_at_one_and_is_ninety_percent_when_due() -> None:
    card = schedule(None, "two-sum", "medium", NOW)

    assert recall(card, NOW) == pytest.approx(1.0)
    assert recall(card, NOW + DAY) == pytest.approx(0.9)
    assert recall(card, NOW + DAY * 2) == pytest.approx(0.81)


def test_recall_is_one_until_a_card_has_been_reviewed() -> None:
    card = Card(slug="two-sum", due_at=NOW)

    assert recall(card, NOW + timedelta(days=400)) == 1.0


def test_the_queue_puts_the_most_forgotten_first() -> None:
    # "Most overdue" is measured in how much has been forgotten, not in days:
    # a one-day card three days late is in worse shape than a month-long card
    # one day late.
    cards = [
        schedule(None, "recent", "medium", NOW - timedelta(days=2)),
        Card(
            slug="mature",
            state="review",
            stability_days=30.0,
            due_at=NOW,
            reps=5,
            last_reviewed_at=NOW - timedelta(days=30),
        ),
        schedule(None, "stale", "medium", NOW - timedelta(days=4)),
    ]

    queue = next_due(cards, NOW)

    assert [card.slug for card in queue] == ["stale", "recent", "mature"]


def test_the_upcoming_queue_is_the_rest_of_the_sheet() -> None:
    due = schedule(None, "due", "medium", NOW - timedelta(days=1))
    later = schedule(None, "later", "medium", NOW)

    assert [card.slug for card in next_due([due, later], NOW)] == ["due"]
    assert [card.slug for card in next_upcoming([due, later], NOW)] == ["later"]


def test_the_queue_breaks_ties_stably() -> None:
    cards = [
        schedule(None, "zebra", "medium", NOW - timedelta(days=1)),
        schedule(None, "apple", "medium", NOW - timedelta(days=1)),
    ]
    assert [card.slug for card in next_due(cards, NOW)] == ["apple", "zebra"]


def test_an_unknown_rating_is_refused() -> None:
    with pytest.raises(ValueError):
        schedule(None, "two-sum", "brilliant", NOW)
    with pytest.raises(ValueError):
        schedule(None, "two-sum", "easy", NOW)


def test_a_card_survives_a_round_trip() -> None:
    card = schedule(None, "two-sum", "extreme", NOW)
    assert Card.model_validate(card.model_dump()) == card


def test_the_shortest_interval_is_ten_minutes() -> None:
    assert MIN_STABILITY == TEN_MINUTES
