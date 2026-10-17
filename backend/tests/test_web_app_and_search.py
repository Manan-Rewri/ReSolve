import pytest

PAGE_ROUTES = ("/", "/register", "/login", "/home", "/learn", "/settings")


@pytest.fixture
def no_suggestions(monkeypatch):
    async def fake_search(query, limit=8, sheet_id=None):
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
    async def fake_search(query, limit=8, sheet_id=None):
        return []

    monkeypatch.setattr(
        "app.routers.problems.leetcode_service.search_suggestions", fake_search
    )
    resp = client.get("/api/v1/problems/search?q=zzzznotaproblem")
    assert resp.status_code == 200
    assert resp.json() == []


def test_sheets_endpoint_lists_practice_sheets(client):
    resp = client.get("/api/v1/problems/sheets")
    assert resp.status_code == 200
    ids = {sheet["id"] for sheet in resp.json()}
    assert {"all", "striver", "leetcode"} <= ids


def test_sheet_filter_narrows_suggestions(client, monkeypatch):
    async def fake_rows(query, limit):
        return [
            {
                "questionFrontendId": "1",
                "title": "Two Sum",
                "titleSlug": "two-sum",
                "difficulty": "Easy",
                "topicTags": [{"name": "Array"}],
            },
            {
                "questionFrontendId": "1234",
                "title": "Dashboard Design",
                "titleSlug": "dashboard-design",
                "difficulty": "Medium",
                "topicTags": [{"name": "Design"}],
            },
        ]

    monkeypatch.setattr(
        "app.services.leetcode_client.search_question_suggestions", fake_rows
    )

    from app.services.leetcode_service import leetcode_service
    from app.services.sheets import LEETCODE_DSA

    assert "two-sum" in LEETCODE_DSA
    assert "dashboard-design" not in LEETCODE_DSA

    scoped = await_run(leetcode_service.search_suggestions("two", limit=8, sheet_id="leetcode"))
    assert [s["title_slug"] for s in scoped] == ["two-sum"]

    unscoped = await_run(leetcode_service.search_suggestions("two", limit=8))
    assert len(unscoped) == 2

    unknown = await_run(leetcode_service.search_suggestions("two", limit=8, sheet_id="nope"))
    assert len(unknown) == 2


DATABASE_ROWS = [
    {"frontend_id": "1", "title": "Two Sum", "difficulty": "Easy", "topic": "Array"},
    {"frontend_id": "2", "title": "Add Two Numbers", "difficulty": "Medium", "topic": "Linked List"},
    {"frontend_id": "3", "title": "SQL Queries", "difficulty": "Hard", "topic": "Database"},
]


def test_search_excludes_database_problems(client, monkeypatch):
    async def fake_rows(query, limit):
        return [
            {
                "questionFrontendId": row["frontend_id"],
                "title": row["title"],
                "titleSlug": row["title"].lower().replace(" ", "-"),
                "difficulty": row["difficulty"],
                "topicTags": [{"name": row["topic"]}],
            }
            for row in DATABASE_ROWS
        ]

    monkeypatch.setattr(
        "app.services.leetcode_client.search_question_suggestions", fake_rows
    )

    from app.services.leetcode_service import leetcode_service

    results = await_run(leetcode_service.search_suggestions("two", limit=8))
    titles = [item["title"] for item in results]

    assert "Two Sum" in titles
    assert "Add Two Numbers" in titles
    assert "SQL Queries" not in titles


def test_search_excludes_keyword_matches_without_database_tag(client, monkeypatch):
    from app.services.leetcode_service import _is_dsa_problem

    assert _is_dsa_problem("Two Sum", ["Array"]) is True
    assert _is_dsa_problem("Design an Online SQL Query Builder", ["Database"]) is False
    # Caught by title keyword even when LeetCode omits the Database tag.
    assert _is_dsa_problem("SQL Executor", ["Concurrency"]) is False
    # Untagged rows are LeetCode's SQL / pandas tracks, not DSA.
    assert _is_dsa_problem("Select Data", []) is False
    assert _is_dsa_problem("Reshape Data: Pivot", []) is False
    # Bare "query" must stay allowed: "Range Sum Query - Immutable" is real DSA.
    assert _is_dsa_problem("Range Sum Query - Immutable", ["Array"]) is True
    # The Database tag counts even when it is not the first tag.
    assert _is_dsa_problem("Swap Digits", ["Math", "Database"]) is False


def await_run(coro):
    import asyncio

    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def test_extract_examples_returns_all_pairs(client):
    from app.services.leetcode_service import extract_examples

    html = (
        "<pre><strong>Input:</strong> nums = [2,7,11,15], n = 9\n"
        "<strong>Output:</strong> [0,1]\n<strong>Explanation:</strong> why</pre>"
        "<p><strong>Example 2:</strong></p>"
        "<pre><strong>Input:</strong> nums = [3,2,4], n = 6\n"
        "<strong>Output:</strong> [1,2]\n<strong>Explanation:</strong> why</pre>"
    )
    examples = extract_examples(html)
    assert len(examples) == 2
    assert examples[0] == {"input": "nums = [2,7,11,15], n = 9", "output": "[0,1]"}
    assert examples[1] == {"input": "nums = [3,2,4], n = 6", "output": "[1,2]"}


def test_extract_examples_caps_at_five(client):
    from app.services.leetcode_service import extract_examples

    block = "<pre><strong>Input:</strong> a = 1\n<strong>Output:</strong> 1</pre>"
    assert len(extract_examples(block * 8)) == 5


def test_extract_examples_returns_empty_without_labels(client):
    from app.services.leetcode_service import extract_examples

    assert extract_examples("<p>See the image above.</p>") == []
    assert extract_examples("") == []


def test_extract_expected_output_from_first_example(client):
    from app.services.leetcode_service import extract_expected_output

    html = (
        "<p><strong>Example 1:</strong></p><pre>"
        "<strong>Input:</strong> nums = [2,7,11,15], n = 9\n"
        "<strong>Output:</strong> [0,1]\n"
        "<strong>Explanation:</strong> Because nums[0] + nums[1] == 9."
        "</pre>"
    )
    assert extract_expected_output(html) == "[0,1]"


def test_extract_expected_output_handles_missing_label(client):
    from app.services.leetcode_service import extract_expected_output

    assert extract_expected_output("<p>No examples here.</p>") is None
    assert extract_expected_output("") is None


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
        "/assets/css/search.css",
        "/assets/css/learn.css",
        "/assets/css/settings.css",
        "/assets/js/core/api.js",
        "/assets/js/core/session.js",
        "/assets/js/core/dom.js",
        "/assets/js/core/format.js",
        "/assets/js/core/sheets.js",
        "/assets/js/core/templates.js",
        "/assets/js/components/navbar.js",
        "/assets/js/components/problem-search.js",
        "/assets/js/components/sheet-select.js",
        "/assets/js/components/toast.js",
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