"""The problem catalogue.

The data lives in `backend/data/problems.json`. It is a stand-in for the
database: when the tables exist, this module is the only thing that changes.

Every expected output in the file was measured by compiling and running the
problem's own reference solution, so the stored answer is a fact rather than a
prediction.

Each problem carries the C++ that goes before and after the user's function:

    prefix + the user's function + suffix

That is why the editor only ever holds the function.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "problems.json"


class ProblemNotFoundError(LookupError):
    """Raised when a slug does not match a problem in the catalogue."""


@lru_cache(maxsize=1)
def _catalogue() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    return data


@lru_cache(maxsize=1)
def _by_slug() -> dict[str, dict[str, Any]]:
    return {p["slug"]: p for p in _catalogue()}


def all_problems() -> list[dict[str, Any]]:
    return _catalogue()


def summaries() -> list[dict[str, Any]]:
    """Just enough to render and filter the list."""
    return [
        {
            "slug": p["slug"],
            "title": p["title"],
            "difficulty": p["difficulty"],
            "tags": p["tags"],
        }
        for p in _catalogue()
    ]


def get_problem(slug: str) -> dict[str, Any]:
    problem = _by_slug().get(slug)
    if problem is None:
        raise ProblemNotFoundError(slug)
    return problem


def search(query: str) -> list[dict[str, Any]]:
    """Filter by title, tag or difficulty. An empty query returns everything."""
    needle = query.strip().lower()
    if not needle:
        return summaries()
    out = []
    for p in _catalogue():
        haystack = " ".join(
            [p["title"], p["difficulty"], *p["tags"], *p["examples"][0].values()]
        ).lower()
        if needle in haystack:
            out.append(
                {
                    "slug": p["slug"],
                    "title": p["title"],
                    "difficulty": p["difficulty"],
                    "tags": p["tags"],
                }
            )
    return out
