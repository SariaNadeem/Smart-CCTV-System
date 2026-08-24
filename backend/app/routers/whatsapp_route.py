from fastapi import APIRouter
from pydantic import BaseModel

from app.whatsapp import send_whatsapp_text

router = APIRouter(tags=["WhatsApp"])


class WhatsAppMessage(BaseModel):
    message: str


@router.post("/send-whatsapp")
def send_whatsapp(payload: WhatsAppMessage):
    result = send_whatsapp_text(payload.message)
    return {"result": result}
