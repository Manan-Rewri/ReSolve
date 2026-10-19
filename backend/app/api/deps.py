from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from app.core.supabase import get_supabase_admin
from app.schemas.user import CurrentUser

# auto_error=False so we can raise our own 401 shape instead of FastAPI's default.
bearer_scheme = HTTPBearer(auto_error=False)


def supabase_provider() -> Callable[[], Client]:
    """Returns a *callable*, not a client.

    FastAPI resolves every sub-dependency before the endpoint body runs, so
    injecting a client directly would try to build it even for anonymous
    requests. Deferring the build means a request with no token still gets a
    clean 401 without the server needing Supabase configured at all.
    """

    def build() -> Client:
        try:
            return get_supabase_admin()
        except RuntimeError as exc:
            # A missing backend .env is an operator problem, not a client error.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc

    return build


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    build_client: Annotated[Callable[[], Client], Depends(supabase_provider)],
) -> CurrentUser | None:
    """Resolve the caller from their Supabase access token, or None."""
    if credentials is None:
        return None

    supabase = build_client()

    try:
        response = supabase.auth.get_user(credentials.credentials)
    except Exception as exc:  # never leak upstream auth errors verbatim
        raise _unauthorized("Invalid or expired token") from exc

    user = response.user if response else None
    if user is None:
        return None

    return CurrentUser(id=user.id, email=user.email)


async def get_current_user(
    user: Annotated[CurrentUser | None, Depends(get_optional_user)],
) -> CurrentUser:
    """Same as get_optional_user, but rejects anonymous callers."""
    if user is None:
        raise _unauthorized()
    return user
