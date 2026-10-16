"""
Code execution router.

Exposes a single endpoint, ``POST /api/v1/execute``, that compiles and runs a
snippet of code (default C++) and returns its output.

When merging into the main Resolve backend, register this router the same way
the others are registered in ``app/main.py`` and add
``Depends(get_current_user)`` to the endpoint if running code should require
authentication.
"""
from typing import List

from fastapi import APIRouter, status

from app.schemas.execution import (
    ExecutionRequest,
    ExecutionResult,
    LanguageInfo,
)
from app.services.judge0_service import judge0_service

router = APIRouter(prefix="/execute", tags=["Code Execution"])


@router.get(
    "/languages",
    response_model=List[LanguageInfo],
    summary="List supported languages",
    description="Returns the languages the code runner currently supports.",
)
def list_languages() -> List[LanguageInfo]:
    return judge0_service.language_options()


@router.post(
    "",
    response_model=ExecutionResult,
    status_code=status.HTTP_200_OK,
    summary="Compile and run a snippet",
    description=(
        "Compiles and runs the submitted source code in a sandboxed Judge0 "
        "instance and returns stdout, stderr, compiler output and timing. "
        "The code is never executed on this server."
    ),
)
async def execute_code(payload: ExecutionRequest) -> ExecutionResult:
    """Run a code snippet and return a normalised execution result."""
    return await judge0_service.execute(
        source_code=payload.source_code,
        language=payload.language,
        stdin=payload.stdin,
    )
