"""
AI microservice — face embedding pipeline.
Wraps the same FaceProcessor used in the backend worker so the
backend can call it over HTTP (or keep calling the worker directly
during Week 1 dev without Docker networking).
"""
import os
import tempfile
import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

# Reuse the processor from the backend worker package.
# In the Docker setup the ai-service copies that module in; for local dev
# it's on PYTHONPATH because both services share the repo root.
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from worker.face_processor import FaceProcessor, FaceQualityError  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Face Embedding Service", version="1.0.0")


class EmbeddingResponse(BaseModel):
    embedding: list[float]
    quality_score: float
    embedding_dim: int
    model_version: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/embed", response_model=EmbeddingResponse)
async def embed(file: UploadFile = File(...)):
    """
    Accept an image, run quality checks + ArcFace embedding.
    Returns the 512-dim embedding and quality score.
    Raises 422 with actionable detail on any quality failure.
    """
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Only JPEG, PNG, or WebP accepted.")

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(400, "Image must be under 5 MB.")

    # Write to a temp file so OpenCV/DeepFace can read it by path
    suffix = "." + (file.filename or "img.jpg").rsplit(".", 1)[-1]
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        processor = FaceProcessor.get_instance()
        embedding, quality_score = processor.process_image(tmp_path)
    except FaceQualityError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        logger.error(f"Unexpected embedding error: {e}")
        raise HTTPException(500, "Embedding generation failed.")
    finally:
        os.unlink(tmp_path)

    return EmbeddingResponse(
        embedding=embedding,
        quality_score=quality_score,
        embedding_dim=len(embedding),
        model_version="ArcFace",
    )
