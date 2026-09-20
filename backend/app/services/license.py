"""M10 — ออกเอกสารสิทธิ์อิเล็กทรอนิกส์ที่พิมพ์ได้ พร้อมเลขอ้างอิง

ออกได้สองแบบตามผลจำแนกประเภท (ดู models/license.py):
  license        — ที่พักแรมประเภท 1/2 มีค่าธรรมเนียมและอายุตามอัตราที่มีผลตอนนั้น
  notice_receipt — ที่พักที่ไม่เข้าข่ายโรงแรม ไม่มีค่าธรรมเนียมและไม่มีวันหมดอายุ

หัวใจของไฟล์นี้คือ **snapshot ค่าธรรมเนียม** ตามข้อควรคิดข้อ 1 ของโจทย์ข้อ 8:
เก็บทั้ง fee_schedule_id และคัดลอก fee_amount มาไว้ในแถวใบอนุญาตเลย
ถ้าเก็บแค่ FK แล้ววันหนึ่ง Super Admin แก้อัตรา ใบอนุญาตที่ออกไปแล้วจะเปลี่ยนตาม
ซึ่งผิด เพราะใบอนุญาตคือหลักฐานว่าเก็บเงินไปเท่าไรตอนนั้น
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationStatusHistory
from app.models.audit import AuditLog
from app.models.classification import PropertyType
from app.models.enums import ApplicationStatus, LicenseKind
from app.models.license import License
from app.models.user import User
from app.services import classification as classify_svc
from app.services import document as doc_svc

BUDDHIST_OFFSET = 543
LICENSE_PREFIX = "HL"  # ใบอนุญาต
RECEIPT_PREFIX = "NR"  # หนังสือรับรองการแจ้ง


@dataclass(frozen=True)
class Issued:
    license: License
    property_type: PropertyType


def existing(db: Session, application_id: int) -> License | None:
    return db.scalar(select(License).where(License.application_id == application_id))


def _reference_no(kind: LicenseKind, row_id: int) -> str:
    """เลขอ้างอิงสำหรับตรวจสอบย้อนกลับ (M10) เช่น HL-2569-000042

    ใช้ id ของแถวที่เพิ่ง flush เหมือนเลขที่คำขอ เพราะฐานข้อมูลรับประกันว่าไม่ซ้ำ
    """
    prefix = LICENSE_PREFIX if kind is LicenseKind.LICENSE else RECEIPT_PREFIX
    year = datetime.now(UTC).year + BUDDHIST_OFFSET
    return f"{prefix}-{year}-{row_id:06d}"


def signature_dir() -> Path:
    """เก็บแยกจากโฟลเดอร์ของคำขอ เพราะเป็นไฟล์ของเอกสารที่ระบบออก ไม่ใช่ไฟล์ที่ผู้ยื่นส่งมา"""
    return doc_svc.storage_root() / "licenses"


def signature_path(row: License) -> Path | None:
    if not row.issuer_signature_path:
        return None
    return doc_svc.storage_root() / row.issuer_signature_path


def issue(
    db: Session,
    *,
    application: Application,
    officer: User,
    property_type: PropertyType,
    signature_png: bytes,
    ip: str | None = None,
) -> tuple[Issued | None, str | None]:
    """ออกเอกสารสิทธิ์ให้คำขอที่อนุมัติแล้ว พร้อมลายมือชื่อผู้ลงนาม

    ลายมือชื่อเป็นส่วนหนึ่งของการออกเอกสาร ไม่ใช่ขั้นตอนแยก เพราะเอกสารที่ยัง
    ไม่มีใครลงนามคือเอกสารที่ใช้ไม่ได้ — กติกาเดียวกับที่ผู้ยื่นต้องลงลายมือชื่อ
    ในแบบฟอร์มก่อนยื่น (M6)
    """
    # ตรวจ "ออกไปแล้วหรือยัง" ก่อนตรวจสถานะเสมอ
    # เพราะพอออกเอกสารแล้วสถานะจะกลายเป็น license_issued ถ้าเรียงกลับกัน
    # การกดซ้ำจะได้ข้อความว่า "ยังไม่อนุมัติ" ซึ่งไม่ใช่เหตุผลจริงและชวนงง
    if existing(db, application.id) is not None:
        return None, "คำขอนี้ออกเอกสารไปแล้ว ไม่ต้องออกซ้ำ"

    if application.status != ApplicationStatus.APPROVED:
        return None, "ออกเอกสารได้เฉพาะคำขอที่อนุมัติแล้วเท่านั้น"

    kind = LicenseKind.LICENSE if property_type.requires_license else LicenseKind.NOTICE_RECEIPT
    today = date.today()

    fee = classify_svc.current_fee(db, property_type.id) if kind is LicenseKind.LICENSE else None
    if kind is LicenseKind.LICENSE and fee is None:
        return None, "ยังไม่มีอัตราค่าธรรมเนียมที่มีผลสำหรับประเภทนี้ กรุณาติดต่อผู้ดูแลระบบ"

    fee_row = None
    valid_until = None
    if fee is not None:
        fee_row = classify_svc.fee_row(db, property_type.id)
        valid_until = today.replace(year=today.year + fee.validity_years)

    row = License(
        application_id=application.id,
        license_no="",  # แทนที่ด้วยเลขจริงทันทีหลัง flush
        kind=kind,
        property_type_id=property_type.id,
        issued_by_id=officer.id,
        local_authority_id=application.local_authority_id,
        fee_schedule_id=fee_row.id if fee_row else None,
        fee_amount=fee.amount if fee else None,
        issued_at=datetime.now(UTC),
        valid_from=today,
        valid_until=valid_until,
    )
    db.add(row)
    db.flush()
    row.license_no = _reference_no(kind, row.id)

    # ตั้งชื่อไฟล์ด้วยเลขเอกสารซึ่งไม่ซ้ำอยู่แล้ว จึงไม่ต้องสุ่มชื่อเหมือนไฟล์ที่ผู้ใช้อัปโหลด
    # (ชื่อไฟล์ที่ผู้ใช้ตั้งเองเป็นช่องทาง path traversal ส่วนเลขนี้ระบบเป็นคนออก)
    folder = signature_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{row.license_no}.png").write_bytes(signature_png)
    row.issuer_signature_path = f"licenses/{row.license_no}.png"

    previous = application.status
    application.status = ApplicationStatus.LICENSE_ISSUED
    application.status_changed_at = func.now()

    label = "ใบอนุญาต" if kind is LicenseKind.LICENSE else "หนังสือรับรองการแจ้ง"
    db.add(
        ApplicationStatusHistory(
            application_id=application.id,
            from_status=previous,
            to_status=ApplicationStatus.LICENSE_ISSUED,
            changed_by_id=officer.id,
            note=f"ออก{label}เลขที่ {row.license_no}",
        )
    )
    db.add(
        AuditLog(
            actor_id=officer.id,
            action="license.issue",
            entity_type="license",
            entity_id=row.id,
            from_status=previous,
            to_status=ApplicationStatus.LICENSE_ISSUED,
            outcome="success",
            detail=f"ออก{label} {row.license_no} ให้คำขอ {application.application_no}",
            ip_address=ip,
        )
    )
    return Issued(row, property_type), None


def is_expired(row: License, on: date | None = None) -> bool:
    """หนังสือรับรองการแจ้งไม่มีวันหมดอายุ จึงไม่มีทางหมดอายุ"""
    if row.valid_until is None:
        return False
    return (on or date.today()) > row.valid_until
