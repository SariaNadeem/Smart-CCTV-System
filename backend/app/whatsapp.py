"""
Sends WhatsApp alerts using Meta's free-tier WhatsApp Cloud API.
Setup: https://developers.facebook.com/docs/whatsapp/cloud-api/get-started
"""
import requests
from app.config import settings


def send_whatsapp_text(message: str) -> dict:
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        print("[whatsapp] Skipped: WHATSAPP_TOKEN / PHONE_NUMBER_ID not configured.")
        return {"skipped": True}

    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": settings.WHATSAPP_ADMIN_NUMBER,
        "type": "text",
        "text": {"body": message},
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        return resp.json()
    except Exception as exc:
        print(f"[whatsapp] Failed to send alert: {exc}")
        return {"error": str(exc)}


def build_unknown_person_message(camera_name, timestamp, confidence):
    return (
        "🚨 Unknown Person Detected\n"
        f"Camera: {camera_name}\n"
        f"Time: {timestamp}\n"
        f"Confidence: {confidence:.0%}\n"
        "Status: Face not found in registered members."
    )


def build_restricted_object_message(camera_name, object_name, timestamp, confidence):
    return (
        "🚨 Restricted Object Detected\n"
        f"Camera: {camera_name}\n"
        f"Object: {object_name}\n"
        f"Time: {timestamp}\n"
        f"Confidence: {confidence:.0%}"
    )
