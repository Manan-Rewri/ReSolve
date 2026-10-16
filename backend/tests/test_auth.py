"""
Authentication tests.
Tests registration, login, token generation, authentication failures, and profile endpoint.
"""
from fastapi.testclient import TestClient


def test_signup_success(client: TestClient):
    """Test successful user registration."""
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "coder@example.com",
            "password": "strongpassword123",
            "full_name": "Test Coder"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "coder@example.com"
    assert data["user"]["full_name"] == "Test Coder"
    assert "id" in data["user"]


def test_signup_duplicate_email(client: TestClient, user1: dict):
    """Test duplicate registration returns HTTP 400."""
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": user1["email"],
            "password": "anotherpassword",
            "full_name": "Duplicate User"
        }
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_signup_invalid_email(client: TestClient):
    """Test registration with invalid email format returns HTTP 422."""
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "not-an-email",
            "password": "validpassword",
        }
    )
    assert response.status_code == 422


def test_signup_short_password(client: TestClient):
    """Test registration with password under 6 characters returns HTTP 422."""
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "short@example.com",
            "password": "123",
        }
    )
    assert response.status_code == 422


def test_login_success(client: TestClient, user1: dict):
    """Test successful login with valid credentials."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user1["email"],
            "password": "password123",
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == user1["email"]


def test_login_wrong_password(client: TestClient, user1: dict):
    """Test login failure on incorrect password returns HTTP 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": user1["email"],
            "password": "wrongpassword",
        }
    )
    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()


def test_login_nonexistent_user(client: TestClient):
    """Test login failure on non-existent email returns HTTP 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "ghost@resolve.dev",
            "password": "anyPassword",
        }
    )
    assert response.status_code == 401


def test_get_me_authenticated(client: TestClient, user1: dict):
    """Test /auth/me returns current user profile when authenticated."""
    response = client.get("/api/v1/auth/me", headers=user1["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user1["id"]
    assert data["email"] == user1["email"]


def test_get_me_unauthenticated(client: TestClient):
    """Test /auth/me returns 401 when no token is provided."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_get_me_invalid_token(client: TestClient):
    """Test /auth/me returns 401 when an invalid token is passed."""
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.value"})
    assert response.status_code == 401


def test_update_me_changes_full_name(client: TestClient, user1: dict):
    response = client.put(
        "/api/v1/auth/me",
        json={"full_name": "Alice Updated"},
        headers=user1["headers"],
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Alice Updated"


def test_update_me_rejects_blank_name(client: TestClient, user1: dict):
    response = client.put(
        "/api/v1/auth/me", json={"full_name": "   "}, headers=user1["headers"]
    )
    assert response.status_code == 422


def test_update_me_requires_auth(client: TestClient):
    assert client.put("/api/v1/auth/me", json={"full_name": "Nobody"}).status_code == 401
