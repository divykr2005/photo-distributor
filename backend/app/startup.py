# backend/app/startup.py

"""Startup utilities for the FastAPI application.

This module logs resolved configuration values on application startup.
"""

import logging
from fastapi import FastAPI
from core.config import settings


def register_startup_logs(app: FastAPI) -> None:
    """Register a startup event that logs important URLs.

    Args:
        app: The FastAPI application instance.
    """

    @app.on_event("startup")
    async def log_configuration() -> None:
        logging.info("Resolved FRONTEND_URL: %s", settings.FRONTEND_URL)
        logging.info("Resolved API_BASE_URL: %s", settings.API_BASE_URL)

    # Additional startup tasks can be added here.
