"""The problem catalogue.

The catalogue is seeded into Supabase from `supabase/seed/problems.json` and
`supabase/seed/sheets.json`. At runtime it is read from the database, so the
JSON files are the seed, not a second source of truth.

The JSON path is kept as a fallback for a checkout with no Supabase
credentials, and for the test suite (`RESOLVE_CATALOGUE=json`), so the backend
still boots and answers on a fresh clone.

Every expected output was measured by compiling and running the problem's own
reference solution, so the stored answer is a fact rather than a prediction.

Each problem carries the C++ that goes before and after the user's function:

    prefix + the user's function + suffix

That is why the editor only ever holds the function.
"""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings

#: `backend/app/core/problems.py` -> up to the repo root.
ROOT = Path(__file__).resolve().parents[3]
DATA_FILE = ROOT / "supabase" / "seed" / "problems.json"
SHEETS_FILE = ROOT / "supabase" / "seed" / "sheets.json"


class ProblemNotFoundError(LookupError):
    """Raised when a slug does not match a problem in the catalogue."""


def source() -> str:
    """Where the catalogue is read from: `supabase` or `json`."""
    choice = (os.environ.get("RESOLVE_CATALOGUE") or "").strip().lower()
    if not choice:
        choice = get_settings().resolve_catalogue.strip().lower()
    if choice == "json":
        return "json"
    if choice == "supabase":
        return "supabase"
    return "supabase" if get_settings().is_configured else "json"


def _client():
    from app.core.supabase import get_supabase_admin

    return get_supabase_admin()


# --------------------------------------------------------------------- JSON


@lru_cache(maxsize=1)
def _catalogue() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _by_slug() -> dict[str, dict[str, Any]]:
    return {p["slug"]: p for p in _catalogue()}


@lru_cache(maxsize=1)
def _json_sheets() -> list[dict[str, Any]]:
    if not SHEETS_FILE.exists():
        return []
    data = json.loads(SHEETS_FILE.read_text(encoding="utf-8"))
    return data.get("sheets", [])


# ---------------------------------------------------------------- Supabase


def _without_internal(row: dict[str, Any]) -> dict[str, Any]:
    """Drop the columns that are storage details, not part of the catalogue."""
    return {
        key: value
        for key, value in row.items()
        if key not in {"id", "created_at", "updated_at"}
    }


@lru_cache(maxsize=1)
def _db_summaries() -> list[dict[str, Any]]:
    rows = (
        _client()
        .table("problems")
        .select("slug,title,difficulty,tags")
        .order("title")
        .execute()
        .data
    )
    return rows or []


@lru_cache(maxsize=1)
def _db_sheets() -> list[dict[str, Any]]:
    sheets = (
        _client()
        .table("sheets")
        .select("id,name,blurb,tier,position")
        .order("position")
        .execute()
        .data
    ) or []
    rows = (
        _client()
        .table("sheet_problems")
        .select("sheet_id,problem_slug,position")
        .order("position")
        .execute()
        .data
    ) or []

    grouped: dict[str, list[tuple[int, str]]] = {}
    for row in rows:
        grouped.setdefault(row["sheet_id"], []).append(
            (row["position"], row["problem_slug"])
        )

    # A problem in no sheet is not a catalogue, it is a gap. The JSON path
    # checks this too; the database should not be able to drift silently.
    known = {
        row["slug"]
        for row in (_client().table("problems").select("slug").execute().data or [])
    }
    claimed = {row["problem_slug"] for row in rows}
    missing = known - claimed
    if missing:
        raise ProblemNotFoundError(
            f"{len(missing)} problem(s) are in no sheet: {', '.join(sorted(missing))}"
        )

    out: list[dict[str, Any]] = []
    for sheet in sheets:
        problems = [slug for _, slug in sorted(grouped.get(sheet["id"], []))]
        out.append(
            {
                "id": sheet["id"],
                "name": sheet["name"],
                "blurb": sheet.get("blurb") or "",
                "tier": sheet.get("tier") or "",
                "problems": problems,
                "total": len(problems),
            }
        )
    return out


@lru_cache(maxsize=256)
def _db_problem(slug: str) -> dict[str, Any]:
    rows = (
        _client()
        .table("problems")
        .select("*")
        .eq("slug", slug)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise ProblemNotFoundError(slug)

    problem = _without_internal(rows[0])
    cases = (
        _client()
        .table("test_cases")
        .select("position,args,expected,note")
        .eq("problem_id", rows[0]["id"])
        .order("position")
        .execute()
        .data
    ) or []
    problem["test_cases"] = [
        {
            "args": case["args"],
            "expected": case["expected"],
            "note": case.get("note", ""),
        }
        for case in cases
    ]
    return problem


# -------------------------------------------------------------------- public


def all_problems() -> list[dict[str, Any]]:
    if source() == "json":
        return _catalogue()

    # Full rows, without test cases: enough for a catalogue-wide check, and
    # much cheaper than pulling 3,000 cases the caller did not ask for.
    rows = _client().table("problems").select("*").order("slug").execute().data or []
    return [_without_internal(row) for row in rows]


def summaries() -> list[dict[str, Any]]:
    """Just enough to render and filter the list."""
    if source() == "json":
        return [
            {
                "slug": p["slug"],
                "title": p["title"],
                "difficulty": p["difficulty"],
                "tags": p["tags"],
            }
            for p in _catalogue()
        ]
    return _db_summaries()


def get_problem(slug: str) -> dict[str, Any]:
    if source() == "json":
        problem = _by_slug().get(slug)
        if problem is None:
            raise ProblemNotFoundError(slug)
        return problem
    return _db_problem(slug)


def sheets() -> list[dict[str, Any]]:
    """The sheets, each with its problems in the order they should be done.

    The JSON path also checks that the two seed files cannot drift apart
    silently. The database enforces the same thing with foreign keys.
    """
    if source() == "supabase":
        return _db_sheets()

    known = set(_by_slug())
    out: list[dict[str, Any]] = []
    claimed: set[str] = set()

    for sheet in _json_sheets():
        problems = [slug for slug in sheet.get("problems", []) if slug in known]
        claimed.update(problems)
        out.append(
            {
                "id": sheet["id"],
                "name": sheet["name"],
                "blurb": sheet.get("blurb", ""),
                "tier": sheet.get("tier", ""),
                "problems": problems,
                "total": len(problems),
            }
        )

    missing = known - claimed
    if missing:
        raise ProblemNotFoundError(
            f"{len(missing)} problem(s) are in no sheet: {', '.join(sorted(missing))}"
        )

    return out


def sheet_problems(sheet_id: str) -> list[dict[str, Any]]:
    """The problems of one sheet, in order, with the problem's own details."""
    for sheet in sheets():
        if sheet["id"] != sheet_id:
            continue
        return [get_problem(slug) for slug in sheet["problems"]]
    raise ProblemNotFoundError(sheet_id)
