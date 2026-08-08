from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.endpoints import auth, events, dashboard
from core.config import settings
from middleware.rate_limit import limiter

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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


@app.get("/")
def root():
    return {"message": "Welcome to AI Event Photo Distribution API"}

