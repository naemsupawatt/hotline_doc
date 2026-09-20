"""M2/M3/M4 — จำแนกประเภทที่พัก และประกอบรายการเอกสารที่ต้องใช้

หลักการเดียวที่ต้องจำ: **ไม่มีตัวเลขของกฎอยู่ในไฟล์นี้เลย**
ทุกเงื่อนไข อัตราค่าธรรมเนียม และรายการเอกสาร อ่านจากฐานข้อมูลทั้งหมด
ไฟล์นี้มีแต่ "วิธีเทียบ" — ซึ่งคือสิ่งที่ทำให้ US-09 เป็นจริง
Super Admin แก้กฎในตารางแล้วผลลัพธ์เปลี่ยนทันทีโดยไม่ต้องแตะโค้ด

การจำแนก: เรียงกฎตาม priority น้อย→มาก เอากฎแรกที่เงื่อนไขครบทุกข้อ
เหตุผลที่ต้องพึ่งลำดับ ไม่ใช่ใส่ min_rooms ให้ครบ อ่านหัวข้อกับดัก T-02
ใน models/classification.py ก่อนแก้อะไรในนี้
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.authority import ContactPoint, LocalAuthority
from app.models.classification import ClassificationRule, PropertyType
from app.models.document import DocumentRequirement, DocumentType
from app.models.enums import DocumentCategory
from app.models.license import FeeSchedule


@dataclass(frozen=True)
class Answers:
    """คำตอบจาก wizard — สามข้อนี้คือทุกอย่างที่ตารางข้อ 4 ใช้ตัดสิน"""

    rooms: int
    guests: int
    has_restaurant: bool


@dataclass(frozen=True)
class Fee:
    amount: float
    currency: str
    validity_years: int


@dataclass(frozen=True)
class Outcome:
    property_type: PropertyType
    matched_rule: ClassificationRule | None
    reason: str
    outcome_message: str
    fee: Fee | None


def active_rules(db: Session, on: date | None = None) -> list[ClassificationRule]:
    """กฎที่ "มีผลอยู่" ณ วันที่กำหนด เรียงตามลำดับการตัดสิน

    กรองด้วยช่วงเวลาด้วย ไม่ใช่แค่ is_active เพราะโจทย์ข้อ 8 กำหนดว่า
    กฎเก่าต้องไม่ถูกลบทิ้ง ต้องยังย้อนดูได้ว่าเมื่อก่อนตัดสินด้วยอะไร
    """
    today = on or date.today()
    return list(
        db.scalars(
            select(ClassificationRule)
            .options(selectinload(ClassificationRule.property_type))
            .where(
                ClassificationRule.is_active,
                ClassificationRule.effective_from <= today,
                or_(
                    ClassificationRule.effective_to.is_(None),
                    ClassificationRule.effective_to >= today,
                ),
            )
            .order_by(ClassificationRule.priority)
        ).all()
    )


def current_fee(db: Session, property_type_id: int, on: date | None = None) -> Fee | None:
    """อัตราที่มีผลอยู่ของประเภทนั้น — ประเภทที่ไม่ต้องขอใบอนุญาตจะไม่มี"""
    today = on or date.today()
    row = db.scalar(
        select(FeeSchedule)
        .where(
            FeeSchedule.property_type_id == property_type_id,
            FeeSchedule.is_active,
            FeeSchedule.effective_from <= today,
            or_(FeeSchedule.effective_to.is_(None), FeeSchedule.effective_to >= today),
        )
        .order_by(FeeSchedule.effective_from.desc())
    )
    if row is None:
        return None
    return Fee(amount=float(row.amount), currency=row.currency, validity_years=row.validity_years)


def fee_row(db: Session, property_type_id: int, on: date | None = None) -> FeeSchedule | None:
    """แถวอัตราค่าธรรมเนียมที่มีผล — ใบอนุญาตต้องชี้กลับมาที่แถวนี้ได้ (โจทย์ข้อ 8)"""
    today = on or date.today()
    return db.scalar(
        select(FeeSchedule)
        .where(
            FeeSchedule.property_type_id == property_type_id,
            FeeSchedule.is_active,
            FeeSchedule.effective_from <= today,
            or_(FeeSchedule.effective_to.is_(None), FeeSchedule.effective_to >= today),
        )
        .order_by(FeeSchedule.effective_from.desc())
    )


def render_reason(rule: ClassificationRule, answers: Answers) -> str:
    """เติมตัวเลขที่ผู้ใช้ตอบลงใน reason_template

    M2 บังคับให้ "แสดงผลสรุปพร้อมเหตุผลว่าทำไมจึงได้ผลนั้น"
    ข้อความมาจาก DB ทั้งประโยค โค้ดแค่เติมค่าลงช่องว่าง

    ใช้ format_map กับ dict ที่คืนค่าว่างเมื่อไม่รู้จัก placeholder
    เพราะข้อความนี้ Super Admin แก้เองได้ ถ้าเผลอพิมพ์ {typo} เข้าไป
    ระบบต้องไม่ล่มกลางการสาธิต แค่แสดงข้อความนั้นโดยเว้นช่องไว้
    """

    class _Safe(dict):
        def __missing__(self, key: str) -> str:
            return ""

    return rule.reason_template.format_map(
        _Safe(
            rooms=answers.rooms,
            guests=answers.guests,
            restaurant="มีห้องอาหาร" if answers.has_restaurant else "ไม่มีห้องอาหาร",
        )
    )


def classify(db: Session, answers: Answers, on: date | None = None) -> Outcome | None:
    """จำแนกประเภทจากคำตอบ — คืน None เมื่อไม่มีกฎใดรับกรณีนี้

    ไม่บันทึกอะไรลงฐานข้อมูล เป็นการคำนวณล้วน
    เพราะ US-01 คือ "ตอบคำถามไม่กี่ข้อแล้วรู้ว่าต้องขอใบอนุญาตหรือไม่"
    คนที่แค่มาเช็กยังไม่ยื่น จึงไม่ควรสร้างคำขอค้างไว้ในระบบ
    ผลจะถูกบันทึกเป็น snapshot ตอนกดเริ่มยื่นคำขอ (ApplicationClassification)
    """
    rule = next((r for r in active_rules(db, on) if r.matches(*_as_tuple(answers))), None)
    if rule is None:
        return None

    ptype = rule.property_type
    return Outcome(
        property_type=ptype,
        matched_rule=rule,
        reason=render_reason(rule, answers),
        outcome_message=rule.outcome_message,
        # ประเภทที่ไม่ต้องขอใบอนุญาตไม่ต้องคิดค่าธรรมเนียม
        fee=current_fee(db, ptype.id, on) if ptype.requires_license else None,
    )


def _as_tuple(a: Answers) -> tuple[int, int, bool]:
    return a.rooms, a.guests, a.has_restaurant


# ---------------------------------------------------------------------------
# M3 / M4 — รายการเอกสารของประเภทนั้น
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RequiredDocument:
    requirement: DocumentRequirement
    document_type: DocumentType
    # จุดติดต่อของ อปท. ที่ผู้ใช้เลือก — มีเฉพาะเอกสารหมวดที่ต้องขอจากหน่วยงานอื่น
    contact_point: ContactPoint | None


def required_documents(
    db: Session, property_type_id: int, local_authority_id: int | None = None
) -> list[RequiredDocument]:
    """รายการเอกสารของประเภทที่พัก พร้อมจุดติดต่อตาม อปท. ที่ผู้ใช้อยู่

    M3: ผู้เรียกเอาไปแยก 2 หมวดด้วย document_type.category
    M4: หมวด external ต้องได้ contact_point ของ อปท. นั้นติดมาด้วย
        ถ้าไม่ส่ง local_authority_id มา จะไม่มีจุดติดต่อ — หน้าจอต้องบอกผู้ใช้
        ให้เลือกท้องถิ่นก่อน ไม่ใช่แสดงที่อยู่ของเขตอื่นมั่ว ๆ
    """
    requirements = db.scalars(
        select(DocumentRequirement)
        .options(
            selectinload(DocumentRequirement.document_type).selectinload(
                DocumentType.issuing_agency
            ),
            selectinload(DocumentRequirement.document_type).selectinload(DocumentType.parent),
        )
        .join(DocumentType)
        .where(
            DocumentRequirement.property_type_id == property_type_id,
            DocumentType.is_active,
        )
        .order_by(DocumentRequirement.display_order)
    ).all()

    contacts = _contacts_for(db, local_authority_id)

    return [
        RequiredDocument(
            requirement=r,
            document_type=r.document_type,
            contact_point=contacts.get(r.document_type.issuing_agency_id),
        )
        for r in requirements
    ]


def _contacts_for(db: Session, local_authority_id: int | None) -> dict[int, ContactPoint]:
    """จุดติดต่อในเขตนั้น เก็บเป็น dict ตาม agency เพื่อไม่ query ซ้ำรายเอกสาร"""
    if local_authority_id is None:
        return {}
    rows = db.scalars(
        select(ContactPoint)
        .options(selectinload(ContactPoint.local_authority))
        .where(ContactPoint.local_authority_id == local_authority_id)
    ).all()
    return {c.issuing_agency_id: c for c in rows}


def local_authorities(db: Session) -> list[LocalAuthority]:
    """อปท. ทั้งหมดสำหรับให้ wizard แสดงเป็นตัวเลือก (ข้อ 4: ต้องอ่านจาก DB)"""
    return list(
        db.scalars(
            select(LocalAuthority).where(LocalAuthority.is_active).order_by(LocalAuthority.id)
        ).all()
    )


def property_type_by_code(db: Session, code: str) -> PropertyType | None:
    return db.scalar(select(PropertyType).where(PropertyType.code == code))


def category_of(doc: DocumentType) -> DocumentCategory:
    return DocumentCategory(doc.category)
