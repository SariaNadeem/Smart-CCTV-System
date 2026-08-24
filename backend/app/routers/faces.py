import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KnownFace, FaceEmbedding
from app.schemas import KnownFaceOut
from app.face_engine import extract_faces
from app.config import settings
from app.auth import get_current_user

router = APIRouter(tags=["Faces"])


@router.post("/register-face", response_model=KnownFaceOut)
async def register_face(
    name: str = Form(...),
    files: list[UploadFile] = File(..., description="2-4 clear front-facing photos recommended"),
    db: Session = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """
    Multi-photo registration: every uploaded photo that contains a detectable
    face becomes its own embedding row for this person, which meaningfully
    improves recognition across different lighting/angles.
    """
    known_face = KnownFace(name=name)
    db.add(known_face)
    db.flush()  # get id before commit

    saved_count = 0
    cover_photo_path = None

    for idx, file in enumerate(files):
        contents = await file.read()
        img_array = np.frombuffer(contents, np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if frame is None:
            continue

        faces = extract_faces(frame)
        if not faces:
            continue  # skip photos with no detectable face, don't fail the whole batch

        photo_path = f"{settings.SNAPSHOT_DIR}/known_{name}_{idx}.jpg"
        cv2.imwrite(photo_path, frame)
        if cover_photo_path is None:
            cover_photo_path = photo_path

        embedding = FaceEmbedding(
            face_id=known_face.id, vector=faces[0].embedding.tolist(), photo_path=photo_path
        )
        db.add(embedding)
        saved_count += 1

    if saved_count == 0:
        db.rollback()
        raise HTTPException(400, "No face detected in any of the uploaded photos")

    known_face.photo_path = cover_photo_path
    db.commit()
    db.refresh(known_face)

    result = KnownFaceOut.model_validate(known_face)
    result.photo_count = saved_count
    return result


@router.get("/known-faces", response_model=list[KnownFaceOut])
def list_known_faces(db: Session = Depends(get_db)):
    faces = db.query(KnownFace).all()
    out = []
    for f in faces:
        item = KnownFaceOut.model_validate(f)
        item.photo_count = len(f.embeddings)
        out.append(item)
    return out


@router.delete("/known-faces/{face_id}")
def delete_known_face(
    face_id: int, db: Session = Depends(get_db), user: str = Depends(get_current_user)
):
    known_face = db.query(KnownFace).filter(KnownFace.id == face_id).first()
    if not known_face:
        raise HTTPException(404, "Face not found")
    db.delete(known_face)  # cascade deletes all embeddings for this person
    db.commit()
    return {"status": "deleted", "id": face_id, "name": known_face.name}
