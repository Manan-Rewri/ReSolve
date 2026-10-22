"""Tests for the practice endpoints.

The state lives on the server now, so each test gets a user of its own and
the tests never see each other's cards.
"""

import itertools
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

NOW = datetime(2026, 10, 19, 9, 0, tzinfo=UTC)

_ids = itertools.count()


@pytest.fixture
def user() -> str:
    """A user of this test's own, so the tests do not share cards."""
    return f"test-user-{next(_ids)}"


def headers(user: str) -> dict[str, str]:
    return {"X-Resolve-User": user}


def rate(user: str, slug: str, rating: str, at: datetime = NOW) -> dict:
    response = client.post(
        "/api/v1/practice/schedule",
        headers=headers(user),
        json={"slug": slug, "rating": rating, "at": at.isoformat()},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_scheduling_a_first_rating_makes_a_card(user: str) -> None:
    body = rate(user, "two-sum", "medium")

    assert body["card"]["slug"] == "two-sum"
    assert body["card"]["stability_days"] == 1.0
    assert body["card"]["state"] == "review"
    assert not body["graduated"]


def test_the_card_is_kept(user: str) -> None:
    rate(user, "two-sum", "medium")

    state = client.get("/api/v1/practice/state", headers=headers(user)).json()
    assert "two-sum" in state["cards"]
    assert state["sheet"] == ["two-sum"]


def test_extreme_comes_back_in_ten_minutes(user: str) -> None:
    card = rate(user, "two-sum", "extreme")["card"]

    assert card["stability_days"] == pytest.approx(10 / (60 * 24), abs=1e-6)
    assert card["lapses"] == 1
    assert card["state"] == "learning"


def test_hard_halves_the_interval(user: str) -> None:
    rate(user, "two-sum", "medium")
    card = rate(user, "two-sum", "hard", NOW + timedelta(days=1))["card"]

    assert card["stability_days"] == 0.5
    assert card["state"] == "learning"


def test_the_problem_tag_does_not_change_the_schedule(user: str) -> None:
    # two-sum is tagged Easy; best-time-to-buy-and-sell-stock is Medium. The
    # same rating must produce the same schedule for both, because the tag is
    # not an input.
    easy = rate(user, "two-sum", "medium")["card"]
    medium = rate(user, "best-time-to-buy-and-sell-stock", "medium")["card"]

    assert easy["stability_days"] == medium["stability_days"]
    assert "difficulty" not in easy


def test_a_problem_that_reaches_the_top_and_is_answered_again_graduates(user: str) -> None:
    at = NOW
    for _ in range(10):
        body = rate(user, "two-sum", "medium", at)
        card = body["card"]
        at = at + timedelta(days=card["stability_days"] + 1)
        if body["graduated"]:
            break

    assert body["graduated"]
    assert card["state"] == "graduated"


def test_a_graduated_problem_leaves_the_sheet(user: str) -> None:
    at = NOW
    for _ in range(10):
        body = rate(user, "two-sum", "medium", at)
        card = body["card"]
        at = at + timedelta(days=card["stability_days"] + 1)
        if body["graduated"]:
            break

    state = client.get("/api/v1/practice/state", headers=headers(user)).json()
    assert state["sheet"] == []


def test_an_unknown_rating_is_refused(user: str) -> None:
    response = client.post(
        "/api/v1/practice/schedule",
        headers=headers(user),
        json={"slug": "two-sum", "rating": "easy"},
    )
    assert response.status_code == 422


def test_an_unknown_problem_is_refused(user: str) -> None:
    response = client.post(
        "/api/v1/practice/schedule",
        headers=headers(user),
        json={"slug": "not-a-problem", "rating": "medium"},
    )
    assert response.status_code == 404


def test_a_caller_with_no_id_is_refused() -> None:
    response = client.get("/api/v1/practice/state")
    assert response.status_code == 401


def test_the_queue_returns_what_is_due(user: str) -> None:
    rate(user, "two-sum", "medium")

    # Not due yet.
    response = client.get(
        "/api/v1/practice/queue",
        headers=headers(user),
        params={"at": NOW.isoformat()},
    )
    assert response.json()["slugs"] == []
    assert response.json()["upcoming"] == ["two-sum"]

    # Due now.
    response = client.get(
        "/api/v1/practice/queue",
        headers=headers(user),
        params={"at": (NOW + timedelta(days=1)).isoformat()},
    )
    assert response.json()["slugs"] == ["two-sum"]


def test_the_queue_leaves_graduated_problems_out(user: str) -> None:
    at = NOW
    for _ in range(10):
        body = rate(user, "two-sum", "medium", at)
        card = body["card"]
        at = at + timedelta(days=card["stability_days"] + 1)
        if body["graduated"]:
            break

    response = client.get(
        "/api/v1/practice/queue",
        headers=headers(user),
        params={"at": (NOW + timedelta(days=4000)).isoformat()},
    )
    assert response.json()["slugs"] == []
    assert response.json()["upcoming"] == []


def test_the_queue_is_empty_for_a_new_user(user: str) -> None:
    response = client.get("/api/v1/practice/queue", headers=headers(user))
    assert response.status_code == 200
    assert response.json()["slugs"] == []


def test_a_solved_problem_is_remembered(user: str) -> None:
    response = client.post(
        "/api/v1/practice/solved",
        headers=headers(user),
        json={"slug": "two-sum", "solved": True},
    )
    assert response.status_code == 200

    state = client.get("/api/v1/practice/state", headers=headers(user)).json()
    assert state["solved"] == ["two-sum"]


def test_a_review_is_recorded_in_the_history(user: str) -> None:
    rate(user, "two-sum", "medium")

    state = client.get("/api/v1/practice/state", headers=headers(user)).json()
    assert len(state["history"]) == 1
    assert state["history"][0]["slug"] == "two-sum"
    assert state["history"][0]["rating"] == "medium"


def test_very_easy_removes_the_card_but_keeps_the_tick(user: str) -> None:
    rate(user, "two-sum", "medium")
    client.post(
        "/api/v1/practice/solved",
        headers=headers(user),
        json={"slug": "two-sum", "solved": True},
    )

    response = client.post(
        "/api/v1/practice/very-easy",
        headers=headers(user),
        json={"slug": "two-sum"},
    )
    assert response.status_code == 200
    assert response.json()["removed"] is True

    state = client.get("/api/v1/practice/state", headers=headers(user)).json()
    assert state["cards"] == {}
    assert state["sheet"] == []
    assert state["solved"] == ["two-sum"]


def test_a_local_bucket_can_be_imported_once(user: str) -> None:
    payload = {
        "cards": {
            "two-sum": {
                "slug": "two-sum",
                "state": "review",
                "stability_days": 1.0,
                "due_at": "2026-10-20T09:00:00Z",
                "reps": 1,
                "lapses": 0,
                "last_rating": "medium",
                "last_reviewed_at": "2026-10-19T09:00:00Z",
            }
        },
        "solved": ["two-sum"],
        "history": [
            {"slug": "two-sum", "rating": "medium", "at": "2026-10-19T09:00:00Z"}
        ],
    }

    response = client.post("/api/v1/practice/import", headers=headers(user), json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["cards"] == 1

    state = client.get("/api/v1/practice/state", headers=headers(user)).json()
    assert list(state["cards"]) == ["two-sum"]
    assert state["sheet"] == ["two-sum"]
    assert state["solved"] == ["two-sum"]
    assert len(state["history"]) == 1

    # A second import must not duplicate the review log.
    again = client.post("/api/v1/practice/import", headers=headers(user), json=payload)
    assert again.status_code == 409


def test_a_solved_problem_can_be_undone(user: str) -> None:
    client.post(
        "/api/v1/practice/solved",
        headers=headers(user),
        json={"slug": "two-sum", "solved": True},
    )
    client.post(
        "/api/v1/practice/solved",
        headers=headers(user),
        json={"slug": "two-sum", "solved": False},
    )

    state = client.get("/api/v1/practice/state", headers=headers(user)).json()
    assert state["solved"] == []


def test_two_users_do_not_see_each_other(user: str) -> None:
    other = f"{user}-other"
    rate(user, "two-sum", "medium")

    state = client.get("/api/v1/practice/state", headers=headers(other)).json()
    assert state["cards"] == {}
    assert state["sheet"] == []


def test_preview_schedules_without_a_user_and_stores_nothing() -> None:
    response = client.post(
        "/api/v1/practice/preview",
        json={"slug": "two-sum", "rating": "medium", "at": NOW.isoformat()},
    )
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["card"]["slug"] == "two-sum"
    assert body["card"]["stability_days"] == 1.0
    assert body["card"]["state"] == "review"
    assert not body["graduated"]

    state = client.get("/api/v1/practice/state", headers=headers("preview-user")).json()
    assert state["cards"] == {}


def test_preview_applies_the_rating_to_the_card_it_is_given() -> None:
    first = client.post(
        "/api/v1/practice/preview",
        json={"slug": "two-sum", "rating": "medium", "at": NOW.isoformat()},
    ).json()["card"]

    second = client.post(
        "/api/v1/practice/preview",
        json={
            "slug": "two-sum",
            "rating": "hard",
            "card": first,
            "at": (NOW + timedelta(days=2)).isoformat(),
        },
    ).json()["card"]

    assert second["stability_days"] == 0.5
    assert second["state"] == "learning"
    assert second["reps"] == first["reps"] + 1


def test_preview_refuses_an_unknown_problem() -> None:
    response = client.post(
        "/api/v1/practice/preview",
        json={"slug": "not-a-problem", "rating": "medium"},
    )
    assert response.status_code == 404
