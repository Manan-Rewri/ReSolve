"""
Spaced Repetition Scheduler tests.
Verifies the Anki/SM-2 spaced repetition calculation logic and review submission API.
"""
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.schemas.problem import StruggleRating
from app.services.scheduler_service import SpacedRepetitionScheduler


def test_scheduler_couldnt_write_a_line_resets():
    """Test that 'Couldn't Write a Line' resets repetitions to 0 and interval to 1 day."""
    result = SpacedRepetitionScheduler.calculate_next_schedule(
        rating=StruggleRating.COULDNT_WRITE_A_LINE,
        current_interval=10,
        ease_factor=2.5,
        repetitions=4,
    )
    assert result.interval_days == 1
    assert result.repetitions == 0
    assert result.ease_factor == 2.30  # Penalized by 0.20


def test_scheduler_hard_progression():
    """Test that 'Hard' slightly scales interval and lowers ease factor."""
    # First repetition
    r1 = SpacedRepetitionScheduler.calculate_next_schedule(
        rating=StruggleRating.HARD,
        current_interval=1,
        ease_factor=2.5,
        repetitions=0,
    )
    assert r1.interval_days == 1
    assert r1.repetitions == 1
    assert r1.ease_factor == 2.35  # Reduced by 0.15

    # Subsequent repetition
    r2 = SpacedRepetitionScheduler.calculate_next_schedule(
        rating=StruggleRating.HARD,
        current_interval=5,
        ease_factor=2.35,
        repetitions=2,
    )
    assert r2.interval_days == 6  # 5 * 1.2 = 6
    assert r2.repetitions == 3
    assert r2.ease_factor == 2.20


def test_scheduler_medium_progression():
    """Test that 'Medium' follows standard SM-2 intervals (1 day -> 3 days -> EF)."""
    # Repetition 0 -> 1 day
    r1 = SpacedRepetitionScheduler.calculate_next_schedule(
        rating=StruggleRating.MEDIUM,
        current_interval=1,
        ease_factor=2.5,
        repetitions=0,
    )
    assert r1.interval_days == 1
    assert r1.repetitions == 1
    assert r1.ease_factor == 2.5

    # Repetition 1 -> 3 days
    r2 = SpacedRepetitionScheduler.calculate_next_schedule(
        rating=StruggleRating.MEDIUM,
        current_interval=r1.interval_days,
        ease_factor=r1.ease_factor,
        repetitions=r1.repetitions,
    )
    assert r2.interval_days == 3
    assert r2.repetitions == 2

    # Repetition 2 -> 3 * 2.5 = 8 days
    r3 = SpacedRepetitionScheduler.calculate_next_schedule(
        rating=StruggleRating.MEDIUM,
        current_interval=r2.interval_days,
        ease_factor=r2.ease_factor,
        repetitions=r2.repetitions,
    )
    assert r3.interval_days == 8
    assert r3.repetitions == 3


def test_scheduler_easy_bonus():
    """Test that 'Easy' provides bonus interval growth and increases ease factor."""
    # Repetition 0 -> 3 days
    r1 = SpacedRepetitionScheduler.calculate_next_schedule(
        rating=StruggleRating.EASY,
        current_interval=1,
        ease_factor=2.5,
        repetitions=0,
    )
    assert r1.interval_days == 3
    assert r1.repetitions == 1
    assert r1.ease_factor == 2.65  # Boosted by 0.15

    # Repetition 1 -> 7 days
    r2 = SpacedRepetitionScheduler.calculate_next_schedule(
        rating=StruggleRating.EASY,
        current_interval=r1.interval_days,
        ease_factor=r1.ease_factor,
        repetitions=r1.repetitions,
    )
    assert r2.interval_days == 7
    assert r2.repetitions == 2


def test_scheduler_ease_factor_minimum_bound():
    """Ensure ease factor cannot fall below the 1.3 floor."""
    result = SpacedRepetitionScheduler.calculate_next_schedule(
        rating=StruggleRating.COULDNT_WRITE_A_LINE,
        current_interval=1,
        ease_factor=1.35,
        repetitions=0,
    )
    assert result.ease_factor == 1.3  # Clamped to min 1.3


def test_submit_review_api_flow(client: TestClient, user1: dict):
    """Test full API review cycle: creation -> review submission -> schedule check -> review history."""
    # 1. Create a problem
    create_resp = client.post(
        "/api/v1/problems",
        json={
            "url": "https://leetcode.com/problems/climbing-stairs/",
            "title": "Climbing Stairs",
            "topic": "Dynamic Programming",
            "difficulty": "Easy",
        },
        headers=user1["headers"]
    )
    problem_id = create_resp.json()["id"]

    # 2. First review: Medium
    rev1 = client.post(
        f"/api/v1/problems/{problem_id}/review",
        json={
            "struggle_rating": "Medium",
            "notes": "Solved using Fibonacci recurrence in O(n) time."
        },
        headers=user1["headers"]
    )
    assert rev1.status_code == 200
    rev1_data = rev1.json()
    assert rev1_data["struggle_rating"] == "Medium"
    assert rev1_data["scheduled_days"] == 1
    assert rev1_data["updated_problem"]["repetitions"] == 1

    # 3. Second review: Medium -> interval should be 3 days
    rev2 = client.post(
        f"/api/v1/problems/{problem_id}/review",
        json={"struggle_rating": "Medium"},
        headers=user1["headers"]
    )
    assert rev2.status_code == 200
    rev2_data = rev2.json()
    assert rev2_data["scheduled_days"] == 3
    assert rev2_data["updated_problem"]["repetitions"] == 2

    # 4. Third review: Couldn't Write a Line -> interval resets to 1 day, reps resets to 0
    rev3 = client.post(
        f"/api/v1/problems/{problem_id}/review",
        json={"struggle_rating": "Couldn't Write a Line", "notes": "Forgot base cases"},
        headers=user1["headers"]
    )
    assert rev3.status_code == 200
    rev3_data = rev3.json()
    assert rev3_data["scheduled_days"] == 1
    assert rev3_data["updated_problem"]["repetitions"] == 0

    # 5. Check review history
    hist_resp = client.get(f"/api/v1/problems/{problem_id}/reviews", headers=user1["headers"])
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) == 3
    # Check that latest review is first
    assert history[0]["struggle_rating"] == "Couldn't Write a Line"
