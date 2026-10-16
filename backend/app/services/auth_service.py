from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.schemas.auth import UserSignUp, UserUpdate


class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except (ValueError, TypeError):
            return False

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        payload = data.copy()
        lifetime = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload["exp"] = int((datetime.now(timezone.utc) + lifetime).timestamp())
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def decode_access_token(token: str) -> Optional[dict]:
        try:
            return jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
        except jwt.PyJWTError:
            return None

    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email.lower().strip()).first()

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @classmethod
    def register_user(cls, db: Session, user_in: UserSignUp) -> User:
        user = User(
            email=user_in.email.lower().strip(),
            hashed_password=cls.hash_password(user_in.password),
            full_name=user_in.full_name.strip() if user_in.full_name else None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @classmethod
    def update_profile(
        cls, db: Session, user: User, profile_in: UserUpdate
    ) -> User:
        for field, value in profile_in.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return user

    @classmethod
    def authenticate_user(
        cls, db: Session, email: str, password: str
    ) -> Optional[User]:
        user = cls.get_user_by_email(db, email)
        if user and cls.verify_password(password, user.hashed_password):
            return user
        return None


auth_service = AuthService()