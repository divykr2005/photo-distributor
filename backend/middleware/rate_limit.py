import os
import redis
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_token_from_request(request: Request) -> str:
    """Extract access token from query params or path parameters for token-based rate limiting."""
    token = request.query_params.get("token")
    if token:
        return f"token_{token}"

    session = request.query_params.get("session")
    if session:
        return f"session_{session}"

    token_param = request.path_params.get("token") or request.path_params.get("access_code")
    if token_param:
        return f"token_{token_param}"

    return get_remote_address(request)


def _init_limiter() -> Limiter:
    try:
        client = redis.from_url(redis_url, socket_timeout=0.5)
        client.ping()
        return Limiter(
            key_func=get_remote_address,
            storage_uri=redis_url,
            strategy="moving-window",
        )
    except Exception:
        return Limiter(
            key_func=get_remote_address,
            storage_uri="memory://",
            strategy="moving-window",
        )


limiter = _init_limiter()


def custom_rate_limit_exceeded_handler(request: Request, exc: Exception) -> Response:
    """Return uniform 429 Too Many Requests response with Retry-After header per D29."""
    headers = {"Retry-After": "60"}
    return JSONResponse(
        status_code=429,
        headers=headers,
        content={"detail": "Rate limit exceeded. Please try again later."},
    )
