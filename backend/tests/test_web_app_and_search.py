import pytest

PAGE_ROUTES = ("/", "/register", "/login", "/home", "/learn", "/settings")


@pytest.fixture
def no_suggestions(monkeypatch):
    async def fake_search(query, limit=8):
        return [
            {
                "frontend_id": "1",
                "title": "Two Sum",
                "title_slug": "two-sum",
                "difficulty": "Easy",
                "topic": "Array",
            }
        ]

    monkeypatch.setattr(
        "app.routers.problems.leetcode_service.search_suggestions", fake_search
    )


def test_search_returns_suggestions(client, no_suggestions):
    resp = client.get("/api/v1/problems/search?q=two")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["title_slug"] == "two-sum"
    assert data[0]["frontend_id"] == "1"


def test_search_requires_a_query(client):
    assert client.get("/api/v1/problems/search").status_code == 422


def test_search_empty_results_is_ok(client, monkeypatch):
    async def fake_search(query, limit=8):
        return []

    monkeypatch.setattr(
        "app.routers.problems.leetcode_service.search_suggestions", fake_search
    )
    resp = client.get("/api/v1/problems/search?q=zzzznotaproblem")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.parametrize("path", PAGE_ROUTES)
def test_page_routes_serve_html(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


@pytest.mark.parametrize(
    "asset",
    [
        "/assets/css/base.css",
        "/assets/css/app.css",
        "/assets/css/landing.css",
        "/assets/css/auth.css",
        "/assets/css/home.css",
        "/assets/css/learn.css",
        "/assets/css/settings.css",
        "/assets/js/core/api.js",
        "/assets/js/core/session.js",
        "/assets/js/core/dom.js",
        "/assets/js/core/format.js",
        "/assets/js/components/navbar.js",
        "/assets/js/components/problem-search.js",
        "/assets/js/pages/landing.js",
        "/assets/js/pages/register.js",
        "/assets/js/pages/login.js",
        "/assets/js/pages/home.js",
        "/assets/js/pages/learn.js",
        "/assets/js/pages/settings.js",
    ],
)
def test_static_assets_are_served(client, asset):
    assert client.get(asset).status_code == 200


def test_old_pages_are_gone(client):
    for path in ("/app", "/import", "/runner"):
        assert client.get(path).status_code == 404


def test_api_info_endpoint(client):
    resp = client.get("/api")
    assert resp.status_code == 200
    assert resp.json()["app_ui"] == "/"