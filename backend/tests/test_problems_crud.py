"""
CRUD tests for Problems API.
Verifies problem creation, reading, filtering, updating, and deletion.
"""
from fastapi.testclient import TestClient


def test_create_problem_success(client: TestClient, user1: dict):
    """Test saving a problem with notes, solution hints, and difficulty."""
    payload = {
        "url": "https://leetcode.com/problems/two-sum/",
        "title": "Two Sum",
        "topic": "Arrays & Hashing",
        "difficulty": "Easy",
        "notes": "Use a hash map for O(n) time and O(n) space.",
        "solution_or_hints": "Map value to index as you iterate.",
    }
    response = client.post("/api/v1/problems", json=payload, headers=user1["headers"])
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Two Sum"
    assert data["topic"] == "Arrays & Hashing"
    assert data["difficulty"] == "Easy"
    assert data["url"] == "https://leetcode.com/problems/two-sum/"
    assert data["user_id"] == user1["id"]
    assert data["status"] == "active"
    assert data["current_interval_days"] == 1
    assert "id" in data


def test_create_problem_invalid_url(client: TestClient, user1: dict):
    """Test saving a problem with invalid URL format returns 422."""
    payload = {
        "url": "not-a-valid-url",
        "title": "Invalid URL Problem",
        "topic": "Arrays",
        "difficulty": "Medium",
    }
    response = client.post("/api/v1/problems", json=payload, headers=user1["headers"])
    assert response.status_code == 422


def test_create_problem_invalid_difficulty(client: TestClient, user1: dict):
    """Test saving problem with non-enum difficulty returns 422."""
    payload = {
        "url": "https://leetcode.com/problems/valid-anagram/",
        "title": "Valid Anagram",
        "topic": "Arrays",
        "difficulty": "Impossible",
    }
    response = client.post("/api/v1/problems", json=payload, headers=user1["headers"])
    assert response.status_code == 422


def test_get_problem_by_id(client: TestClient, user1: dict):
    """Test retrieving a single problem by ID."""
    create_resp = client.post(
        "/api/v1/problems",
        json={
            "url": "https://leetcode.com/problems/3sum/",
            "title": "3Sum",
            "topic": "Two Pointers",
            "difficulty": "Medium",
            "notes": "Sort array first, then use two pointers.",
        },
        headers=user1["headers"]
    )
    problem_id = create_resp.json()["id"]

    get_resp = client.get(f"/api/v1/problems/{problem_id}", headers=user1["headers"])
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == problem_id
    assert get_resp.json()["title"] == "3Sum"


def test_get_nonexistent_problem(client: TestClient, user1: dict):
    """Test retrieving nonexistent problem returns 404."""
    response = client.get("/api/v1/problems/non-existent-id", headers=user1["headers"])
    assert response.status_code == 404


def test_list_and_filter_problems(client: TestClient, user1: dict):
    """Test listing problems and filtering by topic, difficulty, and search."""
    # Create 3 problems
    problems_data = [
        {"url": "https://leetcode.com/p1", "title": "Invert Binary Tree", "topic": "Trees", "difficulty": "Easy"},
        {"url": "https://leetcode.com/p2", "title": "Maximum Depth of Binary Tree", "topic": "Trees", "difficulty": "Easy"},
        {"url": "https://leetcode.com/p3", "title": "Coin Change", "topic": "Dynamic Programming", "difficulty": "Medium"},
    ]
    for p in problems_data:
        client.post("/api/v1/problems", json=p, headers=user1["headers"])

    # 1. List all
    res_all = client.get("/api/v1/problems", headers=user1["headers"])
    assert res_all.status_code == 200
    assert res_all.json()["total"] == 3

    # 2. Filter by topic
    res_trees = client.get("/api/v1/problems?topic=Trees", headers=user1["headers"])
    assert res_trees.status_code == 200
    assert res_trees.json()["total"] == 2

    # 3. Filter by difficulty
    res_medium = client.get("/api/v1/problems?difficulty=Medium", headers=user1["headers"])
    assert res_medium.status_code == 200
    assert res_medium.json()["total"] == 1
    assert res_medium.json()["items"][0]["title"] == "Coin Change"

    # 4. Search query
    res_search = client.get("/api/v1/problems?search=Coin", headers=user1["headers"])
    assert res_search.status_code == 200
    assert res_search.json()["total"] == 1


def test_update_problem(client: TestClient, user1: dict):
    """Test updating problem title, notes, and status."""
    create_resp = client.post(
        "/api/v1/problems",
        json={
            "url": "https://leetcode.com/problems/lru-cache/",
            "title": "LRU Cache",
            "topic": "Linked List",
            "difficulty": "Hard",
        },
        headers=user1["headers"]
    )
    problem_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/api/v1/problems/{problem_id}",
        json={
            "notes": "Use doubly linked list and hash map.",
            "status": "mastered",
        },
        headers=user1["headers"]
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["notes"] == "Use doubly linked list and hash map."
    assert updated["status"] == "mastered"
    assert updated["title"] == "LRU Cache"  # Unchanged field preserved


def test_delete_problem(client: TestClient, user1: dict):
    """Test deleting problem returns 204 and removes problem."""
    create_resp = client.post(
        "/api/v1/problems",
        json={
            "url": "https://leetcode.com/problems/delete-me/",
            "title": "Temporary Problem",
            "topic": "Math",
            "difficulty": "Easy",
        },
        headers=user1["headers"]
    )
    problem_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/v1/problems/{problem_id}", headers=user1["headers"])
    assert del_resp.status_code == 204

    # Subsequent GET should return 404
    get_resp = client.get(f"/api/v1/problems/{problem_id}", headers=user1["headers"])
    assert get_resp.status_code == 404


def test_create_problem_with_initial_struggle_rating(client: TestClient, user1: dict):
    """Test creating problem with an initial struggle rating automatically sets interval."""
    response = client.post(
        "/api/v1/problems",
        json={
            "url": "https://leetcode.com/problems/daily-temperatures/",
            "title": "Daily Temperatures",
            "topic": "Monotonic Stack",
            "difficulty": "Medium",
            "initial_struggle_rating": "Easy",
        },
        headers=user1["headers"]
    )
    assert response.status_code == 201
    data = response.json()
    assert data["last_struggle_rating"] == "Easy"
    assert data["current_interval_days"] == 3
    assert data["repetitions"] == 1

    # Check review log was created
    reviews = client.get(f"/api/v1/problems/{data['id']}/reviews", headers=user1["headers"]).json()
    assert len(reviews) == 1
    assert reviews[0]["struggle_rating"] == "Easy"


def test_filter_due_only(client: TestClient, user1: dict):
    """Test filtering problems with due_only query flag."""
    # Problem due today
    client.post(
        "/api/v1/problems",
        json={
            "url": "https://leetcode.com/problems/p-due/",
            "title": "Due Problem",
            "topic": "Arrays",
            "difficulty": "Easy",
        },
        headers=user1["headers"]
    )
    # Problem scheduled in 7 days (not due now)
    client.post(
        "/api/v1/problems",
        json={
            "url": "https://leetcode.com/problems/p-future/",
            "title": "Future Problem",
            "topic": "Arrays",
            "difficulty": "Easy",
            "initial_struggle_rating": "Easy",
        },
        headers=user1["headers"]
    )

    resp = client.get("/api/v1/problems?due_only=true", headers=user1["headers"])
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Due Problem"


def test_update_problem_invalid_url(client: TestClient, user1: dict):
    """Test updating problem with invalid URL format returns 422."""
    create_resp = client.post(
        "/api/v1/problems",
        json={
            "url": "https://leetcode.com/problems/valid-url/",
            "title": "Valid URL Problem",
            "topic": "Trees",
            "difficulty": "Medium",
        },
        headers=user1["headers"]
    )
    problem_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/api/v1/problems/{problem_id}",
        json={"url": "not-a-valid-http-url"},
        headers=user1["headers"]
    )
    assert update_resp.status_code == 422

