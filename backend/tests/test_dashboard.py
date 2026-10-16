"""
Dashboard API tests.
Verifies aggregation of due today, overdue items, total problems, and upcoming revisions.
"""
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.problem import Problem


def test_dashboard_empty(client: TestClient, user1: dict):
    """Test dashboard for a user with no problems returns zeros."""
    resp = client.get("/api/v1/dashboard", headers=user1["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_saved_problems"] == 0
    assert data["due_today_count"] == 0
    assert data["overdue_count"] == 0
    assert data["mastered_count"] == 0
    assert len(data["due_today"]) == 0
    assert len(data["overdue"]) == 0
    assert len(data["upcoming_revisions"]) == 0


def test_dashboard_due_today_and_overdue(client: TestClient, user1: dict, db_session: Session):
    """Test that problems due today, overdue, and upcoming are categorized correctly."""
    now = datetime.now(timezone.utc)

    # 1. Create a problem due today (default on creation)
    p_today_resp = client.post(
        "/api/v1/problems",
        json={
            "url": "https://leetcode.com/problems/valid-parentheses/",
            "title": "Valid Parentheses",
            "topic": "Stacks",
            "difficulty": "Easy",
        },
        headers=user1["headers"]
    )
    assert p_today_resp.status_code == 201

    # 2. Insert an overdue problem (due 2 days ago) directly into db
    overdue_problem = Problem(
        user_id=user1["id"],
        url="https://leetcode.com/problems/merge-k-sorted-lists/",
        title="Merge k Sorted Lists",
        topic="Heaps",
        difficulty="Hard",
        next_review_due=now - timedelta(days=2),
        current_interval_days=1,
        ease_factor=2.5,
        repetitions=1,
    )
    db_session.add(overdue_problem)

    # 3. Insert an upcoming problem (due in 3 days)
    upcoming_problem = Problem(
        user_id=user1["id"],
        url="https://leetcode.com/problems/number-of-islands/",
        title="Number of Islands",
        topic="Graphs",
        difficulty="Medium",
        next_review_due=now + timedelta(days=3),
        current_interval_days=3,
        ease_factor=2.5,
        repetitions=2,
    )
    db_session.add(upcoming_problem)
    db_session.commit()

    # Call dashboard API
    dash_resp = client.get("/api/v1/dashboard", headers=user1["headers"])
    assert dash_resp.status_code == 200
    data = dash_resp.json()

    assert data["total_saved_problems"] == 3
    assert data["due_today_count"] == 1
    assert data["overdue_count"] == 1
    assert len(data["upcoming_revisions"]) >= 1

    # Verify problem details
    assert data["due_today"][0]["title"] == "Valid Parentheses"
    assert data["overdue"][0]["title"] == "Merge k Sorted Lists"

    # Verify category breakdowns
    assert data["by_topic"]["Stacks"] == 1
    assert data["by_topic"]["Heaps"] == 1
    assert data["by_topic"]["Graphs"] == 1
    assert data["by_difficulty"]["Easy"] == 1
    assert data["by_difficulty"]["Medium"] == 1
    assert data["by_difficulty"]["Hard"] == 1
