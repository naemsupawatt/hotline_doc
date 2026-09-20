"""M8/M9 — งานของเจ้าหน้าที่ท้องถิ่น: คิวคำขอ ตรวจเอกสาร และสรุปผล

หัวใจของไฟล์นี้คือ **ขอบเขตเขต** (T-09)
เจ้าหน้าที่เห็นและแตะได้เฉพาะคำขอใน อปท. ที่ตนสังกัด ผ่านตาราง
OfficerAssignment ซึ่งเป็น many-to-many เพราะบางคนดูแลมากกว่าหนึ่ง อปท.
(เช่น อบจ. ที่ครอบทั้งจังหวัด)

โจทย์ไม่ได้บอกแค่ว่า "ต้องปฏิเสธ" แต่บอกว่าต้อง **บันทึกความพยายามนั้นไว้ด้วย**
ฟังก์ชัน deny_cross_authority() จึงเป็นตัวเดียวที่ใช้ปฏิเสธ เพื่อไม่ให้มี
เส้นทางไหนหลุดไปปฏิเสธเงียบ ๆ โดยไม่เขียน log
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.application import Application, ApplicationStatusHistory
from app.models.audit import AuditLog
from app.models.classification import ApplicationClassification
from app.models.document import DocumentFile, DocumentRequirement, DocumentType
from app.models.enums import ApplicationStatus, DocumentStatus, ReviewDecision
from app.models.property import Property
from app.models.user import OfficerAssignment, User

# สถานะที่เจ้าหน้าที่ยังแก้ผลได้ — ตัดสินไปแล้วต้องไม่ย้อนกลับมาแก้เงียบ ๆ
OPEN_STATUSES = {
    ApplicationStatus.SUBMITTED,
    ApplicationStatus.UNDER_REVIEW,
    ApplicationStatus.NEEDS_REVISION,
}

# สถานะที่ยัง "รอเจ้าหน้าที่ทำอะไรสักอย่าง" — ใช้กรองคิวงานหลัก
#
# ต้องแยกจาก OPEN_STATUSES เพราะสองชุดนี้ตอบคนละคำถาม:
#   OPEN_STATUSES        = ยังแก้ผลพิจารณาได้ไหม
#   NEEDS_OFFICER_ACTION = ยังค้างงานที่เจ้าหน้าที่ไหม
#
# approved อยู่ในชุดนี้เพราะยังค้างการออกเอกสาร (M10) แต่ต้องตัดสินซ้ำไม่ได้
# ส่วน needs_revision ไม่อยู่ เพราะลูกบอลอยู่ที่ผู้ยื่น ไม่ใช่เจ้าหน้าที่
NEEDS_OFFICER_ACTION = {
    ApplicationStatus.SUBMITTED,
    ApplicationStatus.UNDER_REVIEW,
    ApplicationStatus.APPROVED,
}

# รอผู้ยื่นส่งเอกสารกลับมา — เจ้าหน้าที่ทำอะไรไม่ได้จนกว่าจะได้รับ
# แยกออกมาเป็นคิวของตัวเอง เพราะเป็นคนละงานกับที่ตัวเองต้องลงมือ
WAITING_ON_APPLICANT = {ApplicationStatus.NEEDS_REVISION}

# จบกระบวนการแล้ว เก็บไว้ให้ค้นย้อนหลัง ไม่ต้องขึ้นคิวหลัก
CLOSED_STATUSES = {
    ApplicationStatus.LICENSE_ISSUED,
    ApplicationStatus.REJECTED,
}

# ผลตรวจรายฉบับ -> สถานะของเอกสารฉบับนั้น
#
# ทั้ง "ขอแก้ไข" และ "ไม่ผ่าน" ทำให้ผู้ยื่นต้องส่งไฟล์ใหม่เหมือนกัน
# สถานะเอกสารจึงเป็นค่าเดียวกัน ส่วนความต่างถูกเก็บไว้ใน DocumentReview.decision
# เพื่อให้ย้อนดูได้ว่าเจ้าหน้าที่ตัดสินด้วยคำไหน
DOCUMENT_STATUS_OF = {
    ReviewDecision.PASS: DocumentStatus.APPROVED,
    ReviewDecision.REQUEST_REVISION: DocumentStatus.REVISION_REQUESTED,
    ReviewDecision.FAIL: DocumentStatus.REVISION_REQUESTED,
}

# ผลตรวจที่ต้องมีเหตุผลกำกับเสมอ — ผู้ยื่นต้องรู้ว่าต้องแก้อะไร
NEEDS_COMMENT = {ReviewDecision.REQUEST_REVISION, ReviewDecision.FAIL}


@dataclass(frozen=True)
class QueueRow:
    application: Application
    property_obj: Property
    classification: ApplicationClassification
    days_waiting: int


def authority_ids(db: Session, officer: User) -> list[int]:
    """อปท. ที่เจ้าหน้าที่คนนี้รับผิดชอบ"""
    return list(
        db.scalars(
            select(OfficerAssignment.local_authority_id).where(
                OfficerAssignment.officer_id == officer.id,
                OfficerAssignment.is_active,
            )
        ).all()
    )


def deny_cross_authority(
    db: Session,
    *,
    officer: User,
    application: Application,
    ip: str | None,
    detail: str,
) -> None:
    """บันทึกความพยายามเปิดคำขอข้ามเขต (T-09)

    เรียกก่อนโยน HTTPException เสมอ ผู้เรียกต้อง commit เองเพื่อให้ log อยู่
    แม้ transaction หลักจะถูก rollback
    """
    db.add(
        AuditLog(
            actor_id=officer.id,
            action="officer.cross_authority_denied",
            entity_type="application",
            entity_id=application.id,
            outcome="denied",
            detail=detail,
            ip_address=ip,
        )
    )


# กลุ่มคิวที่หน้าจอเลือกดูได้ — ตรงกับแท็บบนหน้าคิวคำขอ
QUEUE_SCOPES = {
    "open": NEEDS_OFFICER_ACTION,
    "revision": WAITING_ON_APPLICANT,
    "closed": CLOSED_STATUSES,
    "all": set(ApplicationStatus) - {ApplicationStatus.DRAFT},
}


def queue(db: Session, officer: User, scope: str = "open") -> list[QueueRow]:
    """คิวคำขอในเขตของเจ้าหน้าที่ รอนานสุดขึ้นก่อน

    เรียงจากคำขอที่ค้างนานที่สุด เพราะปัญหาที่โจทย์ยกมาคือผู้ยื่นไม่รู้ว่า
    เรื่องค้างอยู่ที่ใคร การให้เรื่องเก่าขึ้นก่อนช่วยไม่ให้มีคำขอตกค้างลืม

    ไม่รวมคำขอสถานะร่างไม่ว่ากลุ่มไหน เพราะผู้ยื่นยังไม่ได้ส่งมา
    เจ้าหน้าที่จึงไม่ควรเห็น
    """
    mine = authority_ids(db, officer)
    if not mine:
        return []

    statuses = QUEUE_SCOPES.get(scope, NEEDS_OFFICER_ACTION)

    query = (
        select(Application)
        .where(
            Application.local_authority_id.in_(mine),
            Application.status.in_([s.value for s in statuses]),
        )
        .order_by(Application.status_changed_at)
    )

    rows: list[QueueRow] = []
    for application in db.scalars(query).all():
        prop = db.get(Property, application.property_id)
        snapshot = db.scalar(
            select(ApplicationClassification)
            .options(selectinload(ApplicationClassification.property_type))
            .where(ApplicationClassification.application_id == application.id)
        )
        rows.append(
            QueueRow(application, prop, snapshot, _days_since(application.status_changed_at))
        )
    return rows


def _days_since(moment: datetime | None) -> int:
    if moment is None:
        return 0
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return max((datetime.now(UTC) - moment).days, 0)


def in_scope(db: Session, officer: User, application: Application) -> bool:
    return application.local_authority_id in authority_ids(db, officer)


def _claim(db: Session, application: Application, officer: User) -> str | None:
    """รับเรื่องอัตโนมัติเมื่อเจ้าหน้าที่ลงมือตรวจฉบับแรก

    ไม่ทำเป็นปุ่มแยก เพราะการบังคับกด "รับเรื่อง" ก่อนตรวจเป็นขั้นตอนที่
    ไม่ได้ให้ข้อมูลอะไรเพิ่ม และเป็นจุดที่เจ้าหน้าที่ลืมกดบ่อย
    คืนสถานะเดิมถ้ามีการเปลี่ยน ไม่งั้นคืน None
    """
    if application.status != ApplicationStatus.SUBMITTED:
        return None

    previous = application.status
    application.status = ApplicationStatus.UNDER_REVIEW
    application.status_changed_at = func.now()
    application.assigned_officer_id = officer.id
    db.add(
        ApplicationStatusHistory(
            application_id=application.id,
            from_status=previous,
            to_status=ApplicationStatus.UNDER_REVIEW,
            changed_by_id=officer.id,
            note="เจ้าหน้าที่รับเรื่องและเริ่มตรวจเอกสาร",
        )
    )
    return previous


def review_document(
    db: Session,
    *,
    application: Application,
    file: DocumentFile,
    officer: User,
    decision: ReviewDecision,
    comment: str | None,
    ip: str | None = None,
) -> tuple[bool, str | None]:
    """บันทึกผลตรวจเอกสารหนึ่งฉบับ (M8)"""
    from app.models.document import DocumentReview

    if application.status not in OPEN_STATUSES:
        return False, "คำขอนี้ตัดสินไปแล้ว จึงแก้ผลตรวจเอกสารไม่ได้"

    if decision in NEEDS_COMMENT and not (comment or "").strip():
        return False, "กรุณาระบุเหตุผล เพื่อให้ผู้ยื่นรู้ว่าต้องแก้ไขอะไร"

    if not file.is_current:
        return False, "ไฟล์นี้ไม่ใช่รุ่นล่าสุดแล้ว กรุณาตรวจรุ่นล่าสุดแทน"

    _claim(db, application, officer)

    db.add(
        DocumentReview(
            document_file_id=file.id,
            reviewer_id=officer.id,
            decision=decision,
            comment=(comment or "").strip() or None,
            reviewed_at=datetime.now(UTC),
        )
    )
    file.status = DOCUMENT_STATUS_OF[decision]

    db.add(
        AuditLog(
            actor_id=officer.id,
            action="document.review",
            entity_type="document_file",
            entity_id=file.id,
            outcome="success",
            detail=(
                f"ตรวจ {file.document_type.code} ของคำขอ {application.application_no}: "
                f"{decision.value}"
            ),
            ip_address=ip,
        )
    )
    return True, None


def mandatory_not_approved(db: Session, application: Application) -> list[str]:
    """เอกสารบังคับที่ยังไม่ผ่านการตรวจ — ใช้กันการกดอนุมัติข้ามขั้น"""
    snapshot = db.scalar(
        select(ApplicationClassification).where(
            ApplicationClassification.application_id == application.id
        )
    )
    requirements = db.scalars(
        select(DocumentRequirement)
        .options(selectinload(DocumentRequirement.document_type))
        .join(DocumentType)
        .where(
            DocumentRequirement.property_type_id == snapshot.property_type_id,
            DocumentRequirement.is_mandatory,
            DocumentType.is_active,
        )
        .order_by(DocumentRequirement.display_order)
    ).all()

    approved_types = {
        row.document_type_id
        for row in db.scalars(
            select(DocumentFile).where(
                DocumentFile.application_id == application.id,
                DocumentFile.is_current,
                DocumentFile.status == DocumentStatus.APPROVED,
            )
        ).all()
    }

    return [
        f"{r.document_type.code} {r.document_type.name_th}"
        for r in requirements
        # รวมแบบฟอร์มที่ระบบสร้างด้วย เพราะมีลายมือชื่อผู้แจ้งเป็นไฟล์ให้ตรวจจริง
        # ถ้ายกเว้นไว้ ลายมือชื่อจะเป็นสิ่งเดียวในคำขอที่ไม่มีใครตรวจเลย
        if r.document_type_id not in approved_types
    ]


DECISION_TARGET = {
    "approve": ApplicationStatus.APPROVED,
    "reject": ApplicationStatus.REJECTED,
    "request_revision": ApplicationStatus.NEEDS_REVISION,
}

DECISION_NOTE = {
    "approve": "เจ้าหน้าที่อนุมัติคำขอ",
    "reject": "เจ้าหน้าที่ไม่อนุมัติคำขอ",
    "request_revision": "เจ้าหน้าที่ขอให้ผู้ยื่นแก้ไขเอกสาร",
}


def decide(
    db: Session,
    *,
    application: Application,
    officer: User,
    decision: str,
    reason: str | None,
    ip: str | None = None,
) -> tuple[bool, str | None]:
    """สรุปผลคำขอ (M8) — เปลี่ยนสถานะ + เขียนประวัติ + AuditLog (M9)"""
    if application.status not in OPEN_STATUSES:
        return False, "คำขอนี้ตัดสินไปแล้ว"

    target = DECISION_TARGET.get(decision)
    if target is None:
        return False, "ผลการพิจารณาไม่ถูกต้อง"

    if decision != "approve" and not (reason or "").strip():
        return False, "กรุณาระบุเหตุผล เพื่อให้ผู้ยื่นรู้ว่าต้องทำอะไรต่อ"

    if decision == "approve":
        pending = mandatory_not_approved(db, application)
        if pending:
            return False, "ยังอนุมัติไม่ได้ เพราะมีเอกสารบังคับที่ยังไม่ผ่านการตรวจ: " + ", ".join(pending)

    previous = application.status
    application.status = target
    application.status_changed_at = func.now()
    application.assigned_officer_id = officer.id
    application.decision_reason = (reason or "").strip() or None
    if target in {ApplicationStatus.APPROVED, ApplicationStatus.REJECTED}:
        application.decided_at = func.now()

    db.add(
        ApplicationStatusHistory(
            application_id=application.id,
            from_status=previous,
            to_status=target,
            changed_by_id=officer.id,
            note=DECISION_NOTE[decision],
        )
    )
    db.add(
        AuditLog(
            actor_id=officer.id,
            action="application.decide",
            entity_type="application",
            entity_id=application.id,
            from_status=previous,
            to_status=target,
            outcome="success",
            detail=f"{DECISION_NOTE[decision]} {application.application_no}",
            ip_address=ip,
        )
    )
    return True, None
