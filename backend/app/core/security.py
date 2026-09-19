from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# ผ่อนผันความคลาดเคลื่อนของนาฬิกาเวลาตรวจ token
#
# PyJWT ตัดเศษวินาทีทิ้งตอนสร้าง iat/exp (timegm ของ utctimetuple) แต่ตอนตรวจ
# เทียบกับเวลาแบบทศนิยม ถ้านาฬิกาของเครื่องขยับถอยแม้เพียงเสี้ยววินาที
# — ซึ่งเกิดบ่อยบน WSL เวลาเครื่องโฮสต์ sleep แล้วตื่น — token ที่เพิ่งออกจะถูก
# ปฏิเสธด้วย ImmatureSignatureError ทั้งที่ทุกอย่างถูกต้อง
#
# อาการคือผู้ใช้ถูกเด้งออกแบบสุ่มโดยไม่มีสาเหตุ ซึ่งอันตรายมากตอนสาธิตสด
# RFC 7519 ข้อ 4.1.5 อนุญาตให้ผ่อนผันเล็กน้อยเพื่อรองรับเรื่องนี้โดยเฉพาะ
CLOCK_SKEW_LEEWAY = timedelta(seconds=30)


def hash_password(plain: str) -> str:
    """NFR: รหัสผ่านต้องเข้ารหัสแบบทางเดียว ห้ามเก็บเป็นข้อความธรรมดา"""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str, role: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        leeway=CLOCK_SKEW_LEEWAY,
    )
