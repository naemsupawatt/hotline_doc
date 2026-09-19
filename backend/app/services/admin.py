"""US-09 — Super Admin แก้เงื่อนไขและค่าธรรมเนียมโดยไม่ต้องแก้โค้ด

นี่คือส่วนที่พิสูจน์ว่าระบบเป็น config-driven จริง ไม่ใช่แค่เขียนไว้ในเอกสาร

สองอย่างที่แก้ต่างกันโดยพื้นฐาน:

  กฎจำแนกประเภท — แก้แถวเดิมได้เลย เพราะผลจำแนกของคำขอเก่าถูก snapshot
                   ไว้ที่ application_classification แล้ว การแก้กฎจึงไม่ย้อน
                   ไปเปลี่ยนคำขอที่ตัดสินไปแล้ว

  อัตราค่าธรรมเนียม — **ห้าม UPDATE แถวเดิม** ต้องปิด effective_to ของแถวเก่า
                     แล้วเพิ่มแถวใหม่ เพราะใบอนุญาตชี้กลับมาที่ fee_schedule_id
                     ถ้าทับแถวเดิม ใบที่ออกไปแล้วจะอ้างถึงอัตราที่ไม่เคยมีอยู่จริง
                     (ข้อควรคิดข้อ 1 ของโจทย์ข้อ 8)

ทุกการแก้ต้องเขียน AuditLog พร้อมค่าก่อนและหลัง เพราะการเปลี่ยนกฎกระทบคำขอ
ทุกใบที่จะเข้ามาหลังจากนี้ ต้องย้อนได้ว่าใครแก้อะไรเมื่อไร
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.audit import AuditLog
from app.models.classification import ClassificationRule
from app.models.license import FeeSchedule
from app.models.property import Property
from app.models.user import User

# ช่องของกฎที่ Super Admin แก้ได้ — จำกัดไว้ชัดเจน ไม่เปิดให้แก้ทุกคอลัมน์
# เพราะ code กับ property_type_id เป็นตัวผูกกฎเข้ากับประเภท ถ้าแก้ได้จะพังทั้งชุด
EDITABLE_RULE_FIELDS = (
    "priority",
    "min_rooms",
    "max_rooms",
    "min_guests",
    "max_guests",
    "requires_restaurant",
    "reason_template",
    "outcome_message",
    "is_active",
)


@dataclass(frozen=True)
class Change:
    field: str
    before: object
    after: object


def all_rules(db: Session) -> list[ClassificationRule]:
    return list(
        db.scalars(
            select(ClassificationRule)
            .options(selectinload(ClassificationRule.property_type))
            .order_by(ClassificationRule.priority)
        ).all()
    )


def rule_by_code(db: Session, code: str) -> ClassificationRule | None:
    return db.scalar(
        select(ClassificationRule)
        .options(selectinload(ClassificationRule.property_type))
        .where(ClassificationRule.code == code)
    )


def update_rule(
    db: Session,
    *,
    rule: ClassificationRule,
    changes: dict,
    admin: User,
    ip: str | None = None,
) -> tuple[list[Change], str | None]:
    """แก้กฎจำแนกประเภท คืน (รายการที่เปลี่ยน, ข้อความผิดพลาด)"""
    applied: list[Change] = []

    for field, after in changes.items():
        if field not in EDITABLE_RULE_FIELDS:
            return [], f"ช่อง {field} ไม่อนุญาตให้แก้ไข"
        before = getattr(rule, field)
        if before == after:
            continue
        setattr(rule, field, after)
        applied.append(Change(field, before, after))

    if not applied:
        return [], None

    problem = _validate_rule(rule)
    if problem:
        db.rollback()
        return [], problem

    summary = ", ".join(f"{c.field}: {c.before} -> {c.after}" for c in applied)
    db.add(
        AuditLog(
            actor_id=admin.id,
            action="admin.rule_update",
            entity_type="classification_rule",
            entity_id=rule.id,
            outcome="success",
            detail=f"แก้กฎ {rule.code} ({summary})",
            ip_address=ip,
        )
    )
    return applied, None


def _validate_rule(rule: ClassificationRule) -> str | None:
    """กันค่าที่ทำให้กฎไม่มีทางเข้าเงื่อนไขได้เลย

    ถ้าปล่อยผ่าน ระบบจะตอบผู้ใช้ว่า "ไม่มีเกณฑ์สำหรับที่พักลักษณะนี้"
    โดยที่ผู้ดูแลระบบไม่รู้ตัวว่าตัวเองทำพัง
    """
    if rule.min_rooms is not None and rule.max_rooms is not None:
        if rule.min_rooms > rule.max_rooms:
            return "จำนวนห้องขั้นต่ำต้องไม่มากกว่าขั้นสูง"
    if rule.min_guests is not None and rule.max_guests is not None:
        if rule.min_guests > rule.max_guests:
            return "จำนวนผู้เข้าพักขั้นต่ำต้องไม่มากกว่าขั้นสูง"
    for field in ("min_rooms", "max_rooms", "min_guests", "max_guests"):
        value = getattr(rule, field)
        if value is not None and value < 0:
            return "จำนวนห้องและจำนวนผู้เข้าพักต้องไม่ติดลบ"
    if not rule.reason_template.strip() or not rule.outcome_message.strip():
        return "ข้อความเหตุผลและข้อความผลลัพธ์ต้องไม่ว่าง"
    return None


def active_fees(db: Session) -> list[FeeSchedule]:
    """อัตราทั้งหมดรวมที่ปิดไปแล้ว เรียงใหม่สุดก่อน — ให้เห็นประวัติการแก้"""
    return list(
        db.scalars(
            select(FeeSchedule).order_by(
                FeeSchedule.property_type_id, FeeSchedule.effective_from.desc()
            )
        ).all()
    )


def supersede_fee(
    db: Session,
    *,
    current: FeeSchedule,
    amount: float,
    validity_years: int,
    effective_from: date,
    note: str | None,
    admin: User,
    ip: str | None = None,
) -> tuple[FeeSchedule | None, str | None]:
    """เปลี่ยนอัตราค่าธรรมเนียมด้วยการเพิ่มแถวใหม่ ไม่ทับแถวเดิม"""
    if amount < 0:
        return None, "ค่าธรรมเนียมต้องไม่ติดลบ"
    if validity_years < 1:
        return None, "ระยะเวลาของใบอนุญาตต้องอย่างน้อย 1 ปี"
    if effective_from <= current.effective_from:
        return None, "วันที่เริ่มมีผลของอัตราใหม่ต้องหลังอัตราเดิม"

    # ปิดอัตราเดิมหนึ่งวันก่อนอัตราใหม่เริ่ม เพื่อไม่ให้ช่วงเวลาซ้อนกัน
    current.effective_to = date.fromordinal(effective_from.toordinal() - 1)

    replacement = FeeSchedule(
        property_type_id=current.property_type_id,
        amount=amount,
        currency=current.currency,
        validity_years=validity_years,
        effective_from=effective_from,
        note=note,
    )
    db.add(replacement)
    db.flush()

    db.add(
        AuditLog(
            actor_id=admin.id,
            action="admin.fee_supersede",
            entity_type="fee_schedule",
            entity_id=replacement.id,
            outcome="success",
            detail=(
                f"เปลี่ยนอัตราค่าธรรมเนียมจาก {current.amount} เป็น {amount} "
                f"มีผล {effective_from} (อัตราเดิมปิดที่ {current.effective_to})"
            ),
            ip_address=ip,
        )
    )
    return replacement, None


def preview(db: Session, rooms: int, guests: int, has_restaurant: bool) -> dict:
    """ลองจำแนกด้วยกฎปัจจุบันโดยไม่บันทึกอะไร

    มีไว้ให้ผู้ดูแลระบบกดทดสอบทันทีหลังแก้กฎ จะได้เห็นผลก่อนของจริงเข้ามา
    """
    from app.services import classification as classify_svc

    outcome = classify_svc.classify(db, classify_svc.Answers(rooms, guests, has_restaurant))
    if outcome is None:
        return {"matched": False, "property_type_name": None, "reason": None, "rule_code": None}
    return {
        "matched": True,
        "property_type_name": outcome.property_type.name_th,
        "reason": outcome.reason,
        "rule_code": outcome.matched_rule.code if outcome.matched_rule else None,
    }


def counts_using_rule(db: Session, property_type_id: int) -> int:
    """จำนวนที่พักที่ถูกจำแนกเป็นประเภทนี้ไปแล้ว — เตือนก่อนแก้กฎที่มีผลกระทบ"""
    from app.models.classification import ApplicationClassification

    return len(
        list(
            db.scalars(
                select(ApplicationClassification.id).where(
                    ApplicationClassification.property_type_id == property_type_id
                )
            ).all()
        )
    )


def property_count(db: Session) -> int:
    return len(list(db.scalars(select(Property.id)).all()))
