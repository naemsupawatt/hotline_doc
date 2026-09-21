"""ค่าที่ต้องบังคับให้เหมือนกันทุกเคส ไม่ว่าเครื่องที่รันจะตั้ง .env ไว้อย่างไร"""

import pytest

from app.core.config import settings

# ค่าใน .env ที่เปลี่ยนพฤติกรรมการส่งอีเมล ถ้าปล่อยไว้ ผลเทสต์จะขึ้นกับเครื่องที่รัน
FORCED = {
    "STORAGE_BACKEND": "local",
    "SUPABASE_SECRET_KEY": "",
    # เครื่องที่ตั้ง smtp ไว้ใช้งานจริง ถ้าไม่บังคับ การรันเทสต์จะพยายามยิงเมลจริง
    # ไปหาที่อยู่สมมติอย่าง pytest-officer-owner-xxx@example.com ทุกครั้งที่เคสไหน
    # ก็ตามสั่งให้เจ้าหน้าที่ตัดสินคำขอ ซึ่งช้า พึ่งเน็ต และทำให้บัญชีผู้ส่งเสียชื่อ
    "EMAIL_BACKEND": "outbox",
    # โหมดทดสอบเปลี่ยนปลายทางทุกฉบับ เคสที่ตรวจว่า "ส่งถึงผู้ยื่นคนนั้นจริงไหม"
    # จะล้มทันทีถ้าเครื่องเปิดโหมดนี้ค้างไว้ เคสที่ต้องการโหมดนี้ให้เปิดเองในเคส
    "EMAIL_REDIRECT_TO": "",
}


@pytest.fixture(autouse=True, scope="session")
def stable_email_settings():
    original = {key: getattr(settings, key) for key in FORCED}
    for key, value in FORCED.items():
        setattr(settings, key, value)
    yield
    for key, value in original.items():
        setattr(settings, key, value)
