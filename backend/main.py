from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.endpoints import auth, events, dashboard, guests, event_photos, photos, uploads, matches, media, pipeline, magic_links, public, public_media, public_selfie, public_download, public_zip, notifications, clusters, public_registration
from core.config import settings
from middleware.rate_limit import limiter

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for dev flexibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=settings.JWT_SECRET or "random_secret")

from fastapi.responses import PlainTextResponse
from middleware.rate_limit import limiter, custom_rate_limit_exceeded_handler
from middleware.security_headers import SecurityHeadersMiddleware

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)  # type: ignore

# Routers
app.include_router(
    auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"]
)
app.include_router(
    events.router, prefix=f"{settings.API_V1_STR}/events", tags=["events"]
)
app.include_router(
    dashboard.router, prefix=f"{settings.API_V1_STR}/dashboard", tags=["dashboard"]
)
app.include_router(
    guests.router, prefix=f"{settings.API_V1_STR}/guests", tags=["guests"]
)
app.include_router(
    photos.router, prefix=f"{settings.API_V1_STR}", tags=["photos"]
)
app.include_router(
    event_photos.router, prefix=f"{settings.API_V1_STR}/events", tags=["event_photos"]
)
app.include_router(
    uploads.router, prefix=f"{settings.API_V1_STR}", tags=["uploads"]
)
app.include_router(
    matches.router, prefix=f"{settings.API_V1_STR}", tags=["matches"]
)
app.include_router(
    media.router, prefix=f"{settings.API_V1_STR}", tags=["media"]
)
app.include_router(
    pipeline.router, prefix=f"{settings.API_V1_STR}", tags=["pipeline"]
)
app.include_router(
    clusters.router, prefix=f"{settings.API_V1_STR}/events", tags=["clusters"]
)

# Week 3: organizer magic-link management
app.include_router(
    magic_links.router, prefix=f"{settings.API_V1_STR}", tags=["magic_links"]
)
app.include_router(
    notifications.router, prefix=f"{settings.API_V1_STR}", tags=["notifications"]
)

# Week 3: public portal (no JWT — token-validated)
app.include_router(
    public.router, prefix=f"{settings.API_V1_STR}/public", tags=["public"]
)
app.include_router(
    public_media.router, prefix=f"{settings.API_V1_STR}/public", tags=["public_media"]
)
app.include_router(
    public_selfie.router, prefix=f"{settings.API_V1_STR}/public", tags=["public_selfie"]
)
app.include_router(
    public_download.router, prefix=f"{settings.API_V1_STR}/public", tags=["public_download"]
)
app.include_router(
    public_zip.router, prefix=f"{settings.API_V1_STR}/public", tags=["public_zip"]
)
app.include_router(
    public_registration.router, prefix=f"{settings.API_V1_STR}/public", tags=["public_registration"]
)
app.include_router(
    notifications.public_opt_out_router, prefix=f"{settings.API_V1_STR}", tags=["public_opt_out"]
)

import os
from fastapi import HTTPException
from fastapi.responses import Response, FileResponse
from services.storage import get_storage_backend
# Serve uploaded files via storage backend (supports Local AND R2 seamlessly)
@app.get("/uploads/{file_path:path}")
def serve_uploads(file_path: str):
    storage = get_storage_backend()
    storage_key = f"uploads/{file_path}"
    try:
        data = storage.get(storage_key)
        if data:
            # Guess mime type basic
            media_type = "image/jpeg"
            if file_path.lower().endswith(".png"): media_type = "image/png"
            elif file_path.lower().endswith(".webp"): media_type = "image/webp"
            return Response(content=data, media_type=media_type)
    except Exception:
        pass
    
    # Fallback to checking local dir just in case
    local_path = os.path.join(os.path.dirname(__file__), "uploads", file_path)
    if os.path.exists(local_path):
        return FileResponse(local_path)
        
    raise HTTPException(status_code=404, detail="File not found")


@app.get("/robots.txt", response_class=PlainTextResponse)
def get_robots_txt():
    return "User-agent: *\nDisallow: /g/\nDisallow: /events/*/find\n"


@app.get("/")
def root():
    return {"message": "Welcome to AI Event Photo Distribution API"}
