from fastapi import APIRouter, Depends, Request, HTTPException
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


# Google OAuth Setup
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from fastapi.responses import RedirectResponse
from core.config import settings

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
    """Initiates the Google OAuth flow"""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    redirect_uri = str(request.url_for("google_callback"))
        
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handles the Google OAuth callback and issues our own JWTs"""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")
        if not user_info:
            # Fallback if userinfo is not in token
            user_info = await oauth.google.parse_id_token(request, token)
            
        if not user_info:
            raise HTTPException(status_code=400, detail="Could not parse Google user info")
            
        email = user_info.get("email")
        name = user_info.get("name", email.split("@")[0])
        
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")
            
        auth_service = AuthService(db)
        token_pair = auth_service.login_with_google(email, name)
        
        print(f"DEBUG: Successfully logged in {email}")
        
        # Redirect to frontend callback page with tokens in query params
        frontend_url = settings.FRONTEND_URL
        redirect_url = f"{frontend_url}/auth/callback?access_token={token_pair['access_token']}&refresh_token={token_pair['refresh_token']}"
        print(f"DEBUG: Redirecting to {redirect_url}")
        return RedirectResponse(url=redirect_url)
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Google OAuth error: {e}")
        print(f"DEBUG: Exception in google_callback: {e}")
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/login?error=oauth_failed")
