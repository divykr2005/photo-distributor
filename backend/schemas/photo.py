from datetime import datetime
from uuid import UUID
from typing import Optional, List
from pydantic import BaseModel


class PhotoFaceResponse(BaseModel):
    id: UUID
    photo_id: UUID
    event_id: UUID
    bbox_x: float
    bbox_y: float
    bbox_w: float
    bbox_h: float
    det_score: float
    model_version: str
    embedding_dim: int
    quality_score: Optional[float] = None
    blur_score: Optional[float] = None
    face_area_ratio: Optional[float] = None
    yaw: Optional[float] = None
    pitch: Optional[float] = None
    roll: Optional[float] = None
    is_matchable: bool
    quality_flags: Optional[List[str]] = None
    crop_key: Optional[str] = None
    matched_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PhotoUploadResponse(BaseModel):
    photo_id: UUID
    duplicate: bool = False


class PhotoResponse(BaseModel):
    id: UUID
    event_id: UUID
    batch_id: Optional[UUID] = None
    uploaded_by: UUID
    original_filename: str
    content_hash: str
    mime_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    exif_taken_at: Optional[datetime] = None
    status: str
    face_count: int
    processing_error: Optional[str] = None
    attempts: int
    created_at: datetime
    processed_at: Optional[datetime] = None
    updated_at: datetime
    dup_cluster_id: Optional[UUID] = None
    is_cluster_representative: Optional[bool] = None
    faces: List[PhotoFaceResponse] = []

    class Config:
        from_attributes = True


class PhotoListResponse(BaseModel):
    data: List[PhotoResponse]
    next_cursor: Optional[str] = None
    has_more: bool = False
