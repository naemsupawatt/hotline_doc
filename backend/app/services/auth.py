"""M1 — ตรรกะการเข้าสู่ระบบ

แยกจาก endpoint ตามกฎของทีม (ห้ามเขียน business logic ปนใน router)

ทุกครั้งที่ล็อกอิน ไม่ว่าสำเร็จหรือไม่ ต้องเขียน AuditLog
การล็อกอินไม่สำเร็จคือ "ความพยายามเข้าถึง" แบบเดียวกับ T-09
ถ้าบันทึกเฉพาะที่สำเร็จ จะตรวจการเดารหัสผ่านย้อนหลังไม่ได้เลย
"""

from datetime import UTC, date, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.audit import AuditLog
from app.models.enums import UserRole
from app.models.user import User

# โหมดสาธิต: รหัสยืนยันคงที่ เพราะยังไม่ได้ต่อระบบส่งอีเมล/SMS จริง
# ระบบจริงต้องสุ่มรหัสต่อครั้ง มีวันหมดอายุ และจำกัดจำนวนครั้งที่กรอกผิด
DEMO_OTP = "123456"


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


def register(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    national_id: str,
    birth_date: date,
    email: str,
    password: str,
    ip: str | None = None,
) -> tuple[User | None, str | None]:
    """สร้างบัญชีใหม่ในสถานะ "ยังไม่ยืนยันตัวตน" (M1)

    คืน (ผู้ใช้, ข้อความผิดพลาด) เหมือน authenticate เพื่อให้ endpoint จัดการแบบเดียวกัน

    ไม่ auto-login หลังสมัคร เพราะ M1 กำหนดให้มี "กลไกยืนยันตัวตนเพื่อแยก
    ผู้ใช้จริงออกจากบัญชีขยะ" ถ้าสมัครแล้วใช้งานได้เลย กลไกนั้นก็ไม่มีความหมาย
    """
    key = email.strip().lower()

    if db.scalar(select(User).where(User.email == key)):
        return None, "อีเมลนี้ถูกใช้สมัครไว้แล้ว กรุณาเข้าสู่ระบบ หรือใช้อีเมลอื่น"

    if db.scalar(select(User).where(User.national_id == national_id)):
        # ไม่บอกว่าบัญชีนั้นคืออีเมลอะไร เพราะจะกลายเป็นช่องทางเชื่อมเลขบัตรกับอีเมล
        return None, "เลขประจำตัวประชาชนนี้ถูกใช้สมัครไว้แล้ว หากไม่ได้สมัครเอง กรุณาติดต่อเจ้าหน้าที่"

    user = User(
        email=key,
        first_name=first_name,
        last_name=last_name,
        national_id=national_id,
        birth_date=birth_date,
        password_hash=hash_password(password),
        role=UserRole.OPERATOR,
        is_verified=False,
        verification_code=DEMO_OTP,
    )
    db.add(user)
    db.flush()

    # detail ห้ามมีเลขบัตรเต็ม — ใช้แบบปิดบังเท่านั้น
    log_attempt(
        db,
        user=user,
        outcome="success",
        detail=f"สมัครสมาชิก (บัตร {user.national_id_masked})",
        ip=ip,
    )
    return user, None


def verify_otp(
    db: Session, email: str, code: str, ip: str | None = None
) -> tuple[User | None, str | None]:
    """ยืนยันตัวตนด้วยรหัส 6 หลัก (M1)"""
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        return None, "ไม่พบบัญชีที่ใช้อีเมลนี้ กรุณาสมัครสมาชิกก่อน"

    if user.is_verified:
        # ห้ามคืน token ให้บัญชีที่ยืนยันไปแล้วโดยไม่ตรวจรหัส
        # ไม่งั้นใครที่รู้อีเมลก็ยิง endpoint นี้ด้วยรหัสมั่ว ๆ แล้วได้ token ไปเลย
        return None, "บัญชีนี้ยืนยันตัวตนเรียบร้อยแล้ว กรุณาเข้าสู่ระบบตามปกติ"

    if not user.verification_code or user.verification_code != code.strip():
        log_attempt(db, user=user, outcome="denied", detail="รหัสยืนยันไม่ถูกต้อง", ip=ip)
        return None, "รหัสยืนยันไม่ถูกต้อง กรุณาตรวจสอบแล้วลองใหม่อีกครั้ง"

    user.is_verified = True
    user.verified_at = datetime.now(UTC)
    user.verification_code = None
    log_attempt(db, user=user, outcome="success", detail="ยืนยันตัวตนสำเร็จ", ip=ip)
    return user, None
