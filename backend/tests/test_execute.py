"""
Unit tests for the code execution feature.

These tests do NOT hit the network. The Judge0 service is monkeypatched so the
suite is fast and deterministic. One optional integration test (skipped unless
RUN_LIVE_JUDGE0=1) exercises the real service.

Endpoint tests use the shared ``client`` fixture from ``tests/conftest.py``.
"""
import os
import base64

import pytest

from app.schemas.execution import (
    CodeLanguage,
    ExecutionResult,
    ExecutionStatus,
)
from app.services.judge0_service import Judge0Service


def _fake_result(**overrides) -> ExecutionResult:
    defaults = dict(
        language=CodeLanguage.cpp,
        status=ExecutionStatus(id=3, description="Accepted"),
        succeeded=True,
        stdout="7\n",
        stderr=None,
        compile_output=None,
        message=None,
        time=0.003,
        memory=1160,
        exit_code=0,
    )
    defaults.update(overrides)
    return ExecutionResult(**defaults)


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------
def test_languages_endpoint_lists_cpp(client):
    resp = client.get("/api/v1/execute/languages")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()]
    assert "cpp" in ids


def test_execute_rejects_empty_source_code(client):
    resp = client.post(
        "/api/v1/execute", json={"language": "cpp", "source_code": ""}
    )
    assert resp.status_code == 422  # pydantic min_length


def test_execute_rejects_unknown_language(client):
    resp = client.post(
        "/api/v1/execute",
        json={"language": "brainfuck", "source_code": "+++"},
    )
    assert resp.status_code == 422


def test_execute_success_mocked(client, monkeypatch):
    async def fake_execute(*args, **kwargs):
        return _fake_result()

    monkeypatch.setattr("app.routers.execute.judge0_service.execute", fake_execute)

    resp = client.post(
        "/api/v1/execute",
        json={
            "language": "cpp",
            "source_code": "int main(){return 0;}",
            "stdin": "3 4",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["succeeded"] is True
    assert body["stdout"] == "7\n"
    assert body["status"]["id"] == 3


def test_execute_compile_error_mocked(client, monkeypatch):
    async def fake_execute(*args, **kwargs):
        return _fake_result(
            status=ExecutionStatus(id=6, description="Compilation Error"),
            succeeded=False,
            stdout=None,
            compile_output="error: expected ';'",
        )

    monkeypatch.setattr("app.routers.execute.judge0_service.execute", fake_execute)

    resp = client.post(
        "/api/v1/execute",
        json={"language": "cpp", "source_code": "int main(){ broken }"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["succeeded"] is False
    assert "error" in body["compile_output"]


# ---------------------------------------------------------------------------
# Service unit tests (no network)
# ---------------------------------------------------------------------------
def test_base64_roundtrip():
    svc = Judge0Service()
    original = "héllo\n\tworld ✓"
    encoded = svc._encode(original)
    assert svc._decode(encoded) == original


def test_decode_none_is_none():
    assert Judge0Service._decode(None) is None


def test_to_result_maps_status_and_fields():
    svc = Judge0Service()
    data = {
        "status": {"id": 3, "description": "Accepted"},
        "stdout": base64.b64encode(b"hi\n").decode(),
        "stderr": None,
        "compile_output": None,
        "message": None,
        "time": "0.01",
        "memory": 512,
        "exit_code": 0,
    }
    result = svc._to_result(data, CodeLanguage.cpp)
    assert result.succeeded is True
    assert result.stdout == "hi\n"
    assert result.time == 0.01
    assert result.memory == 512


def test_to_result_marks_non_accepted_as_failed():
    svc = Judge0Service()
    data = {"status": {"id": 5, "description": "Time Limit Exceeded"}, "time": "3.0"}
    result = svc._to_result(data, CodeLanguage.cpp)
    assert result.succeeded is False


# ---------------------------------------------------------------------------
# Optional live integration test (network). Run with RUN_LIVE_JUDGE0=1.
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    os.getenv("RUN_LIVE_JUDGE0") != "1",
    reason="set RUN_LIVE_JUDGE0=1 to run against the live Judge0 instance",
)
def test_live_cpp_execution(client):
    resp = client.post(
        "/api/v1/execute",
        json={
            "language": "cpp",
            "source_code": (
                "#include <iostream>\n"
                "int main(){int a,b;std::cin>>a>>b;std::cout<<a+b<<\"\\n\";}\n"
            ),
            "stdin": "20 22",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["succeeded"] is True
    assert body["stdout"].strip() == "42"
