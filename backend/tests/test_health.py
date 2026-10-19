from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, supabase_provider
from app.main import app

client = TestClient(app)


def test_health_is_ok() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "resolve-api"}


def test_root_health_is_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_schema_is_served() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "ReSolve API"


def test_protected_route_rejects_anonymous_caller() -> None:
    """A missing bearer token is rejected before Supabase is ever contacted."""
    probe_app = FastAPI()

    @probe_app.get("/probe")
    async def _probe(user: object = Depends(get_current_user)) -> dict[str, str]:
        return {"id": str(getattr(user, "id", ""))}

    # Stub the Supabase client so the test never needs real credentials.
    probe_app.dependency_overrides[supabase_provider] = lambda: (lambda: None)

    response = TestClient(probe_app).get("/probe")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
