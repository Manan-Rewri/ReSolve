"""The problem catalogue and the judge.

Two things live here:

* the catalogue — a list of problems, and one problem in full
* the judge — run a user's function against that problem's stored test cases

The user's function is spliced between the problem's stored `prefix` and
`suffix`, so the browser never sends an include or a main, and the editor only
ever holds the function itself.
"""

from fastapi import APIRouter, HTTPException, status

from app.core import problems as catalogue
from app.core.judge import run_cxx
from app.schemas.problem import (
    CaseResult,
    JudgeRequest,
    JudgeResponse,
    Problem,
    ProblemSummary,
    Sheet,
)

router = APIRouter(tags=["problems"])

#: Marks the boundary between one case's output and the next, so a single run
#: carrying every case can be split apart again.
CASE_MARKER = "___CASE___"

#: Judge0 status ids -> what we tell the user.
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


@router.get("/problems", response_model=list[ProblemSummary])
async def list_problems() -> list[ProblemSummary]:
    """Every problem, summarised. Enough to render and filter the list."""
    return [ProblemSummary(**s) for s in catalogue.summaries()]


@router.get("/sheets", response_model=list[Sheet])
async def list_sheets() -> list[Sheet]:
    """The sheets, each with its problems in the order they should be done."""
    try:
        return [Sheet(**s) for s in catalogue.sheets()]
    except catalogue.ProblemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get("/problems/{slug}", response_model=Problem)
async def read_problem(slug: str) -> Problem:
    """One problem in full, with its examples, constraints and test cases."""
    try:
        problem = catalogue.get_problem(slug)
    except catalogue.ProblemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such problem.",
        ) from exc

    return Problem(
        slug=problem["slug"],
        title=problem["title"],
        difficulty=problem["difficulty"],
        tags=problem["tags"],
        statement=problem["statement"],
        examples=problem["examples"],
        constraints=problem["constraints"],
        signature=problem["signature"],
        editor_start=problem["editor_start"],
    )


@router.get("/problems/{slug}/cases")
async def read_cases(slug: str) -> dict:
    """The stored test cases, with the expected output for each.

    Every case is returned. Nothing is hidden, so the user can see exactly
    what they are being measured against.
    """
    try:
        problem = catalogue.get_problem(slug)
    except catalogue.ProblemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such problem.",
        ) from exc

    return {"slug": slug, "cases": problem["test_cases"]}


@router.post("/judge", response_model=JudgeResponse)
async def judge(payload: JudgeRequest) -> JudgeResponse:
    """Run the user's function against the problem's stored test cases."""
    try:
        problem = catalogue.get_problem(payload.slug)
    except catalogue.ProblemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such problem.",
        ) from exc

    # A submission of nothing but spaces is not a submission.
    if not payload.code.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Write a solution first.",
        )

    program = f"{problem['prefix']}\n{payload.code}\n{problem['suffix']}"

    status_id, stdout, stderr, compile_output = await _run(program)
    cases = problem["test_cases"]

    if status_id == 6:
        return JudgeResponse(
            slug=problem["slug"],
            passed=0,
            total=len(cases),
            cases=[],
            compile_output=compile_output,
            status_text="Compilation error",
        )
    if status_id != 3:
        return JudgeResponse(
            slug=problem["slug"],
            passed=0,
            total=len(cases),
            cases=[],
            compile_output=(compile_output or stderr)[:2000],
            status_text=STATUS_TEXT.get(status_id, "Unknown"),
        )

    actual = _split(stdout)
    results: list[CaseResult] = []
    passed = 0
    for index, case in enumerate(cases):
        got = actual[index] if index < len(actual) else ""
        ok = got.strip() == case["expected"].strip()
        if ok:
            passed += 1
        results.append(
            CaseResult(
                args=case["args"],
                expected=case["expected"],
                actual=got,
                passed=ok,
            )
        )

    return JudgeResponse(
        slug=problem["slug"],
        passed=passed,
        total=len(cases),
        cases=results,
        status_text=(
            "Accepted" if passed == len(cases) else f"{passed} of {len(cases)} passed"
        ),
    )


def _split(stdout: str) -> list[str]:
    """One entry per case, in order."""
    if CASE_MARKER not in stdout:
        return []
    return [part.strip() for part in stdout.split(CASE_MARKER)[1:]]


async def _run(source_code: str) -> tuple[int, str, str, str]:
    """Compile and run the program. Returns `(status_id, stdout, stderr, compile_output)`.

    The code is run here when there is a local compiler, and on Judge0 when
    there is not. Both answer in the same shape.
    """
    outcome = await run_cxx(source_code)
    return (
        outcome.status,
        outcome.stdout,
        outcome.stderr,
        outcome.compile_output,
    )
