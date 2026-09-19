"""M1 — ตรรกะการเข้าสู่ระบบ

แยกจาก endpoint ตามกฎของทีม (ห้ามเขียน business logic ปนใน router)

ทุกครั้งที่ล็อกอิน ไม่ว่าสำเร็จหรือไม่ ต้องเขียน AuditLog
การล็อกอินไม่สำเร็จคือ "ความพยายามเข้าถึง" แบบเดียวกับ T-09
ถ้าบันทึกเฉพาะที่สำเร็จ จะตรวจการเดารหัสผ่านย้อนหลังไม่ได้เลย
"""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.audit import AuditLog
from app.models.user import User


def find_user(db: Session, identifier: str) -> User | None:
    """หาผู้ใช้จากอีเมลหรือเบอร์โทร — M1 ให้เข้าได้ทั้งสองช่องทาง"""
    key = identifier.strip().lower()
    return db.scalar(select(User).where(or_(User.email == key, User.phone == key)))


def log_attempt(
    db: Session,
    *,
    user: User | None,
    outcome: str,
    detail: str,
    ip: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=user.id if user else None,
            action="login",
            entity_type="app_user",
            entity_id=user.id if user else None,
            outcome=outcome,
            detail=detail,
            ip_address=ip,
        )
    )


def authenticate(
    db: Session, identifier: str, password: str, ip: str | None = None
) -> tuple[User | None, str | None]:
    """คืน (ผู้ใช้, ข้อความผิดพลาดสำหรับผู้ใช้ทั่วไป)

    NFR Usability: ข้อความต้องเป็นภาษาที่ผู้ใช้เข้าใจ ไม่ใช่ error code ดิบ
    NFR Security: ไม่บอกว่า "ไม่พบบัญชีนี้" แยกจาก "รหัสผ่านผิด"
                  เพราะจะกลายเป็นเครื่องมือไล่เดาว่าอีเมลใดมีอยู่ในระบบ
    """
    user = find_user(db, identifier)
    generic = "อีเมลหรือรหัสผ่านไม่ถูกต้อง กรุณาตรวจสอบแล้วลองใหม่อีกครั้ง"

    if user is None:
        log_attempt(db, user=None, outcome="denied", detail=f"ไม่พบบัญชี: {identifier}", ip=ip)
        return None, generic

    if not verify_password(password, user.password_hash):
        log_attempt(db, user=user, outcome="denied", detail="รหัสผ่านไม่ถูกต้อง", ip=ip)
        return None, generic

    if not user.is_active:
        log_attempt(db, user=user, outcome="denied", detail="บัญชีถูกปิดใช้งาน", ip=ip)
        return None, "บัญชีนี้ถูกปิดใช้งาน กรุณาติดต่อเจ้าหน้าที่"

    if not user.is_verified:
        # M1 "กลไกยืนยันตัวตนเพื่อแยกผู้ใช้จริงออกจากบัญชีขยะ"
        log_attempt(db, user=user, outcome="denied", detail="ยังไม่ยืนยันตัวตน", ip=ip)
        return None, "บัญชีนี้ยังไม่ได้ยืนยันตัวตน กรุณายืนยันด้วยรหัสที่ส่งให้ก่อนเข้าสู่ระบบ"

    log_attempt(db, user=user, outcome="success", detail="เข้าสู่ระบบสำเร็จ", ip=ip)
    return user, None
