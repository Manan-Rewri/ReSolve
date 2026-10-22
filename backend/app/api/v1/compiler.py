"""Runs code.

The code is compiled and run **here** when there is a C++ compiler on the
machine, and on Judge0 when there is not. The public Judge0 instance takes the
best part of half a minute a run and drops connections often enough that the
page feels broken, so the local compiler is the one that normally answers.

Either way the browser posts to /api/v1/compile and this module forwards, so
any RapidAPI key stays on the server.

The endpoint is deliberately unauthenticated. Judge0 gives us no per-user quota
either way, so gating it would buy nothing except friction. Re-add
`Depends(get_current_user)` before exposing this publicly — an open proxy to
a code runner is a known abuse vector.
"""

from fastapi import APIRouter, HTTPException, status

from app.core import judge
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


@router.post("/compile", response_model=CompileResult)
async def compile_code(payload: CompileRequest) -> CompileResult:
    if payload.language_id != LANGUAGE_CXX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only C++ is wired up right now.",
        )

    outcome = await judge.run_cxx(payload.source_code, payload.stdin)

    return CompileResult(
        stdout=outcome.stdout,
        stderr=outcome.stderr,
        compile_output=outcome.compile_output,
        status=outcome.status,
        status_text=STATUS_TEXT.get(outcome.status, "Unknown"),
        time=outcome.time,
        memory_kb=outcome.memory_kb,
    )
