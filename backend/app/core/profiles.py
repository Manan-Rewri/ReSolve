"""Public profiles, backed by the database.

A share link is `/p/<token>`. The token is a random 128-bit string stored on
the owner's `profiles` row; it is not a user id, so a link cannot be edited
into somebody else's profile. Turning `is_public` off makes the same link
404 without deleting anything.

The public response is assembled here, server-side, from the owner's cards,
solved list and review log. It carries counts and tags only: no email, no user
id, no review log entries. That is the same shape the old URL snapshot used,
so the existing page renders it without a second layout.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core import problems as catalogue
from app.core import scheduler, store
from app.core.supabase import get_supabase_admin

#: A shared name is text on a public page. Keep it short.
NAME_LIMIT = 60
TAG_LIMIT = 24
TOP_TAGS = 6


def _client():
    return get_supabase_admin()


def _user_details(user_id: str, fallback_name: str = "") -> tuple[str, str | None]:
    """The name to show and when the account was created."""
    try:
        user = _client().auth.admin.get_user_by_id(user_id).user
    except Exception:
        return (fallback_name or "Solver", None)

    metadata = user.user_metadata or {}
    name = str(metadata.get("username") or "").strip()
    if not name and user.email:
        name = user.email.split("@")[0]
    if not name:
        name = fallback_name or "Solver"

    created = user.created_at.isoformat() if user.created_at else None
    return (name[:NAME_LIMIT], created)


def ensure_share(user_id: str, fallback_name: str = "") -> dict[str, Any]:
    """Return this user's share token, creating the profile if needed."""
    client = _client()
    name, _ = _user_details(user_id, fallback_name)

    rows = (
        client.table("profiles")
        .select("id,username,share_token,is_public,created_at")
        .eq("id", user_id)
        .limit(1)
        .execute()
        .data
    )

    if rows:
        row = rows[0]
        updates: dict[str, Any] = {}
        if not row.get("share_token"):
            updates["share_token"] = secrets.token_urlsafe(16)
        if not row.get("username"):
            updates["username"] = name
        # Asking for a link is publishing it. A profile that was switched off
        # would otherwise hand back a token that 404s.
        if not row.get("is_public"):
            updates["is_public"] = True
        if updates:
            updates["updated_at"] = datetime.now(UTC).isoformat()
            row = (
                client.table("profiles")
                .update(updates)
                .eq("id", user_id)
                .execute()
                .data[0]
            )
        return {
            "token": row["share_token"],
            "username": row["username"] or name,
            "public": bool(row["is_public"]),
        }

    # A token collision is vanishingly unlikely, but retrying is cheaper than
    # a 500 on the one request that creates the link.
    for _ in range(3):
        token = secrets.token_urlsafe(16)
        try:
            row = (
                client.table("profiles")
                .insert(
                    {
                        "id": user_id,
                        "username": name,
                        "share_token": token,
                        "is_public": True,
                    }
                )
                .execute()
                .data[0]
            )
            return {
                "token": row["share_token"],
                "username": row["username"],
                "public": True,
            }
        except Exception:
            continue

    raise RuntimeError("Could not create a share link.")


def _streak(events: list[dict], today) -> int:
    days = set()
    for event in events:
        raw = str(event.get("at") or "")
        if len(raw) >= 10:
            days.add(raw[:10])

    cursor = today
    if cursor.isoformat() not in days:
        cursor = cursor - timedelta(days=1)

    streak = 0
    while cursor.isoformat() in days:
        streak += 1
        cursor = cursor - timedelta(days=1)
    return streak


def public_profile(token: str) -> dict[str, Any] | None:
    """The whitelisted public view of one profile, or None."""
    if not token or len(token) > 128:
        return None

    rows = (
        _client()
        .table("profiles")
        .select("id,username,is_public,created_at")
        .eq("share_token", token)
        .limit(1)
        .execute()
        .data
    )
    if not rows or not rows[0].get("is_public"):
        return None

    profile = rows[0]
    state = store.read(profile["id"])
    now = datetime.now(UTC)

    cards = [
        scheduler.Card(**raw)
        for raw in state["cards"].values()
        if isinstance(raw, dict)
    ]
    live = [card for card in cards if card.state != "graduated"]
    graduated = sum(1 for card in cards if card.state == "graduated")

    retention = (
        0
        if not live
        else round(
            100 * sum(scheduler.recall(card, now) for card in live) / len(live)
        )
    )

    by_slug = {p["slug"]: p for p in catalogue.summaries()}
    solved = state["solved"]
    by_difficulty = {"Easy": 0, "Medium": 0, "Hard": 0}
    tag_counts: dict[str, int] = {}
    for slug in solved:
        problem = by_slug.get(slug)
        if problem is None:
            continue
        by_difficulty[problem["difficulty"]] += 1
        for tag in problem["tags"]:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    top_tags = [
        {"tag": tag[:TAG_LIMIT], "count": count}
        for tag, count in sorted(
            tag_counts.items(), key=lambda item: (-item[1], item[0])
        )[:TOP_TAGS]
    ]

    _, joined = _user_details(profile["id"], profile.get("username") or "")

    return {
        "v": 1,
        "name": (profile.get("username") or "Solver")[:NAME_LIMIT],
        "joined": joined,
        "at": now.isoformat(),
        "solved": len(solved),
        "in_sheet": len(live),
        "reviews": len(state["history"]),
        "streak": _streak(state["history"], now.date()),
        "retention": max(0, min(100, retention)),
        "graduated": graduated,
        "by_difficulty": by_difficulty,
        "top_tags": top_tags,
        "live": True,
    }
