"""
Data Isolation tests.
Verifies that User A cannot view, modify, delete, or review User B's problems.
"""
from fastapi.testclient import TestClient


def test_user_cannot_access_other_users_problem(client: TestClient, user1: dict, user2: dict):
    """Ensure User 2 cannot access a problem created by User 1."""
    # User 1 creates a problem
    create_resp = client.post(
        "/api/v1/problems",
        json={
            "url": "https://leetcode.com/problems/trapping-rain-water/",
            "title": "Trapping Rain Water",
            "topic": "Two Pointers",
            "difficulty": "Hard",
            "notes": "User 1 private notes on monotonic stack",
        },
        headers=user1["headers"]
    )
    assert create_resp.status_code == 201
    problem_id = create_resp.json()["id"]

    # 1. User 2 GET by ID fails
    get_resp = client.get(f"/api/v1/problems/{problem_id}", headers=user2["headers"])
    assert get_resp.status_code == 404

    # 2. User 2 PUT update fails
    put_resp = client.put(
        f"/api/v1/problems/{problem_id}",
        json={"title": "Hacked Title"},
        headers=user2["headers"]
    )
    assert put_resp.status_code == 404

    # 3. User 2 DELETE fails
    del_resp = client.delete(f"/api/v1/problems/{problem_id}", headers=user2["headers"])
    assert del_resp.status_code == 404

    # 4. User 2 Review fails
    review_resp = client.post(
        f"/api/v1/problems/{problem_id}/review",
        json={"struggle_rating": "Easy"},
        headers=user2["headers"]
    )
    assert review_resp.status_code == 404

    # 5. User 2 Review history fails
    reviews_hist = client.get(f"/api/v1/problems/{problem_id}/reviews", headers=user2["headers"])
    assert reviews_hist.status_code == 404

    # 6. User 2 problem list does not contain User 1's problem
    list_resp = client.get("/api/v1/problems", headers=user2["headers"])
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 0
    assert len(list_resp.json()["items"]) == 0

    # 7. User 2 dashboard metrics isolate counts
    dash_resp = client.get("/api/v1/dashboard", headers=user2["headers"])
    assert dash_resp.status_code == 200
    assert dash_resp.json()["total_saved_problems"] == 0

    # Verify User 1's problem was untouched
    verify_resp = client.get(f"/api/v1/problems/{problem_id}", headers=user1["headers"])
    assert verify_resp.status_code == 200
    assert verify_resp.json()["title"] == "Trapping Rain Water"
