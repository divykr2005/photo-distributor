import os
import firebase_admin
from firebase_admin import credentials, auth
import logging

logger = logging.getLogger(__name__)

# Track if initialized to prevent duplicate app errors in hot-reloading dev environments
_initialized = False

def init_firebase():
    global _initialized
    if _initialized:
        return

    try:
        # Check if default app is already initialized
        firebase_admin.get_app()
        _initialized = True
        return
    except ValueError:
        pass

    firebase_credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if not firebase_credentials_path:
        logger.warning("FIREBASE_CREDENTIALS_PATH not set. Firebase Auth will not work.")
        return

    if not os.path.exists(firebase_credentials_path):
        logger.error(f"Firebase credentials file not found at {firebase_credentials_path}")
        return

    try:
        cred = credentials.Certificate(firebase_credentials_path)
        firebase_admin.initialize_app(cred)
        _initialized = True
        logger.info("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

def verify_token(id_token: str) -> dict:
    """
    Verifies a Firebase ID token.
    Returns the decoded token dictionary if valid.
    Raises ValueError if invalid or expired.
    """
    if not _initialized:
        init_firebase()
        if not _initialized:
            raise ValueError("Firebase is not initialized on the server.")

    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        raise ValueError(f"Invalid Firebase ID token: {e}")
