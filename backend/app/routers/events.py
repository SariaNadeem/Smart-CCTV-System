from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models import Event
from app.schemas import EventOut

router = APIRouter(tags=["Events"])


@router.get("/events", response_model=list[EventOut])
def get_events(
    limit: int = Query(50, le=500),
    event_type: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Event).order_by(desc(Event.timestamp))
    if event_type:
        q = q.filter(Event.event_type == event_type)
    return q.limit(limit).all()


@router.get("/alerts", response_model=list[EventOut])
def get_alerts(limit: int = Query(50, le=500), db: Session = Depends(get_db)):
    """Alerts = unknown persons + restricted objects + forensic confirmations."""
    return (
        db.query(Event)
        .filter(Event.event_type.in_(
            ["unknown_person", "restricted_object", "forensic_confirmation"]
        ))
        .order_by(desc(Event.timestamp))
        .limit(limit)
        .all()
    )
