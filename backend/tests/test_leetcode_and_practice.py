"""
Tests for LeetCode import and Daily Practice prioritization queue.
"""
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient


def test_fetch_leetcode_problem_by_title(client: TestClient):
    """Test fetching full question description from LeetCode by title."""
    response = client.post(
        "/api/v1/problems/fetch-leetcode",
        json={"title_or_url": "Two Sum"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Two Sum"
    assert data["title_slug"] == "two-sum"
    assert data["frontend_id"] == "1"
    assert data["difficulty"] == "Easy"
    assert "Array" in data["all_topics"] or "Hash Table" in data["all_topics"]
    assert "content_html" in data
    assert len(data["content_html"]) > 50
    assert "content_text" in data
    assert "nums" in data["content_text"]


def test_fetch_leetcode_problem_by_url(client: TestClient):
    """Test fetching question by full LeetCode problem URL."""
    response = client.post(
        "/api/v1/problems/fetch-leetcode",
        json={"title_or_url": "https://leetcode.com/problems/trapping-rain-water/description/"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title_slug"] == "trapping-rain-water"
    assert data["difficulty"] == "Hard"


def test_fetch_leetcode_not_found(client: TestClient):
    """Test fetching nonexistent problem returns 404."""
    response = client.post(
        "/api/v1/problems/fetch-leetcode",
        json={"title_or_url": "this-problem-definitely-does-not-exist-xyz123456"}
    )
    assert response.status_code == 404


def test_daily_practice_queue_prioritization(client: TestClient, user1: dict):
    """
    Test that the ReSolve algorithm orders daily practice questions with:
    Category 4 ("Didn't find the solution?") having highest priority,
    followed by Hard, Medium, and finally Easy.
    """
    # Create 4 problems with different ratings
    problems = [
        {"title": "Easy Problem", "url": "https://leetcode.com/p1", "topic": "Arrays", "difficulty": "Easy", "rating": "Easy"},
        {"title": "Medium Problem", "url": "https://leetcode.com/p2", "topic": "Arrays", "difficulty": "Medium", "rating": "Medium"},
        {"title": "Hard Problem", "url": "https://leetcode.com/p3", "topic": "Arrays", "difficulty": "Hard", "rating": "Hard"},
        {"title": "Stuck Problem", "url": "https://leetcode.com/p4", "topic": "Arrays", "difficulty": "Hard", "rating": "Didn't find the solution?"},
    ]

    for p in problems:
        create_resp = client.post(
            "/api/v1/problems",
            json={
                "url": p["url"],
                "title": p["title"],
                "topic": p["topic"],
                "difficulty": p["difficulty"],
                "initial_struggle_rating": p["rating"]
            },
            headers=user1["headers"]
        )
        assert create_resp.status_code == 201

    # Request daily practice queue
    practice_resp = client.get("/api/v1/problems/daily-practice", headers=user1["headers"])
    assert practice_resp.status_code == 200
    queue = practice_resp.json()
    assert len(queue) >= 4

    # The first item MUST be the Category 4 ("Didn't find the solution?") question
    assert queue[0]["title"] == "Stuck Problem"
    assert queue[0]["last_struggle_rating"] == "Didn't find the solution?"
    assert queue[0]["practice_priority"] == 4

    # The second item should be Hard (Priority 3)
    assert queue[1]["title"] == "Hard Problem"
    assert queue[1]["last_struggle_rating"] == "Hard"
    assert queue[1]["practice_priority"] == 3

    # The third item should be Medium (Priority 2)
    assert queue[2]["title"] == "Medium Problem"
    assert queue[2]["last_struggle_rating"] == "Medium"
    assert queue[2]["practice_priority"] == 2

    # The fourth item should be Easy (Priority 1)
    assert queue[3]["title"] == "Easy Problem"
    assert queue[3]["last_struggle_rating"] == "Easy"
    assert queue[3]["practice_priority"] == 1
