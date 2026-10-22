"""The practice state.

Two stores live behind one module:

* **Supabase** — the real one. Cards, the solved list and the review log are
  rows, written by the API with the service-role key. This is what the browser
  uses once the project is configured.
* **A JSON file** — the fallback for a checkout with no credentials and the
  store the test suite runs against. It is the same shape, so nothing above
  this module branches.

The file is written atomically, so a crash halfway through cannot leave a
half-written file behind.
"""

import json
import os
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.scheduler import Card

#: One lock for the whole file. The server is single-process and the writes
#: are small, so there is no need for anything cleverer.
_LOCK = threading.Lock()

#: The review log is capped so one user cannot grow it without bound.
HISTORY_LIMIT = 5000

def using_supabase() -> bool:
    """Whether the database is the store for this process."""
    choice = get_settings().practice_store.strip().lower()
    if choice == "file":
        return False
    if choice == "supabase":
        return True
    return get_settings().is_configured


# ------------------------------------------------------------------- file


def _path() -> Path:
    return Path(get_settings().state_file)


def _read_all() -> dict[str, dict]:
    path = _path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # A file we cannot read is a file we must not overwrite either.
        return {}
    return data if isinstance(data, dict) else {}


def _write_all(data: dict[str, dict]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _normalise_file_state(state: dict | None) -> dict:
    if not isinstance(state, dict):
        # Fresh containers, never `dict(EMPTY)`: a shallow copy would share
        # the nested cards dict with every other new user.
        return {"cards": {}, "sheet": [], "solved": [], "history": []}
    cards = state.get("cards") if isinstance(state.get("cards"), dict) else {}
    return {
        "cards": cards,
        "sheet": state.get("sheet") if isinstance(state.get("sheet"), list) else [],
        "solved": state.get("solved") if isinstance(state.get("solved"), list) else [],
        "history": (
            state.get("history")[-HISTORY_LIMIT:]
            if isinstance(state.get("history"), list)
            else []
        ),
    }


def _file_read(user_id: str) -> dict:
    with _LOCK:
        return _normalise_file_state(_read_all().get(user_id))


def _file_write(user_id: str, state: dict) -> None:
    with _LOCK:
        data = _read_all()
        data[user_id] = state
        _write_all(data)


def _file_update(user_id: str, change: Callable[[dict], Any]) -> Any:
    with _LOCK:
        data = _read_all()
        state = _normalise_file_state(data.get(user_id))
        result = change(state)
        data[user_id] = state
        _write_all(data)
        return result


# --------------------------------------------------------------- supabase


def _client():
    from app.core.supabase import get_supabase_admin

    return get_supabase_admin()


def _db_read(user_id: str) -> dict:
    client = _client()
    cards_rows = (
        client.table("card_state")
        .select("*")
        .eq("user_id", user_id)
        .order("due_at")
        .execute()
        .data
    ) or []
    solved_rows = (
        client.table("solved_problems")
        .select("problem_slug")
        .eq("user_id", user_id)
        .order("solved_at")
        .execute()
        .data
    ) or []
    log_rows = (
        client.table("review_logs")
        .select("problem_slug,rating,created_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(HISTORY_LIMIT)
        .execute()
        .data
    ) or []

    cards: dict[str, dict] = {}
    for row in cards_rows:
        cards[row["problem_slug"]] = {
            "slug": row["problem_slug"],
            "state": row["state"],
            "stability_days": row["stability_days"],
            "due_at": row["due_at"],
            "reps": row["reps"],
            "lapses": row["lapses"],
            "last_rating": row["last_rating"],
            "last_reviewed_at": row["last_reviewed_at"],
        }

    return {
        "cards": cards,
        # A card in the sheet is an active card. Graduated cards stay in
        # `cards` so the dashboard can count them, but they are not scheduled.
        "sheet": [slug for slug, card in cards.items() if card["state"] != "graduated"],
        "solved": [row["problem_slug"] for row in solved_rows],
        "history": [
            {
                "slug": row["problem_slug"],
                "rating": row["rating"],
                "at": row["created_at"],
            }
            for row in reversed(log_rows)
        ],
    }


# ------------------------------------------------------------------ public


def read(user_id: str) -> dict:
    """One user's state: cards, sheet, solved, review log."""
    if using_supabase():
        return _db_read(user_id)
    return _file_read(user_id)


def card(user_id: str, slug: str) -> Card | None:
    """One card, or None when the user has never reviewed that problem."""
    raw = read(user_id)["cards"].get(slug)
    return Card(**raw) if raw else None


def record_review(user_id: str, card: Card, rating: str, at) -> None:
    """Save a review and the card that came out of it, in one transaction.

    The card and the log entry have to land together: a card without its log
    would disappear from the dashboard's history, and a log without its card
    would claim a review that the schedule does not know about.
    """
    if using_supabase():
        _client().rpc(
            "record_review",
            {
                "p_user_id": user_id,
                "p_problem_slug": card.slug,
                "p_rating": rating,
                "p_state": card.state,
                "p_stability_days": card.stability_days,
                "p_due_at": card.due_at.isoformat(),
                "p_reps": card.reps,
                "p_lapses": card.lapses,
                "p_last_reviewed_at": (
                    card.last_reviewed_at.isoformat()
                    if card.last_reviewed_at
                    else None
                ),
            },
        ).execute()
        return

    def change(state: dict) -> None:
        state["cards"][card.slug] = card.model_dump(mode="json")
        sheet = state["sheet"]
        if card.state == "graduated":
            state["sheet"] = [slug for slug in sheet if slug != card.slug]
        elif card.slug not in sheet:
            state["sheet"] = [*sheet, card.slug]

        event = {"slug": card.slug, "rating": rating, "at": at.isoformat()}
        state["history"] = [*state["history"], event][-HISTORY_LIMIT:]

    _file_update(user_id, change)


def set_solved(user_id: str, slug: str, solved: bool) -> bool:
    """Record whether a problem has been got fully right."""
    if using_supabase():
        client = _client()
        if solved:
            client.table("solved_problems").upsert(
                {"user_id": user_id, "problem_slug": slug},
                on_conflict="user_id,problem_slug",
            ).execute()
        else:
            (
                client.table("solved_problems")
                .delete()
                .eq("user_id", user_id)
                .eq("problem_slug", slug)
                .execute()
            )
        return solved

    def change(state: dict) -> bool:
        if solved:
            if slug not in state["solved"]:
                state["solved"] = [*state["solved"], slug]
        else:
            state["solved"] = [s for s in state["solved"] if s != slug]
        return solved

    return _file_update(user_id, change)


def remove_card(user_id: str, slug: str) -> None:
    """Take a problem out of the practice sheet ("very easy")."""
    if using_supabase():
        (
            _client()
            .table("card_state")
            .delete()
            .eq("user_id", user_id)
            .eq("problem_slug", slug)
            .execute()
        )
        return

    def change(state: dict) -> None:
        state["cards"].pop(slug, None)
        state["sheet"] = [s for s in state["sheet"] if s != slug]

    _file_update(user_id, change)


def import_state(user_id: str, state: dict) -> None:
    """Move a browser's localStorage bucket into the store, once.

    Refuses to overwrite an account that already has state: a second import
    would duplicate the review log and quietly rewrite the schedule.
    """
    cards = state.get("cards") or {}
    if not isinstance(cards, dict):
        raise ValueError("cards must be an object")
    solved = state.get("solved") or []
    history = state.get("history") or []

    existing = read(user_id)
    if existing["cards"] or existing["solved"] or existing["history"]:
        raise ValueError("the account already has practice state")

    if using_supabase():

        _client().rpc(
            "import_practice_state",
            {
                "p_user_id": user_id,
                "p_cards": list(cards.values()),
                "p_solved": solved,
                "p_history": history,
            },
        ).execute()
        return

    _file_write(
        user_id,
        {
            "cards": cards,
            "sheet": [
                slug
                for slug, card in cards.items()
                if isinstance(card, dict) and card.get("state") != "graduated"
            ],
            "solved": [s for s in solved if isinstance(s, str)],
            "history": [e for e in history if isinstance(e, dict)][-HISTORY_LIMIT:],
        },
    )
