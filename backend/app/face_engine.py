"""
Face recognition wrapper around InsightFace.
Handles: embedding extraction + matching against known faces stored in pgvector.
"""
import numpy as np
from insightface.app import FaceAnalysis
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import FaceEmbedding, KnownFace
from app.config import settings

# 'buffalo_l' is a free, pre-trained InsightFace model bundle (downloads on first run)
_face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
_face_app.prepare(ctx_id=0, det_size=(640, 640))


def extract_faces(frame: np.ndarray):
    """Returns list of insightface Face objects detected in a BGR frame."""
    return _face_app.get(frame)


def match_face(embedding: np.ndarray, db: Session):
    """
    Compares an embedding against all known face embeddings using cosine distance
    via pgvector's <=> operator. Returns (name, distance) or (None, None) if no match.
    """
    result = db.execute(
        select(FaceEmbedding, KnownFace.name)
        .join(KnownFace, FaceEmbedding.face_id == KnownFace.id)
        .order_by(FaceEmbedding.vector.cosine_distance(embedding))
        .limit(1)
    ).first()

    if result is None:
        return None, None

    face_embedding, name = result
    # recompute exact cosine distance in python for the threshold check
    stored = np.array(face_embedding.vector, dtype=np.float32)
    cos_sim = np.dot(embedding, stored) / (
        np.linalg.norm(embedding) * np.linalg.norm(stored) + 1e-8
    )
    cos_distance = 1 - cos_sim

    if cos_distance <= settings.UNKNOWN_FACE_THRESHOLD:
        return name, float(cos_distance)
    return None, float(cos_distance)
