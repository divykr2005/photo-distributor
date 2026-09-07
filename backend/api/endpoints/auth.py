import secrets
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from fastapi.responses import RedirectResponse

from api.dependencies import get_current_user, get_db
from middleware.rate_limit import limiter
from models.user import User
from schemas.user import UserCreate, UserResponse
from services.auth_service import AuthService
from core.config import settings

router = APIRouter()

def set_auth_cookies(response: Response, token_pair: dict):
    domain = settings.COOKIE_DOMAIN
    secure = settings.ENVIRONMENT != "dev"
    
    response.set_cookie(
        key="access_token",
        value=token_pair["access_token"],
        httponly=True,
        secure=secure,
        samesite="lax",
        domain=domain,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=token_pair["refresh_token"],
        httponly=True,
        secure=secure,
        samesite="lax",
        domain=domain,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )
    
    # CSRF Token for double-submit
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,  # JS needs to read this
        secure=secure,
        samesite="lax",
        domain=domain,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

def clear_auth_cookies(response: Response):
    domain = settings.COOKIE_DOMAIN
    response.delete_cookie("access_token", domain=domain)
    response.delete_cookie("refresh_token", domain=domain)
    response.delete_cookie("csrf_token", domain=domain)


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.register_user(user_in)


@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    token_pair = auth_service.login_for_access_token(
        email=form_data.username, password=form_data.password
    )
    set_auth_cookies(response, token_pair)
    return {"status": "ok"}


@router.post("/refresh")
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token_str = request.cookies.get("refresh_token")
    if not refresh_token_str:
        raise HTTPException(status_code=401, detail="Refresh token missing")
        
    auth_service = AuthService(db)
    token_pair = auth_service.refresh_access_token(refresh_token_str)
    set_auth_cookies(response, token_pair)
    return {"status": "ok"}


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token_str = request.cookies.get("refresh_token")
    if refresh_token_str:
        auth_service = AuthService(db)
        auth_service.logout(refresh_token_str)
    
    clear_auth_cookies(response)
    return None


@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/dev-login")
def dev_login(response: Response, email: str = "test@example.com", name: str = "Test User", db: Session = Depends(get_db)):
    if settings.ENVIRONMENT != "dev":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test bypass only available in development environment",
        )
    auth_service = AuthService(db)
    token_pair = auth_service.login_with_google(email, name)
    set_auth_cookies(response, token_pair)
    return {"status": "ok"}


# Temporary config object for authlib
starlette_config = Config(environ={
    "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID or "",
    "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET or "",
})

oauth = OAuth(starlette_config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@router.get("/google/login")
async def google_login(request: Request):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    redirect_uri = str(request.url_for("google_callback"))
    
    if "up.railway.app" in redirect_uri and redirect_uri.startswith("http://"):
        redirect_uri = redirect_uri.replace("http://", "https://", 1)
        
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        if not user_info:
            user_info = await oauth.google.parse_id_token(request, token)
            
        if not user_info:
            raise HTTPException(status_code=400, detail="Could not parse Google user info")
            
        email = user_info.get("email")
        name = user_info.get("name", email.split("@")[0])
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
            
        auth_service = AuthService(db)
        token_pair = auth_service.login_with_google(email, name)
        
        frontend_url = settings.FRONTEND_URL
        redirect_url = f"{frontend_url}/dashboard"
        
        response = RedirectResponse(url=redirect_url)
        set_auth_cookies(response, token_pair)
        return response
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Google OAuth error: {e}")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=oauth_failed")
