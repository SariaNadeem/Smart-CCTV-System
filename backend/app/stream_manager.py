"""
Thread-safe in-memory store of the latest JPEG frame per camera, so the
FastAPI MJPEG endpoint can serve a live view without touching the camera
directly (the camera_worker thread owns the capture device).
"""
import threading

_lock = threading.Lock()
_latest_frames: dict[int, bytes] = {}


def publish_frame(camera_id: int, jpeg_bytes: bytes):
    with _lock:
        _latest_frames[camera_id] = jpeg_bytes


def get_latest_frame(camera_id: int) -> bytes | None:
    with _lock:
        return _latest_frames.get(camera_id)


def clear_frame(camera_id: int):
    with _lock:
        _latest_frames.pop(camera_id, None)
