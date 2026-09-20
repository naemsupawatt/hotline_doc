"""M1 — ตรรกะการเข้าสู่ระบบ

แยกจาก endpoint ตามกฎของทีม (ห้ามเขียน business logic ปนใน router)

ทุกครั้งที่ล็อกอิน ไม่ว่าสำเร็จหรือไม่ ต้องเขียน AuditLog
การล็อกอินไม่สำเร็จคือ "ความพยายามเข้าถึง" แบบเดียวกับ T-09
ถ้าบันทึกเฉพาะที่สำเร็จ จะตรวจการเดารหัสผ่านย้อนหลังไม่ได้เลย
"""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core import phone as phone_utils
from app.core.security import hash_password, verify_password
from app.models.audit import AuditLog
from app.models.enums import UserRole
from app.models.user import User


def find_user(db: Session, identifier: str) -> User | None:
    """หาผู้ใช้จากอีเมลหรือเบอร์โทร — M1 ให้เข้าได้ทั้งสองช่องทาง

    เบอร์โทรเก็บเป็นตัวเลขล้วน จึงต้อง normalize ก่อนค้นหา ไม่งั้นคนที่
    พิมพ์ "081-234-5678" จะเข้าระบบไม่ได้ทั้งที่เป็นเบอร์เดียวกับที่สมัครไว้
    """
    key = identifier.strip().lower()
    digits = phone_utils.normalize(key)

    matches = [User.email == key]
    # เทียบกับคอลัมน์ phone เฉพาะเมื่อสิ่งที่กรอกมีตัวเลขพอจะเป็นเบอร์ได้
    # ไม่งั้นอีเมลอย่าง a1@example.com จะถูกตีความเป็นเบอร์ "1"
    if phone_utils.is_valid(digits):
        matches.append(User.phone == digits)

    return db.scalar(select(User).where(or_(*matches)))


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
    generic = "อีเมล เบอร์โทรศัพท์ หรือรหัสผ่านไม่ถูกต้อง กรุณาตรวจสอบแล้วลองใหม่อีกครั้ง"

    if user is None:
        log_attempt(db, user=None, outcome="denied", detail=f"ไม่พบบัญชี: {identifier}", ip=ip)
        return None, generic

    if not verify_password(password, user.password_hash):
        log_attempt(db, user=user, outcome="denied", detail="รหัสผ่านไม่ถูกต้อง", ip=ip)
        return None, generic

    if not user.is_active:
        log_attempt(db, user=user, outcome="denied", detail="บัญชีถูกปิดใช้งาน", ip=ip)
        return None, "บัญชีนี้ถูกปิดใช้งาน กรุณาติดต่อเจ้าหน้าที่"

    log_attempt(db, user=user, outcome="success", detail="เข้าสู่ระบบสำเร็จ", ip=ip)
    return user, None


def register(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    national_id: str,
    phone: str,
    email: str,
    password: str,
    ip: str | None = None,
) -> tuple[User | None, str | None]:
    """สร้างบัญชีใหม่และให้ใช้งานได้ทันที (M1)

    คืน (ผู้ใช้, ข้อความผิดพลาด) เหมือน authenticate เพื่อให้ endpoint จัดการแบบเดียวกัน

    หมายเหตุ: M1 ระบุว่าต้องมี "กลไกยืนยันตัวตนเพื่อแยกผู้ใช้จริงออกจากบัญชีขยะ"
    ทีมตัดสินใจไม่ทำ OTP ในรอบนี้ กลไกที่เหลืออยู่จึงเป็นการบังคับเลขประจำตัว
    ประชาชนที่ผ่านหลักตรวจสอบและห้ามซ้ำ (ดู core/thai_id.py) — หนึ่งเลขบัตร
    ต่อหนึ่งบัญชีเท่านั้น ถ้ากรรมการถามเรื่องบัญชีขยะ ให้ตอบด้วยข้อนี้
    """
    key = email.strip().lower()

    if db.scalar(select(User).where(User.email == key)):
        return None, "อีเมลนี้ถูกใช้สมัครไว้แล้ว กรุณาเข้าสู่ระบบ หรือใช้อีเมลอื่น"

    if db.scalar(select(User).where(User.phone == phone)):
        return None, "หมายเลขโทรศัพท์นี้ถูกใช้สมัครไว้แล้ว กรุณาเข้าสู่ระบบ หรือใช้เบอร์อื่น"

    if db.scalar(select(User).where(User.national_id == national_id)):
        # ไม่บอกว่าบัญชีนั้นคืออีเมลอะไร เพราะจะกลายเป็นช่องทางเชื่อมเลขบัตรกับอีเมล
        return None, "เลขประจำตัวประชาชนนี้ถูกใช้สมัครไว้แล้ว หากไม่ได้สมัครเอง กรุณาติดต่อเจ้าหน้าที่"

    user = User(
        email=key,
        first_name=first_name,
        last_name=last_name,
        national_id=national_id,
        phone=phone,
        password_hash=hash_password(password),
        role=UserRole.OPERATOR,
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


def update_profile(
    db: Session,
    *,
    user: User,
    first_name: str,
    last_name: str,
    email: str,
    phone: str,
    ip: str | None = None,
) -> tuple[User | None, str | None]:
    """แก้ข้อมูลบัญชีของตัวเอง คืน (ผู้ใช้, ข้อความผิดพลาด) เหมือน register

    อีเมลกับเบอร์โทรเป็นกุญแจเข้าสู่ระบบทั้งคู่ (M1) การแก้จึงต้องกันซ้ำแบบเดียว
    กับตอนสมัคร มิฉะนั้นคนสองคนจะเข้าสู่ระบบด้วยกุญแจเดียวกันไม่ได้ทั้งคู่

    ไม่แตะ national_id และ role โดยตั้งใจ — เลขบัตรคือกลไกกันบัญชีขยะที่เหลืออยู่
    หลังตัดสินใจไม่ทำ OTP ส่วน role ถ้าเจ้าของบัญชีเปลี่ยนเองได้ ก็เท่ากับ
    ใครก็เลื่อนตัวเองเป็นเจ้าหน้าที่ได้
    """
    key = email.strip().lower()

    duplicate_email = db.scalar(select(User).where(User.email == key, User.id != user.id))
    if duplicate_email:
        return None, "อีเมลนี้ถูกใช้กับบัญชีอื่นแล้ว กรุณาใช้อีเมลอื่น"

    duplicate_phone = db.scalar(select(User).where(User.phone == phone, User.id != user.id))
    if duplicate_phone:
        return None, "หมายเลขโทรศัพท์นี้ถูกใช้กับบัญชีอื่นแล้ว กรุณาใช้เบอร์อื่น"

    # บันทึกว่าแก้ "ช่องไหน" ไม่ใช่ "แก้เป็นอะไร" เพราะอีเมลและเบอร์โทรเป็น
    # ข้อมูลส่วนบุคคล ไม่ควรไปกองอยู่ในตาราง audit ที่คนอื่นเปิดอ่านได้
    changed = [
        label
        for label, before, after in (
            ("ชื่อ", user.first_name, first_name),
            ("นามสกุล", user.last_name, last_name),
            ("อีเมล", user.email, key),
            ("เบอร์โทรศัพท์", user.phone, phone),
        )
        if before != after
    ]

    user.first_name = first_name
    user.last_name = last_name
    user.email = key
    user.phone = phone

    db.add(
        AuditLog(
            actor_id=user.id,
            action="profile.update",
            entity_type="app_user",
            entity_id=user.id,
            outcome="success",
            detail=f"แก้ข้อมูลบัญชี: {', '.join(changed)}" if changed else "บันทึกโดยไม่มีการเปลี่ยนแปลง",
            ip_address=ip,
        )
    )
    return user, None


def change_password(
    db: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
    ip: str | None = None,
) -> str | None:
    """เปลี่ยนรหัสผ่าน คืนข้อความผิดพลาด หรือ None เมื่อสำเร็จ

    กรอกรหัสเดิมผิดก็ต้องบันทึกไว้ เพราะเป็น "ความพยายามเข้าถึง" แบบเดียวกับ
    การล็อกอินไม่สำเร็จและ T-09 — ถ้าบันทึกเฉพาะที่สำเร็จ จะตรวจย้อนหลังไม่ได้ว่า
    มีใครเอาโทเคนที่ขโมยไปลองยึดบัญชีหรือไม่
    """
    if not verify_password(current_password, user.password_hash):
        _log_password_change(db, user=user, outcome="denied", detail="รหัสผ่านเดิมไม่ถูกต้อง", ip=ip)
        return "รหัสผ่านเดิมไม่ถูกต้อง กรุณาตรวจสอบแล้วลองใหม่อีกครั้ง"

    if verify_password(new_password, user.password_hash):
        return "รหัสผ่านใหม่ซ้ำกับรหัสผ่านเดิม กรุณาตั้งรหัสผ่านอื่น"

    user.password_hash = hash_password(new_password)
    _log_password_change(db, user=user, outcome="success", detail="เปลี่ยนรหัสผ่านสำเร็จ", ip=ip)
    return None


def _log_password_change(
    db: Session, *, user: User, outcome: str, detail: str, ip: str | None
) -> None:
    db.add(
        AuditLog(
            actor_id=user.id,
            action="password.change",
            entity_type="app_user",
            entity_id=user.id,
            outcome=outcome,
            detail=detail,
            ip_address=ip,
        )
    )
