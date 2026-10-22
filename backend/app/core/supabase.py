"""Shared Supabase clients.

Two clients exist on purpose:

* ``get_supabase_admin``  - service-role key, bypasses RLS. Server side only.
  Never expose the service-role key to the browser.
* ``get_supabase_anon``   - anon key, subject to Row Level Security. Used for
  anything that should be scoped to the calling user.
"""

from functools import lru_cache

from supabase import Client, create_client
from supabase.lib.client_options import SyncClientOptions

from app.core.config import get_settings

# The API is stateless; nothing should try to persist or refresh a session.
_CLIENT_OPTIONS = SyncClientOptions(
    schema="public",
    auto_refresh_token=False,
    persist_session=False,
)


def _build_client() -> Client:
    settings = get_settings()
    if not settings.is_configured:
        raise RuntimeError(
            "Supabase is not configured. Copy .env.example to .env and fill in "
            "SUPABASE_URL, SUPABASE_ANON_KEY and SUPABASE_SERVICE_ROLE_KEY."
        )
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
        options=_CLIENT_OPTIONS,
    )


@lru_cache
def get_supabase_admin() -> Client:
    """Service-role client. Bypasses RLS - server side only."""
    return _build_client()


@lru_cache
def get_supabase_anon() -> Client:
    """Anon client. Subject to Row Level Security."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_anon_key:
        raise RuntimeError("Supabase anon client is not configured. Check your .env file.")
    return create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=_CLIENT_OPTIONS,
    )
