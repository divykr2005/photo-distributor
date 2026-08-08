from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from middleware.rate_limit import limiter
from models.user import User
from schemas.user import RefreshTokenRequest, Token, UserCreate, UserResponse
from services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.register_user(user_in)


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    return auth_service.login_for_access_token(
        email=form_data.username, password=form_data.password
    )


@router.post("/refresh", response_model=Token)
def refresh_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.refresh_access_token(body.refresh_token)


@router.post("/logout", status_code=204)
def logout(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    auth_service.logout(body.refresh_token)


@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
