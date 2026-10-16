from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import auth_service

security = HTTPBearer(auto_error=False)

UNAUTHORIZED = {
    "headers": {"WWW-Authenticate": "Bearer"},
    "status_code": status.HTTP_401_UNAUTHORIZED,
}


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(detail=detail, **UNAUTHORIZED)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _unauthorized("Authentication credentials were not provided")

    payload = auth_service.decode_access_token(credentials.credentials)
    if not payload:
        raise _unauthorized("Invalid or expired authentication token")

    user_id = payload.get("sub")
    if not user_id:
        raise _unauthorized("Token payload missing subject identifier")

    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise _unauthorized("User associated with this token no longer exists")

    return user