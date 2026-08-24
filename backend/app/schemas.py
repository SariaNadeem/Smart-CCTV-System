from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class EventOut(BaseModel):
    id: int
    event_type: str
    camera_name: str
    timestamp: datetime
    snapshot_path: Optional[str] = None
    person_name: Optional[str] = None
    is_unknown: bool
    object_name: Optional[str] = None
    confidence: Optional[float] = None
    in_zone: bool

    class Config:
        from_attributes = True


class KnownFaceOut(BaseModel):
    id: int
    name: str
    photo_path: Optional[str] = None
    created_at: datetime
    photo_count: int = 0

    class Config:
        from_attributes = True


class CameraCreate(BaseModel):
    name: str
    source: str


class CameraOut(BaseModel):
    id: int
    name: str
    source: str
    is_active: bool

    class Config:
        from_attributes = True


class StatisticsOut(BaseModel):
    total_events: int
    unknown_person_events: int
    restricted_object_events: int
    known_person_events: int
    forensic_confirmations: int
    total_known_faces: int
    active_cameras: int


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class ZoneIn(BaseModel):
    camera_id: int
    points: list[list[float]]  # [[x,y], [x,y], ...] in source-frame pixel coords


class ZoneOut(BaseModel):
    camera_id: int
    points: list[list[float]]


class WorkerHealth(BaseModel):
    camera_id: int
    camera_name: str
    running: bool
    last_frame_at: Optional[str] = None
    frames_processed: int = 0


class HealthOut(BaseModel):
    api_status: str
    redis_connected: bool
    database_connected: bool
    workers: list[WorkerHealth]
