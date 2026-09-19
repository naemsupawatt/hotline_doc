"""M6 — เริ่มยื่นคำขอ: สร้างผู้ประกอบการ / ที่พัก / คำขอ จากคำตอบใน wizard

จุดที่ต้องระวังที่สุดในไฟล์นี้: **จำแนกประเภทใหม่ฝั่งเซิร์ฟเวอร์เสมอ**
ห้ามเชื่อผลจำแนกที่ client ส่งมา ไม่งั้นใครก็ยิง API บอกว่าตัวเองเป็น
"ไม่เข้าข่ายโรงแรม" ได้ทั้งที่มี 60 ห้อง

ทุกการสร้างคำขอเขียน 3 อย่างเสมอ:
  1. ApplicationClassification — snapshot ว่าตอนนั้นตัดสินด้วยกฎใด ด้วยตัวเลขอะไร
  2. ApplicationStatusHistory — จุดเริ่มต้นของเส้นเวลา (M7 ใช้คำนวณ "รอมากี่วัน")
  3. AuditLog — ใครทำ ทำเมื่อใด (M9 + NFR Audit Trail)
เวลาทุกช่องประทับจากฐานข้อมูล ไม่ให้ผู้ใช้กรอกเอง
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatusHistory
from app.models.audit import AuditLog
from app.models.classification import ApplicationClassification
from app.models.enums import ApplicationStatus
from app.models.property import Operator, Property
from app.models.user import User
from app.services import classification as classify_svc

# ปีพุทธศักราชในเลขที่คำขอ — ผู้ใช้ไทยอ่าน "2569" เข้าใจกว่า "2026"
BUDDHIST_OFFSET = 543
APPLICATION_NO_PREFIX = "PKT"


@dataclass(frozen=True)
class PropertyDetails:
    """ข้อมูลที่พักที่ wizard ยังไม่ได้ถาม แต่ต้องมีก่อนเปิดคำขอ

    ชื่อ/ที่อยู่/ลักษณะที่พัก คือช่องในแบบหนังสือแจ้งฯ (A01)
    เก็บที่ property ไม่ใช่ที่ตัวเอกสาร เพราะเป็นคุณสมบัติของที่พัก (3NF)
    """

    name: str
    address: str
    accommodation_kind: str
    accommodation_kind_other: str | None = None
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class NewApplication:
    application: Application
    property_obj: Property
    outcome: classify_svc.Outcome


def get_or_create_operator(db: Session, user: User) -> Operator:
    """ผู้ใช้หนึ่งคนมีโปรไฟล์ผู้ประกอบการเดียว แต่ถือได้หลายที่พัก

    สร้างอัตโนมัติตอนเปิดคำขอใบแรก เพื่อไม่ให้มีขั้นตอน "สร้างโปรไฟล์"
    มาคั่นระหว่างสมัครสมาชิกกับการใช้งานจริง (โจทย์เน้นว่าต้องใช้ง่าย)
    แก้ชื่อที่แสดงและช่องทางติดต่อได้ภายหลัง
    """
    operator = db.scalar(select(Operator).where(Operator.user_id == user.id))
    if operator is not None:
        return operator

    operator = Operator(
        user_id=user.id,
        display_name=user.full_name,
        contact_phone=user.phone,
        contact_email=user.email,
    )
    db.add(operator)
    db.flush()
    return operator


def _next_application_no(db: Session, application: Application) -> str:
    """เลขที่คำขอสำหรับผู้ยื่นใช้อ้างอิง (M6) เช่น PKT-2569-000123

    ใช้ id ของแถวที่เพิ่ง flush เป็นตัวเลขท้าย เพราะฐานข้อมูลรับประกันว่าไม่ซ้ำ
    การนับจำนวนแถวแล้ว +1 จะชนกันทันทีถ้ามีคนกดยื่นพร้อมกันสองคน
    """
    year = datetime.now(UTC).year + BUDDHIST_OFFSET
    return f"{APPLICATION_NO_PREFIX}-{year}-{application.id:06d}"


def start(
    db: Session,
    *,
    user: User,
    answers: classify_svc.Answers,
    local_authority_id: int,
    details: PropertyDetails,
    ip: str | None = None,
) -> tuple[NewApplication | None, str | None]:
    """เปิดคำขอใหม่ในสถานะร่าง — คืน (ผลลัพธ์, ข้อความผิดพลาดสำหรับผู้ใช้)"""

    # จำแนกใหม่ฝั่งเซิร์ฟเวอร์ ไม่รับผลจำแนกจาก client
    outcome = classify_svc.classify(db, answers)
    if outcome is None:
        return None, ("ระบบยังไม่มีเกณฑ์สำหรับที่พักลักษณะนี้ กรุณาติดต่อเจ้าหน้าที่เพื่อตรวจสอบเป็นรายกรณี")

    if outcome.property_type.is_out_of_scope:
        return None, (
            "ที่พักของคุณอยู่นอกขอบเขตของแพลตฟอร์มในระยะนี้ กรุณาติดต่อนายทะเบียนโดยตรง ระบบจึงยังไม่เปิดคำขอให้"
        )

    operator = get_or_create_operator(db, user)

    property_obj = Property(
        operator_id=operator.id,
        local_authority_id=local_authority_id,
        name=details.name,
        address=details.address,
        room_count=answers.rooms,
        max_guests=answers.guests,
        has_restaurant=answers.has_restaurant,
        accommodation_kind=details.accommodation_kind,
        accommodation_kind_other=details.accommodation_kind_other,
        latitude=details.latitude,
        longitude=details.longitude,
    )
    db.add(property_obj)
    db.flush()

    application = Application(
        # ค่าชั่วคราวที่ไม่มีทางซ้ำ — ถูกแทนด้วยเลขจริงทันทีหลัง flush
        # คอลัมน์เป็น NOT NULL + UNIQUE จึงเว้นว่างระหว่างรอ id ไม่ได้
        application_no=f"tmp-{uuid4().hex[:24]}",
        operator_id=operator.id,
        property_id=property_obj.id,
        local_authority_id=local_authority_id,
        status=ApplicationStatus.DRAFT,
    )
    db.add(application)
    db.flush()
    application.application_no = _next_application_no(db, application)

    db.add(
        ApplicationClassification(
            application_id=application.id,
            property_type_id=outcome.property_type.id,
            matched_rule_id=outcome.matched_rule.id if outcome.matched_rule else None,
            answered_rooms=answers.rooms,
            answered_guests=answers.guests,
            answered_has_restaurant=answers.has_restaurant,
            reason_text=outcome.reason,
            classified_at=datetime.now(UTC),
        )
    )

    # from_status = NULL หมายถึง "จุดเริ่มต้น" ไม่ใช่การเปลี่ยนจากสถานะอื่น
    db.add(
        ApplicationStatusHistory(
            application_id=application.id,
            from_status=None,
            to_status=ApplicationStatus.DRAFT,
            changed_by_id=user.id,
            note="เปิดคำขอจากผลประเมินในระบบนำทาง",
        )
    )

    db.add(
        AuditLog(
            actor_id=user.id,
            action="application.create",
            entity_type="application",
            entity_id=application.id,
            to_status=ApplicationStatus.DRAFT,
            outcome="success",
            detail=f"เปิดคำขอ {application.application_no} ({outcome.property_type.name_th})",
            ip_address=ip,
        )
    )

    return NewApplication(application, property_obj, outcome), None


def by_number(db: Session, application_no: str) -> Application | None:
    return db.scalar(select(Application).where(Application.application_no == application_no))


def owned_by(db: Session, user: User) -> list[Application]:
    """คำขอของผู้ใช้คนนี้ ใหม่สุดก่อน — ใช้ทำหน้ารายการคำขอ (M7)"""
    return list(
        db.scalars(
            select(Application)
            .join(Operator, Operator.id == Application.operator_id)
            .where(Operator.user_id == user.id)
            .order_by(Application.created_at.desc())
        ).all()
    )


def is_owner(db: Session, application: Application, user: User) -> bool:
    """ผู้ยื่นต้องเห็นได้เฉพาะคำขอของตัวเอง

    เป็นฝาแฝดของ T-09 ฝั่งผู้ประกอบการ: เจ้าหน้าที่ห้ามข้ามเขต
    ผู้ยื่นก็ห้ามข้ามคำขอของคนอื่น
    """
    owner_id = db.scalar(select(Operator.user_id).where(Operator.id == application.operator_id))
    return owner_id == user.id


def days_waiting(application: Application) -> int:
    """M7: "รออยู่กี่วันแล้ว" — คำนวณตอน query ไม่เก็บค่าไว้ในตาราง"""
    changed = application.status_changed_at
    if changed is None:
        return 0
    now = datetime.now(UTC)
    if changed.tzinfo is None:
        changed = changed.replace(tzinfo=UTC)
    return max((now - changed).days, 0)


def count_by_status(db: Session) -> dict[str, int]:
    """นับคำขอแยกตามสถานะ — เตรียมไว้ให้หน้าภาพรวมส่วนกลาง (M11)"""
    rows = db.execute(select(Application.status, func.count()).group_by(Application.status)).all()
    return {status: count for status, count in rows}
