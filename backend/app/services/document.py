"""M5/M6 — อัปโหลดเอกสาร เก็บเป็นรุ่น และตรวจความครบก่อนยื่น

ข้อ 8 ของโจทย์ถามตรง ๆ ว่า "อัปโหลดฉบับเดิมซ้ำเพื่อแก้ไข ควรทับไฟล์เดิม
หรือเก็บเป็นรุ่นใหม่" -> ระบบนี้เก็บเป็นรุ่นใหม่ทุกครั้ง เพราะไฟล์ที่เจ้าหน้าที่
เคยตรวจต้องย้อนดูได้ และ DocumentReview ชี้ไปยัง document_file_id ตรง ๆ
ถ้าทับไฟล์เดิม ผลตรวจจะชี้ไปยังไฟล์ที่ไม่มีอยู่แล้ว

คำสองคำที่ห้ามสับสน:
  slot    = "คนละไฟล์" เช่น ภาพถ่ายอาคารมุมที่ 1 กับมุมที่ 2
  version = "ไฟล์เดิมส่งใหม่" เช่น ถ่ายใหม่เพราะเจ้าหน้าที่บอกว่าเบลอ
"""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.application import Application
from app.models.document import DocumentFile, DocumentRequirement, DocumentType
from app.models.enums import DocumentStatus
from app.models.user import User

# นามสกุลไฟล์ตาม MIME — ใช้ตั้งชื่อไฟล์ที่เก็บ ไม่ได้ใช้ตรวจความถูกต้อง
EXTENSION = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


@dataclass(frozen=True)
class UploadResult:
    file: DocumentFile
    document_type: DocumentType


def storage_root() -> Path:
    return Path(settings.STORAGE_DIR)


def max_upload_bytes() -> int:
    return settings.MAX_UPLOAD_MB * 1024 * 1024


def requirement_for(db: Session, property_type_id: int, code: str) -> DocumentRequirement | None:
    """ข้อกำหนดของเอกสารรหัสนี้ สำหรับที่พักประเภทนี้

    ต้องเช็กผ่านตาราง requirement ไม่ใช่เช็กแค่ว่ามี document_type รหัสนี้อยู่
    ไม่งั้นผู้ใช้จะอัปโหลดเอกสารที่ไม่เกี่ยวกับประเภทที่พักของตนเข้ามาได้
    """
    return db.scalar(
        select(DocumentRequirement)
        .options(selectinload(DocumentRequirement.document_type))
        .join(DocumentType)
        .where(
            DocumentRequirement.property_type_id == property_type_id,
            DocumentType.code == code,
            DocumentType.is_active,
        )
    )


def current_files(db: Session, application_id: int) -> list[DocumentFile]:
    """ไฟล์รุ่นล่าสุดของทุก slot ในคำขอนี้"""
    return list(
        db.scalars(
            select(DocumentFile)
            .options(selectinload(DocumentFile.document_type))
            .where(
                DocumentFile.application_id == application_id,
                DocumentFile.is_current,
            )
            .order_by(DocumentFile.document_type_id, DocumentFile.slot_no)
        ).all()
    )


def _next_slot(db: Session, application_id: int, document_type_id: int) -> int:
    highest = db.scalar(
        select(func.max(DocumentFile.slot_no)).where(
            DocumentFile.application_id == application_id,
            DocumentFile.document_type_id == document_type_id,
        )
    )
    return (highest or 0) + 1


def _next_version(db: Session, application_id: int, document_type_id: int, slot_no: int) -> int:
    highest = db.scalar(
        select(func.max(DocumentFile.version_no)).where(
            DocumentFile.application_id == application_id,
            DocumentFile.document_type_id == document_type_id,
            DocumentFile.slot_no == slot_no,
        )
    )
    return (highest or 0) + 1


def validate(doc: DocumentType, *, content_type: str, size: int) -> str | None:
    """คืนข้อความผิดพลาดสำหรับผู้ใช้ทั่วไป หรือ None เมื่อผ่าน (M5)

    ชนิดไฟล์ที่ยอมรับอ่านจากฐานข้อมูล ไม่ได้ hard-code ไว้ในโค้ด
    Super Admin จึงแก้ได้เองเมื่อระเบียบเปลี่ยน (US-09)
    """
    if doc.is_system_form:
        return f"{doc.name_th} เป็นแบบฟอร์มที่กรอกในระบบ ไม่ต้องอัปโหลดไฟล์"

    allowed = doc.accepted_mime_list
    if content_type not in allowed:
        return f"{doc.name_th} รับเฉพาะ{_describe(allowed)} กรุณาเลือกไฟล์ใหม่"

    if size <= 0:
        return "ไฟล์ที่เลือกว่างเปล่า กรุณาเลือกไฟล์ใหม่"

    if size > max_upload_bytes():
        return f"ไฟล์ใหญ่เกิน {settings.MAX_UPLOAD_MB} MB กรุณาย่อขนาดไฟล์หรือถ่ายรูปใหม่ด้วยความละเอียดที่ต่ำลง"

    return None


def _describe(mimes: list[str]) -> str:
    """แปลง MIME เป็นคำที่ผู้ใช้เข้าใจ — NFR Usability ห้ามโชว์ application/pdf ดิบ"""
    has_pdf = "application/pdf" in mimes
    has_image = any(m.startswith("image/") for m in mimes)
    if has_pdf and has_image:
        return "ไฟล์ PDF หรือรูปถ่าย"
    if has_pdf:
        return "ไฟล์ PDF"
    if has_image:
        return "รูปถ่าย JPG หรือ PNG"
    return ", ".join(mimes)


def save_upload(
    db: Session,
    *,
    application: Application,
    doc: DocumentType,
    user: User,
    original_name: str,
    content_type: str,
    data: bytes,
    slot_no: int | None = None,
) -> UploadResult:
    """บันทึกไฟล์ลงดิสก์และสร้างแถวรุ่นใหม่

    slot_no = None หมายถึง "แนบไฟล์ใหม่":
      - เอกสารที่แนบได้ไฟล์เดียว -> ใช้ slot 1 เสมอ การอัปซ้ำจึงเป็น version ใหม่
      - เอกสารที่แนบได้หลายไฟล์ -> เปิด slot ถัดไป
    ส่ง slot_no มาด้วยเมื่อผู้ใช้ตั้งใจ "แทนที่ไฟล์เดิมของ slot นั้น"
    """
    if slot_no is None:
        slot_no = _next_slot(db, application.id, doc.id) if doc.allows_multiple else 1

    version_no = _next_version(db, application.id, doc.id, slot_no)

    # ชื่อไฟล์บนดิสก์ไม่ใช้ชื่อที่ผู้ใช้ส่งมา เพื่อกัน path traversal และชื่อซ้ำ
    # ชื่อจริงเก็บไว้ในคอลัมน์ original_name สำหรับแสดงผล
    folder = storage_root() / application.application_no / doc.code
    folder.mkdir(parents=True, exist_ok=True)
    stored = folder / f"{uuid4().hex}{EXTENSION.get(content_type, '')}"
    stored.write_bytes(data)

    # รุ่นเก่าของ slot เดียวกันเลิกเป็นรุ่นปัจจุบัน แต่ไม่ถูกลบ
    for old in db.scalars(
        select(DocumentFile).where(
            DocumentFile.application_id == application.id,
            DocumentFile.document_type_id == doc.id,
            DocumentFile.slot_no == slot_no,
            DocumentFile.is_current,
        )
    ).all():
        old.is_current = False

    record = DocumentFile(
        application_id=application.id,
        document_type_id=doc.id,
        slot_no=slot_no,
        version_no=version_no,
        is_current=True,
        stored_path=str(stored.relative_to(storage_root())),
        original_name=original_name[:255],
        mime_type=content_type,
        size_bytes=len(data),
        status=DocumentStatus.UPLOADED,
        uploaded_by_id=user.id,
    )
    db.add(record)
    db.flush()
    return UploadResult(record, doc)


# ---------------------------------------------------------------------------
# M6 — ตรวจความครบก่อนยื่น
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Missing:
    code: str
    name_th: str


def missing_mandatory(
    db: Session, application: Application, property_type_id: int
) -> list[Missing]:
    """เอกสารบังคับที่ยังขาด — T-06 บังคับให้ "ระบุชัดว่าขาดฉบับใดบ้าง"

    เอกสารที่เป็นแบบฟอร์มในระบบ (is_system_form) ถือว่าครบตั้งแต่เปิดคำขอ
    เพราะข้อมูลที่แบบฟอร์มนั้นใช้ถูกกรอกครบไปแล้วตอนเปิดคำขอ
    ไม่มีไฟล์ให้ผู้ใช้อัปโหลด จึงไม่ควรเอามาบล็อกการยื่น
    """
    uploaded_type_ids = {row.document_type_id for row in current_files(db, application.id)}

    requirements = db.scalars(
        select(DocumentRequirement)
        .options(selectinload(DocumentRequirement.document_type))
        .join(DocumentType)
        .where(
            DocumentRequirement.property_type_id == property_type_id,
            DocumentRequirement.is_mandatory,
            DocumentType.is_active,
        )
        .order_by(DocumentType.display_order)
    ).all()

    return [
        Missing(r.document_type.code, r.document_type.name_th)
        for r in requirements
        if not r.document_type.is_system_form and r.document_type_id not in uploaded_type_ids
    ]
