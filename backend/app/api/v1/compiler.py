"""Runs code on Judge0.

Judge0 is a third-party public service reached over the network. It is never
called from the browser — the frontend posts to /api/v1/compile and this module
forwards, so any RapidAPI key stays on the server.

The endpoint is deliberately unauthenticated. Judge0 gives us no per-user quota
either way, so gating it would buy nothing except friction. Re-add
`Depends(get_current_user)` before exposing this publicly — an open proxy to a
code runner is a known abuse vector.
"""

import httpx
from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.schemas.compiler import LANGUAGE_CXX, CompileRequest, CompileResult

router = APIRouter(tags=["compiler"])

# Judge0 status ids -> what we tell the user.
STATUS_TEXT = {
    1: "In queue",
    2: "Running",
    3: "Accepted",
    4: "Wrong answer",
    5: "Time limit exceeded",
    6: "Compilation error",
    7: "Runtime error (SIGSEGV)",
    8: "Runtime error (SIGXFSZ)",
    9: "Runtime error (SIGFPE)",
    10: "Runtime error (SIGABRT)",
    11: "Internal error",
    12: "Exec format error",
    13: "Unavailable",
}


def _headers() -> dict[str, str]:
    """RapidAPI needs a key header; the public CE instance needs nothing."""
    settings = get_settings()
    if settings.judge0_api_key:
        return {
            "X-RapidAPI-Key": settings.judge0_api_key,
            "X-RapidAPI-Host": settings.judge0_host,
        }
    return {}


@router.post("/compile", response_model=CompileResult)
async def compile_code(payload: CompileRequest) -> CompileResult:
    settings = get_settings()

    if payload.language_id != LANGUAGE_CXX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only C++ is wired up right now.",
        )

    body = {
        "source_code": payload.source_code,
        "language_id": payload.language_id,
        "stdin": payload.stdin,
    }

    # wait=true blocks until Judge0 finishes, so we need no polling loop.
    url = f"{settings.judge0_base_url}/submissions"
    params = {"base64_encoded": "false", "wait": "true"}

    try:
        async with httpx.AsyncClient(timeout=settings.judge0_timeout_seconds) as client:
            response = await client.post(url, params=params, json=body, headers=_headers())
            response.raise_for_status()
            data = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The compiler did not answer in time. Try again.",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the compiler service.",
        ) from exc

    # Judge0 answers 201 with the submission body when wait=true.
    status_id = data.get("status", {}).get("id")
    if not isinstance(status_id, int):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The compiler returned an unexpected response.",
        )

    return CompileResult(
        stdout=data.get("stdout") or "",
        stderr=data.get("stderr") or "",
        compile_output=data.get("compile_output") or "",
        status=status_id,
        status_text=STATUS_TEXT.get(status_id, "Unknown"),
        time=data.get("time"),
        memory_kb=data.get("memory"),
    )
