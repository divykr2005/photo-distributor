from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.config import settings
from core.security import (
    create_access_token,
    create_refresh_token_string,
    verify_password,
)
from models.refresh_token import RefreshToken
from models.user import User
from repositories.user_repository import UserRepository
from schemas.user import UserCreate


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def register_user(self, user_in: UserCreate) -> User:
        user = self.user_repo.get_user_by_email(email=user_in.email)
        if user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        return self.user_repo.create_user(user_in=user_in)

    def authenticate_user(self, email: str, password: str) -> User | None:
        user = self.user_repo.get_user_by_email(email=email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def _create_token_pair(self, user: User) -> dict:
        """Create an access + refresh token pair for the given user."""
        # Access token
        access_token_expires = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires,
        )

        # Refresh token — stored in DB
        refresh_token_str = create_refresh_token_string()
        refresh_token = RefreshToken(
            user_id=user.id,
            token=refresh_token_str,
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
        self.db.add(refresh_token)
        self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer",
        }

    def login_for_access_token(self, email: str, password: str) -> dict:
        user = self.authenticate_user(email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return self._create_token_pair(user)

    def login_with_google(self, email: str, name: str) -> dict:
        user = self.user_repo.get_user_by_email(email=email)
        if not user:
            # Create user without password
            user = User(
                email=email,
                name=name,
                password_hash=None
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        return self._create_token_pair(user)

    def refresh_access_token(self, refresh_token_str: str) -> dict:
        """Validate the refresh token, revoke it, and issue a new pair (rotation)."""
        token = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token == refresh_token_str)
            .first()
        )

        if not token or token.revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked refresh token",
            )

        if token.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired",
            )

        # Revoke the old token (rotation)
        token.revoked = True
        self.db.commit()

        # Issue a new pair
        user = self.db.query(User).filter(User.id == token.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
        return self._create_token_pair(user)

    def logout(self, refresh_token_str: str) -> None:
        """Revoke the given refresh token."""
        token = (
            self.db.query(RefreshToken)
            .filter(RefreshToken.token == refresh_token_str)
            .first()
        )
        if token and not token.revoked:
            token.revoked = True
            self.db.commit()
