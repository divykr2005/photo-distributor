from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware applying security headers to all responses per Day 21 security checklist:
    - X-Content-Type-Options: nosniff
    - Referrer-Policy: no-referrer
    - Content-Security-Policy: restrictive CSP
    - X-Frame-Options: DENY
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline';"
        )

        return response
