import base64

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 201

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def _fake_client(monkeypatch, payload: dict, expect: dict | None = None) -> None:
    class FakeClient:
        def __init__(self, **_kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *_args) -> bool:
            return False

        async def post(self, url, params=None, json=None, headers=None):
            # `is not None`, not truthiness — an empty dict is falsy.
            if expect is not None:
                expect["url"] = url
                expect["params"] = params
                expect["json"] = json
            return _FakeResponse(payload)

    monkeypatch.setattr("app.core.judge.httpx.AsyncClient", FakeClient)
    # These tests are about the request Judge0 would receive, so the local
    # compiler is turned off for them.
    monkeypatch.setattr("app.core.judge.local_compiler", lambda: None)


ACCEPTED = {
    "stdout": "42\n",
    "stderr": "",
    "compile_output": "",
    "memory": 1088,
    "time": "0.003",
    "status": {"id": 3, "description": "Accepted"},
}

COMPILE_ERROR = {
    "stdout": None,
    "stderr": None,
    "compile_output": "error: expected ';' before '}' token",
    "memory": None,
    "time": None,
    "status": {"id": 6, "description": "Compilation Error"},
}


def test_compile_maps_judge0_success(monkeypatch) -> None:
    _fake_client(monkeypatch, ACCEPTED)

    response = client.post("/api/v1/compile", json={"source_code": "int main(){}"})

    assert response.status_code == 200
    body = response.json()
    assert body["stdout"] == "42\n"
    assert body["status"] == 3
    assert body["status_text"] == "Accepted"
    assert body["memory_kb"] == 1088
    assert body["time"] == "0.003"


def test_compile_maps_compiler_errors(monkeypatch) -> None:
    _fake_client(monkeypatch, COMPILE_ERROR)

    response = client.post("/api/v1/compile", json={"source_code": "int main(){"})

    assert response.status_code == 200
    body = response.json()
    assert body["status_text"] == "Compilation error"
    assert "expected" in body["compile_output"]
    assert body["stdout"] == ""


def test_compile_requests_wait_and_cxx(monkeypatch) -> None:
    seen: dict = {}
    _fake_client(monkeypatch, ACCEPTED, expect=seen)

    client.post("/api/v1/compile", json={"source_code": "int main(){}", "stdin": "1"})

    # wait=true avoids a polling loop. Base64 is on, because a submission can
    # carry any character and Judge0 answers HTTP 400 without it.
    assert seen["params"] == {"base64_encoded": "true", "wait": "true"}
    assert seen["json"]["language_id"] == 54
    assert base64.b64decode(seen["json"]["stdin"]).decode() == "1"


def test_compile_rejects_non_cpp(monkeypatch) -> None:
    _fake_client(monkeypatch, ACCEPTED)

    response = client.post(
        "/api/v1/compile",
        json={"source_code": "print(1)", "language_id": 71},  # Python
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only C++ is wired up right now."


def test_compile_requires_source_code() -> None:
    response = client.post("/api/v1/compile", json={"source_code": ""})
    assert response.status_code == 422


def test_the_local_compiler_runs_the_code() -> None:
    """When there is a compiler here, the code runs here.

    Judge0 takes the best part of half a minute and drops connections, so the
    local path is the one that normally answers.
    """
    from app.core import judge

    if not judge.local_compiler():
        import pytest

        pytest.skip("no local C++ compiler on this machine")

    response = client.post(
        "/api/v1/compile",
        json={
            "source_code": (
                "#include <iostream>\n"
                "int main(){ int a; std::cin >> a; std::cout << a * 2 << std::endl; }"
            ),
            "stdin": "21\n",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["stdout"].strip() == "42"
    assert body["status"] == 3
    assert body["status_text"] == "Accepted"


# Note: every test above posts with no Authorization header and still succeeds.
# That is the assertion that this endpoint is intentionally public.
