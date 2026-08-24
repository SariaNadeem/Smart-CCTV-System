"""
Live MJPEG video stream so the React dashboard can show a real-time feed,
not just after-the-fact event snapshots.

Usage in the browser: <img src="/video_feed/1?token=..." />
(query-param token because <img> tags can't send Authorization headers)
"""
import time
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.stream_manager import get_latest_frame
from app.auth import get_current_user_from_query_or_header

router = APIRouter(tags=["Stream"])


def _mjpeg_generator(camera_id: int):
    boundary = b"--frame"
    while True:
        frame = get_latest_frame(camera_id)
        if frame is not None:
            yield (
                boundary + b"\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
        time.sleep(0.08)  # ~12 fps is plenty for a live monitoring view


@router.get("/video_feed/{camera_id}")
def video_feed(camera_id: int, user: str = Depends(get_current_user_from_query_or_header)):
    return StreamingResponse(
        _mjpeg_generator(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
