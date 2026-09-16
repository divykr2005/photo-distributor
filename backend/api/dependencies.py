from typing import Generator

from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from core.config import settings
from database.session import SessionLocal
from models.user import User

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_csrf_token(request: Request):
    """Dependency to verify the Double-Submit Cookie CSRF token.
    In local development we make this check optional to allow API clients
    (e.g., scripts) that do not have a CSRF cookie. In production the
    token should be required for state‑changing requests.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("x-csrf-token")

    if settings.ENVIRONMENT == "dev" and (not csrf_cookie or not csrf_header):
        return

    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed",
        )

def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    _ = Depends(verify_csrf_token),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user


def verify_firebase_token_dep(request: Request) -> dict:
    """
    Dependency to verify a Firebase ID token sent in the Authorization header.
    Returns the decoded token dictionary (which includes 'phone_number').
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    id_token = auth_header.split(" ")[1]

    from services.firebase import verify_token
    try:
        decoded_token = verify_token(id_token)
        return decoded_token
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
