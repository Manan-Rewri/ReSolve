"""The share link and the public profile it points at."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core import profiles
from app.schemas.profile import PublicProfileResponse, ShareResponse
from app.schemas.user import CurrentUser

router = APIRouter(tags=["profile"])


@router.post("/profile/share", response_model=ShareResponse)
async def share(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ShareResponse:
    """The owner's share token, created on first use.

    The request has to be a POST because it may create the profile row; a GET
    that writes is the kind of thing a link prefetcher gets wrong.
    """
    fallback = (user.email or "").split("@")[0]
    result = profiles.ensure_share(user.id, fallback)
    return ShareResponse(**result)


@router.get("/public/profiles/{token}", response_model=PublicProfileResponse)
async def public_profile(token: str) -> PublicProfileResponse:
    """A profile anyone can read with the link, and only the counts.

    No session is required, and nothing private is in the response: no email,
    no user id, no review log entries. A token that is unknown or switched off
    is a 404, so a wrong link cannot confirm that an account exists.
    """
    result = profiles.public_profile(token)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No such public profile.",
        )
    return PublicProfileResponse(**result)
