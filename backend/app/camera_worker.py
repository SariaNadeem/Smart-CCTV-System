"""
One CameraWorker runs per camera in its own thread, so multiple cameras
process independently.

Pipeline per frame:
  capture -> publish live frame (every frame, for the MJPEG stream)
          -> every Nth frame: YOLOv8n objects + InsightFace faces
          -> zone check (only alert if inside the camera's defined zone, if any)
          -> log event -> push to Redis Stream -> WhatsApp alert
          -> if trespass-worthy (unknown person / restricted object in zone):
             re-run detection with the heavier YOLOv8m "forensic" model and
             log a confirmation event with (usually) higher confidence.
"""
import cv2
import json
import time
import threading
from datetime import datetime

from app.database import SessionLocal
from app.models import Event, Zone
from app.face_engine import extract_faces, match_face
from app.object_engine import (
    detect_objects, detect_objects_forensic, filter_restricted, box_center,
)
from app.redis_stream import push_event
from app.whatsapp import (
    send_whatsapp_text,
    build_unknown_person_message,
    build_restricted_object_message,
)
from app.config import settings
from app.stream_manager import publish_frame, clear_frame

INFER_EVERY_N_FRAMES = 5


def _point_in_zone(point, polygon_points) -> bool:
    """cv2.pointPolygonTest expects a numpy int32 array of the polygon."""
    import numpy as np
    poly = np.array(polygon_points, dtype=np.int32)
    return cv2.pointPolygonTest(poly, point, False) >= 0


class CameraWorker:
    def __init__(self, camera_id: int, camera_name: str, source: str):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.source = int(source) if str(source).isdigit() else source
        self._running = False
        self._thread = None
        self.zone_polygon = self._load_zone()

        # health/status info, read by the /health endpoint
        self.status = {
            "camera_id": camera_id,
            "camera_name": camera_name,
            "running": False,
            "last_frame_at": None,
            "frames_processed": 0,
        }

    def _load_zone(self):
        db = SessionLocal()
        try:
            zone = db.query(Zone).filter(Zone.camera_id == self.camera_id).first()
            return json.loads(zone.polygon) if zone else None
        finally:
            db.close()

    def start(self):
        if self._running:
            return
        self._running = True
        self.status["running"] = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        _active_workers[self.camera_id] = self

    def stop(self):
        self._running = False
        self.status["running"] = False
        if self._thread:
            self._thread.join(timeout=2)
        clear_frame(self.camera_id)

    def _save_snapshot(self, frame) -> str:
        filename = f"{self.camera_name}_{int(time.time()*1000)}.jpg"
        path = f"{settings.SNAPSHOT_DIR}/{filename}"
        cv2.imwrite(path, frame)
        return path

    def _log_and_alert(self, event_type, person_name=None, is_unknown=False,
                        object_name=None, confidence=None, frame=None, in_zone=True):
        snapshot_path = self._save_snapshot(frame) if frame is not None else None
        db = SessionLocal()
        try:
            event = Event(
                event_type=event_type,
                camera_name=self.camera_name,
                timestamp=datetime.utcnow(),
                snapshot_path=snapshot_path,
                person_name=person_name,
                is_unknown=is_unknown,
                object_name=object_name,
                confidence=confidence,
                in_zone=in_zone,
            )
            db.add(event)
            db.commit()
        finally:
            db.close()

        push_event({
            "event_type": event_type,
            "camera_name": self.camera_name,
            "timestamp": str(datetime.utcnow()),
            "person_name": person_name,
            "object_name": object_name,
            "confidence": confidence,
        })

        if event_type == "unknown_person":
            msg = build_unknown_person_message(
                self.camera_name, datetime.utcnow().strftime("%I:%M %p"), confidence or 0
            )
            send_whatsapp_text(msg)
        elif event_type == "restricted_object":
            msg = build_restricted_object_message(
                self.camera_name, object_name, datetime.utcnow().strftime("%I:%M %p"), confidence or 0
            )
            send_whatsapp_text(msg)

    def _forensic_confirm(self, frame, trigger_label):
        """Re-run the heavier model on this frame to confirm a trespass event."""
        detections = detect_objects_forensic(frame)
        best = max(detections, key=lambda d: d["confidence"], default=None)
        self._log_and_alert(
            "forensic_confirmation",
            object_name=best["label"] if best else trigger_label,
            confidence=best["confidence"] if best else None,
            frame=frame,
        )

    def _in_zone_or_no_zone(self, box) -> bool:
        if not self.zone_polygon:
            return True  # no zone defined = whole frame counts
        return _point_in_zone(box_center(box), self.zone_polygon)

    def _run(self):
        cap = cv2.VideoCapture(self.source)
        frame_count = 0
        db = SessionLocal()
        try:
            while self._running and cap.isOpened():
                ok, frame = cap.read()
                if not ok:
                    break
                frame_count += 1

                # Publish every frame (not just inference frames) for a smooth live view
                ok_jpeg, buf = cv2.imencode(".jpg", frame)
                if ok_jpeg:
                    publish_frame(self.camera_id, buf.tobytes())

                self.status["last_frame_at"] = datetime.utcnow().isoformat()
                self.status["frames_processed"] += 1

                if frame_count % INFER_EVERY_N_FRAMES != 0:
                    continue

                # --- Object detection (light model) ---
                detections = detect_objects(frame)
                for obj in filter_restricted(detections):
                    inside = self._in_zone_or_no_zone(obj["box"])
                    if not inside:
                        continue  # outside the defined zone, ignore
                    self._log_and_alert(
                        "restricted_object", object_name=obj["label"],
                        confidence=obj["confidence"], frame=frame, in_zone=True,
                    )
                    self._forensic_confirm(frame, obj["label"])

                # --- Face recognition ---
                faces = extract_faces(frame)
                for face in faces:
                    box = tuple(map(int, face.bbox))  # x1,y1,x2,y2
                    inside = self._in_zone_or_no_zone(box)
                    name, distance = match_face(face.embedding, db)
                    if name:
                        self._log_and_alert(
                            "known_person", person_name=name,
                            confidence=1 - (distance or 0), frame=frame, in_zone=inside,
                        )
                    else:
                        if not inside:
                            continue  # unknown but outside the zone -> ignore
                        self._log_and_alert(
                            "unknown_person", is_unknown=True,
                            confidence=1 - (distance or 0), frame=frame, in_zone=True,
                        )
                        self._forensic_confirm(frame, "unknown_person")
        finally:
            cap.release()
            db.close()


# Registry of active workers so API endpoints can start/stop them and check health
_active_workers: dict[int, CameraWorker] = {}


def start_camera(camera_id: int, camera_name: str, source: str):
    if camera_id in _active_workers and _active_workers[camera_id].status["running"]:
        return
    worker = CameraWorker(camera_id, camera_name, source)
    worker.start()


def stop_camera(camera_id: int):
    worker = _active_workers.pop(camera_id, None)
    if worker:
        worker.stop()


def get_all_worker_status():
    return [w.status for w in _active_workers.values()]


def refresh_zone(camera_id: int):
    """Call after saving a new zone so a running worker picks it up immediately."""
    worker = _active_workers.get(camera_id)
    if worker:
        worker.zone_polygon = worker._load_zone()
