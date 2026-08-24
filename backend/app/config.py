import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://cctv:cctv123@localhost:5432/cctv_db"
    )

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_STREAM_NAME: str = os.getenv("REDIS_STREAM_NAME", "cctv_events")

    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_ADMIN_NUMBER: str = os.getenv("WHATSAPP_ADMIN_NUMBER", "")

    UNKNOWN_FACE_THRESHOLD: float = float(os.getenv("UNKNOWN_FACE_THRESHOLD", 0.45))
    RESTRICTED_OBJECTS: list = [
        o.strip().lower()
        for o in os.getenv("RESTRICTED_OBJECTS", "knife,gun,backpack").split(",")
    ]
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", 0.4))

    # Two-tier detection: light model runs continuously, heavier model confirms trespass events
    LIGHT_MODEL: str = os.getenv("LIGHT_MODEL", "yolov8n.pt")
    FORENSIC_MODEL: str = os.getenv("FORENSIC_MODEL", "yolov8m.pt")

    SNAPSHOT_DIR: str = os.getenv("SNAPSHOT_DIR", "data/snapshots")

    # --- Auth ---
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-this-secret-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", 480))
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "cctv2024")


settings = Settings()
os.makedirs(settings.SNAPSHOT_DIR, exist_ok=True)
