from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """ค่าคอนฟิกทั้งหมดอ่านจากไฟล์ .env — ห้าม hard-code ค่าลับไว้ในโค้ด"""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/hotline"
    JWT_SECRET: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    STORAGE_DIR: str = "./storage"
    MAX_UPLOAD_MB: int = 10

    # ที่อยู่ของหน้าเว็บ ใช้ประกอบลิงก์ในอีเมลแจ้งเตือน
    APP_BASE_URL: str = "http://localhost:3000"

    # ---------- อีเมลแจ้งเตือน (ดู services/notification.py) ----------
    # outbox = เขียนไฟล์ลง STORAGE_DIR/outbox ไม่ต้องมีเซิร์ฟเวอร์เมล (ค่าเริ่มต้น)
    # smtp   = ส่งจริงตามค่าด้านล่าง
    EMAIL_BACKEND: str = "outbox"
    EMAIL_FROM: str = "HoTLinE Doc <no-reply@hotline-doc.local>"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_STARTTLS: bool = True
    # โหมดทดสอบ: ใส่ที่อยู่เดียวแล้วอีเมลถึงผู้ยื่น "ทุกฉบับ" จะถูกส่งมาที่นี่แทน
    # ว่าง = ส่งถึงผู้ยื่นตัวจริงตามปกติ (ต้องว่างตอนใช้งานจริง)
    EMAIL_REDIRECT_TO: str = ""
    # งานส่งเมลรันหลังตอบ response แล้ว จึงต้องไม่ค้างยาว
    SMTP_TIMEOUT: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
