from fastapi import APIRouter
from sqlalchemy import text

from app.database import SessionLocal
from app.redis_stream import _client as redis_client
from app.camera_worker import get_all_worker_status
from app.schemas import HealthOut, WorkerHealth

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthOut)
def health():
    db_ok = True
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception:
        db_ok = False

    redis_ok = True
    try:
        redis_client.ping()
    except Exception:
        redis_ok = False

    workers = [WorkerHealth(**w) for w in get_all_worker_status()]

    return HealthOut(
        api_status="running",
        redis_connected=redis_ok,
        database_connected=db_ok,
        workers=workers,
    )
