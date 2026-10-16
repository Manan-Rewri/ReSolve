"""
Pytest configuration and fixtures.
Configures isolated test database and authenticated test clients.
"""
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.services.auth_service import auth_service
from app.schemas.auth import UserSignUp

# Use an in-memory SQLite database for fast, isolated tests
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create fresh tables for each test and drop them after."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def user1(db_session: Session) -> dict:
    """Creates first test user and returns user info + auth headers."""
    signup_data = UserSignUp(
        email="alice@resolve.dev",
        password="password123",
        full_name="Alice Algorithm",
    )
    user = auth_service.register_user(db_session, signup_data)
    token = auth_service.create_access_token(data={"sub": user.id})
    return {
        "user": user,
        "id": user.id,
        "email": user.email,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture(scope="function")
def user2(db_session: Session) -> dict:
    """Creates second test user for data isolation testing."""
    signup_data = UserSignUp(
        email="bob@resolve.dev",
        password="secretpassword",
        full_name="Bob Backtracker",
    )
    user = auth_service.register_user(db_session, signup_data)
    token = auth_service.create_access_token(data={"sub": user.id})
    return {
        "user": user,
        "id": user.id,
        "email": user.email,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }
