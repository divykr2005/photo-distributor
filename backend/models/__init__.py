# Import all models here so Alembic's autogenerate can discover them.
from models.user import User  # noqa: F401
from models.refresh_token import RefreshToken  # noqa: F401
from models.event import Event  # noqa: F401
from models.guest import Guest, EmbeddingStatus  # noqa: F401
from models.face_embedding import FaceEmbedding  # noqa: F401
from models.event_photo import EventPhoto  # noqa: F401
from models.photo_match import PhotoMatch  # noqa: F401
