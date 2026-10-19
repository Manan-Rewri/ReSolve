"""Tests for the problem catalogue and the judge.

Judge0 is stubbed out, so the suite never touches the network. The stubs
replay the submissions the endpoint would make, in order.
"""

import base64

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200
        self.text = ""

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def _fake_judge0(monkeypatch, submissions: list[dict]) -> list[dict]:
    """Replay `submissions`, one per Judge0 call. Returns what was sent."""
    queue = list(submissions)
    sent: list[dict] = []

    class FakeClient:
        def __init__(self, **_kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_args) -> bool:
            return False

        async def post(self, url, params=None, json=None, headers=None):
            sent.append({"url": url, "params": params, "json": json})
            payload = queue.pop(0)
            payload.setdefault("stdout", None)
            payload.setdefault("stderr", None)
            payload.setdefault("compile_output", None)
            return _FakeResponse(payload)

    monkeypatch.setattr("app.api.v1.problems.httpx.AsyncClient", FakeClient)
    return sent


def _accepted(stdout: str) -> dict:
    return {"stdout": _b64(stdout), "status": {"id": 3, "description": "Accepted"}}


# --- the catalogue ----------------------------------------------------------


def test_problems_list_is_the_whole_catalogue() -> None:
    response = client.get("/api/v1/problems")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 50
    # A summary is enough to render and filter the list, and no more.
    assert set(body[0]) == {"slug", "title", "difficulty", "tags"}


def test_problems_list_has_no_duplicates() -> None:
    slugs = [p["slug"] for p in client.get("/api/v1/problems").json()]
    assert len(slugs) == len(set(slugs))


def test_a_problem_carries_everything_the_page_needs() -> None:
    response = client.get("/api/v1/problems/two-sum")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Two Sum"
    assert body["signature"] == "vector<int> twoSum(vector<int>& nums, int target)"
    assert body["examples"]
    assert body["constraints"]
    assert body["statement"].strip()
    # The editor starts as the signature and an empty body, so the user only
    # ever writes the function.
    assert body["editor_start"].startswith(body["signature"])
    assert body["editor_start"].rstrip().endswith("}")


def test_every_problem_has_examples_constraints_and_cases() -> None:
    for problem in client.get("/api/v1/problems").json():
        detail = client.get(f"/api/v1/problems/{problem['slug']}").json()
        assert detail["examples"], problem["slug"]
        assert detail["constraints"], problem["slug"]
        assert detail["statement"].strip(), problem["slug"]

        cases = client.get(f"/api/v1/problems/{problem['slug']}/cases").json()["cases"]
        assert len(cases) >= 20, problem["slug"]
        for case in cases:
            assert case["args"], problem["slug"]
            assert "expected" in case, problem["slug"]


def test_an_unknown_problem_is_a_404() -> None:
    assert client.get("/api/v1/problems/not-a-problem").status_code == 404
    assert client.get("/api/v1/problems/not-a-problem/cases").status_code == 404


# --- the judge --------------------------------------------------------------


def test_judge_reports_every_case(monkeypatch) -> None:
    cases = client.get("/api/v1/problems/two-sum/cases").json()["cases"]

    # The reference output, case by case, so the judge has something to match.
    stdout = "___CASE___\n" + "\n___CASE___\n".join(c["expected"] for c in cases)
    _fake_judge0(monkeypatch, [_accepted(stdout)])

    response = client.post(
        "/api/v1/judge",
        json={"slug": "two-sum", "code": "vector<int> twoSum(vector<int>& a, int b){ return {}; }"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == len(cases)
    assert len(body["cases"]) == len(cases)
    assert body["passed"] == len(cases)
    assert body["status_text"] == "Accepted"


def test_judge_marks_the_failing_cases(monkeypatch) -> None:
    cases = client.get("/api/v1/problems/two-sum/cases").json()["cases"]

    # Every case answers correctly but one.
    answers = [c["expected"] for c in cases]
    answers[2] = "[9,9]"
    stdout = "___CASE___\n" + "\n___CASE___\n".join(answers)
    _fake_judge0(monkeypatch, [_accepted(stdout)])

    response = client.post(
        "/api/v1/judge",
        json={"slug": "two-sum", "code": "vector<int> twoSum(vector<int>& a, int b){ return {}; }"},
    )

    body = response.json()
    assert body["passed"] == len(cases) - 1
    failed = [index for index, c in enumerate(body["cases"]) if not c["passed"]]
    assert failed == [2]
    # The user sees the expected answer and what they actually produced.
    assert body["cases"][2]["expected"] == cases[2]["expected"]
    assert body["cases"][2]["actual"] == "[9,9]"


def test_judge_splices_the_function_into_the_stored_harness(monkeypatch) -> None:
    sent = _fake_judge0(monkeypatch, [_accepted("___CASE___\n[0,1]\n")])

    client.post(
        "/api/v1/judge",
        json={"slug": "two-sum", "code": "vector<int> twoSum(vector<int>& a, int b){ return {}; }"},
    )

    assert len(sent) == 1
    source = base64.b64decode(sent[0]["json"]["source_code"]).decode()

    # The includes and the main are the server's, not the user's.
    assert source.startswith("#include <bits/stdc++.h>")
    assert "int main()" in source
    assert "vector<int> twoSum(vector<int>& a, int b){ return {}; }" in source
    # The user's function is the only thing they wrote.
    assert source.count("int main()") == 1
    assert sent[0]["json"]["language_id"] == 54
    assert sent[0]["params"] == {"base64_encoded": "true", "wait": "true"}


def test_judge_reports_a_compilation_error(monkeypatch) -> None:
    _fake_judge0(
        monkeypatch,
        [
            {
                "compile_output": _b64("main.cpp:5:3: error: expected ';'"),
                "status": {"id": 6, "description": "Compilation Error"},
            }
        ],
    )

    response = client.post(
        "/api/v1/judge",
        json={"slug": "two-sum", "code": "vector<int> twoSum(vector<int>& a, int b){ return {}; "},
    )

    # A compile error is a 200 with the compiler's message, not a 502.
    assert response.status_code == 200
    body = response.json()
    assert body["status_text"] == "Compilation error"
    assert "expected ';'" in body["compile_output"]
    assert body["passed"] == 0


def test_judge_rejects_an_unknown_problem() -> None:
    response = client.post(
        "/api/v1/judge",
        json={"slug": "not-a-problem", "code": "int f(){ return 0; }"},
    )
    assert response.status_code == 404


def test_judge_requires_code() -> None:
    response = client.post("/api/v1/judge", json={"slug": "two-sum", "code": "   "})
    assert response.status_code == 422


def test_judge_rejects_an_oversized_solution() -> None:
    response = client.post(
        "/api/v1/judge",
        json={"slug": "two-sum", "code": "x" * 20_001},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("slug", ["two-sum", "valid-anagram", "climb-stairs"])
def test_the_stored_harness_matches_the_problem(slug: str) -> None:
    """The prefix and suffix must belong to the problem they are stored under."""
    from app.core import problems as catalogue

    problem = catalogue.get_problem(slug)
    function_name = problem["signature"].split("(")[0].split()[-1]

    assert problem["prefix"].startswith("#include <bits/stdc++.h>")
    assert problem["suffix"].count("int main()") == 1
    # The suffix calls the function, so its name has to be in there.
    assert f"{function_name}(" in problem["suffix"]
    # Every stored case is declared in the suffix, so none is dead weight.
    for case in problem["test_cases"]:
        for argument in case["args"]:
            assert argument in problem["suffix"]
