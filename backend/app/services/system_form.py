"""แบบฟอร์มที่ระบบกรอกให้ (is_system_form) — เนื้อหาสำหรับหน้าพิมพ์ + ลายมือชื่อ

ตอนนี้มีสองฉบับ ใช้กลไกเดียวกันทั้งคู่ ต่างกันแค่การจัดหน้ากระดาษฝั่งหน้าเว็บ:
  A01 แบบหนังสือแจ้งสถานที่พักที่ไม่เป็นโรงแรม — เส้น "ไม่เข้าข่ายโรงแรม"
  A06 แบบ ร.ร.1 คำขอรับใบอนุญาตประกอบธุรกิจโรงแรม — ประเภทที่ 1 และ 2

ทั้งสองฉบับต่างจากเอกสารอื่นตรงที่ผู้ยื่นไม่ได้ไปหาไฟล์มาจากที่ไหน ระบบประกอบ
เนื้อหาให้เองจากข้อมูลที่กรอกไปแล้ว เหลือสิ่งเดียวที่ระบบทำแทนไม่ได้คือ
**ลายมือชื่อผู้ยื่น** ซึ่งเป็นสิ่งที่ทำให้เอกสารฉบับนั้นมีผล จึงบังคับต้องมีก่อนยื่น (M6)

ลายมือชื่อเก็บเป็นไฟล์แนบของแบบฟอร์มนั้นเอง ไม่ใช่คอลัมน์ใหม่ใน application
เพราะทำแบบนี้แล้วได้ทั้งการเก็บเป็นรุ่น (เซ็นใหม่ = รุ่นถัดไป ไม่ทับของเดิม)
การตรวจของเจ้าหน้าที่ และหน้าเปิดไฟล์เดิม โดยไม่ต้องเขียนกลไกใหม่เลยสักชิ้น

ส่วนตัวกระดาษ ระบบไม่ได้สร้างเป็นไฟล์ PDF ฝั่งเซิร์ฟเวอร์ แต่ให้หน้าเว็บ
พิมพ์ผ่านเบราว์เซอร์แล้วเลือก "บันทึกเป็น PDF" เหตุผลเดียวกับใบอนุญาต (M10)
คือเลี่ยง dependency และปัญหาฟอนต์ไทยในไลบรารี PDF ซึ่งพังบ่อยและกินเวลา
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.application import Application
from app.models.document import DocumentFile, DocumentRequirement, DocumentType
from app.models.property import Operator
from app.models.user import User
from app.services import document as doc_svc

# รหัสของแบบฟอร์มที่มีหน้ากระดาษให้ดูในระบบ — ตัวเอกสารเองยังอ่านจากฐานข้อมูล
# ทั้งชื่อ ชนิดไฟล์ที่รับ และว่าบังคับหรือไม่ (US-09) ค่าคงที่นี้เป็นแค่ "กุญแจ" ที่ใช้หาแถว
NOTICE_FORM_CODE = "A01"  # หนังสือแจ้งสถานที่พักที่ไม่เป็นโรงแรม
HOTEL_FORM_CODE = "A06"  # แบบ ร.ร.1


@dataclass(frozen=True)
class Attachment:
    """ช่องแนบที่อยู่ "ในแบบฟอร์ม" ฉบับนั้น เช่น A07–A09 ที่อยู่ในแบบ ร.ร.1

    หน้ากระดาษติ๊กให้อัตโนมัติจากว่าแนบไฟล์แล้วหรือยัง ไม่ได้เก็บช่องติ๊ก
    ไว้อีกคอลัมน์ เพราะนั่นคือข้อมูลชุดเดียวกันที่เก็บซ้ำสองที่ (3NF)
    """

    code: str
    name_th: str
    is_mandatory: bool
    is_attached: bool


@dataclass(frozen=True)
class SystemForm:
    document_type: DocumentType
    operator: Operator
    applicant: User
    signature: DocumentFile | None
    attachments: list[Attachment]


def build(
    db: Session, application: Application, property_type_id: int, code: str
) -> SystemForm | None:
    """ข้อมูลทั้งหมดของแบบฟอร์มหนึ่งใบ หรือ None ถ้าที่พักประเภทนี้ไม่ได้ใช้แบบนี้

    เช็กผ่านตาราง requirement เสมอ ไม่ใช่เช็กแค่ว่ามีเอกสารรหัสนี้อยู่ในระบบ
    ไม่งั้นคำขอที่ไม่เข้าข่ายโรงแรมจะเปิดแบบ ร.ร.1 ได้ ทั้งที่ไม่ได้ใช้
    """
    requirement = doc_svc.requirement_for(db, property_type_id, code)
    if requirement is None or not requirement.document_type.is_system_form:
        return None

    operator = db.get(Operator, application.operator_id)
    applicant = db.get(User, operator.user_id) if operator else None
    if operator is None or applicant is None:  # pragma: no cover - คำขอต้องมีเจ้าของเสมอ
        return None

    doc = requirement.document_type
    return SystemForm(
        document_type=doc,
        operator=operator,
        applicant=applicant,
        signature=current_signature(db, application, doc.id),
        attachments=_attachments(db, application, property_type_id, doc.id),
    )


def current_signature(
    db: Session, application: Application, document_type_id: int
) -> DocumentFile | None:
    """รูปลายมือชื่อรุ่นล่าสุด — รุ่นเก่ายังอยู่ในตารางแต่ is_current เป็น false"""
    return db.scalar(
        select(DocumentFile).where(
            DocumentFile.application_id == application.id,
            DocumentFile.document_type_id == document_type_id,
            DocumentFile.is_current,
        )
    )


def _attachments(
    db: Session, application: Application, property_type_id: int, parent_id: int
) -> list[Attachment]:
    """ช่องแนบที่ประกาศว่าเป็นลูกของแบบฟอร์มฉบับนี้ เรียงตามลำดับที่ตั้งไว้"""
    requirements = db.scalars(
        select(DocumentRequirement)
        .options(selectinload(DocumentRequirement.document_type))
        .join(DocumentType)
        .where(
            DocumentRequirement.property_type_id == property_type_id,
            DocumentType.parent_id == parent_id,
            DocumentType.is_active,
        )
        .order_by(DocumentRequirement.display_order)
    ).all()

    attached_type_ids = {row.document_type_id for row in doc_svc.current_files(db, application.id)}

    return [
        Attachment(
            code=r.document_type.code,
            name_th=r.document_type.name_th,
            is_mandatory=r.is_mandatory,
            is_attached=r.document_type_id in attached_type_ids,
        )
        for r in requirements
    ]
