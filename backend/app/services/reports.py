"""M11 — สรุปภาพรวมทั้งจังหวัดสำหรับหน่วยงานส่วนกลาง

โจทย์ตารางข้อ 5: ส่วนกลาง "ดูรายงานสรุปภาพรวมของทั้งจังหวัด **โดยไม่ก้าวก่าย
การพิจารณารายคำขอ**" ไฟล์นี้จึงคืนแต่ตัวเลขรวม ไม่มีชื่อผู้ยื่น ไม่มีเลขที่คำขอ
และไม่มีชื่อเจ้าหน้าที่รายคน

ปัญหาข้อสุดท้ายที่โจทย์ยกมาคือ "ส่วนกลางไม่มีข้อมูลภาพรวมว่าคำขอทั้งจังหวัด
ติดขัดที่ขั้นตอนใดมากที่สุด จึงแก้ปัญหาเชิงระบบได้ยาก" ตัวเลขทุกชุดในนี้จึงถูก
เลือกมาเพื่อตอบคำถามนั้นโดยตรง ไม่ใช่เพื่อให้หน้าจอดูแน่น
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.authority import LocalAuthority
from app.models.classification import ApplicationClassification, PropertyType
from app.models.enums import ApplicationStatus

# คำขอที่ยังไม่จบกระบวนการ แยกตามว่า "ลูกบอลอยู่ในมือใคร"
# แยกแบบนี้เพราะการรู้ว่าค้างที่เจ้าหน้าที่หรือค้างที่ผู้ยื่น นำไปสู่การแก้ที่ต่างกัน
WAITING_ON_OFFICER = (ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW)
WAITING_ON_APPLICANT = (ApplicationStatus.NEEDS_REVISION,)
FINISHED = (ApplicationStatus.APPROVED, ApplicationStatus.LICENSE_ISSUED)

# ร่างยังไม่ถือว่าเข้าสู่กระบวนการ เพราะผู้ยื่นยังไม่ได้ส่งมา
IN_PROCESS = WAITING_ON_OFFICER + WAITING_ON_APPLICANT


@dataclass(frozen=True)
class Bucket:
    """หนึ่งแถวในการแยกกลุ่ม"""

    key: str
    label: str
    count: int


@dataclass(frozen=True)
class AuthorityRow:
    name: str
    total: int
    waiting_on_officer: int
    waiting_on_applicant: int
    finished: int
    longest_wait_days: int


@dataclass(frozen=True)
class Overview:
    total: int
    draft: int
    waiting_on_officer: int
    waiting_on_applicant: int
    finished: int
    rejected: int
    by_property_type: list[Bucket]
    by_status: list[Bucket]
    by_authority: list[AuthorityRow]


STATUS_LABEL = {
    ApplicationStatus.DRAFT: "ร่าง ยังไม่ยื่น",
    ApplicationStatus.SUBMITTED: "ยื่นแล้ว รอเจ้าหน้าที่รับเรื่อง",
    ApplicationStatus.UNDER_REVIEW: "เจ้าหน้าที่กำลังตรวจ",
    ApplicationStatus.NEEDS_REVISION: "รอผู้ยื่นแก้ไข",
    ApplicationStatus.APPROVED: "อนุมัติแล้ว",
    ApplicationStatus.REJECTED: "ไม่อนุมัติ",
    ApplicationStatus.LICENSE_ISSUED: "ออกเอกสารแล้ว",
}


def _counts_by_status(db: Session) -> dict[str, int]:
    rows = db.execute(select(Application.status, func.count()).group_by(Application.status)).all()
    return {status: count for status, count in rows}


def _by_property_type(db: Session) -> list[Bucket]:
    """จำนวนคำขอแยกตามประเภทที่พัก (M11)

    นับจาก snapshot ผลจำแนกของแต่ละคำขอ ไม่ใช่คำนวณประเภทใหม่ตอนทำรายงาน
    เพราะกฎอาจถูกแก้ไปแล้ว รายงานต้องสะท้อนสิ่งที่ตัดสินไปจริง
    """
    rows = db.execute(
        select(PropertyType.code, PropertyType.name_th, func.count(Application.id))
        .select_from(PropertyType)
        .join(
            ApplicationClassification,
            ApplicationClassification.property_type_id == PropertyType.id,
            isouter=True,
        )
        .join(
            Application,
            Application.id == ApplicationClassification.application_id,
            isouter=True,
        )
        .group_by(PropertyType.code, PropertyType.name_th, PropertyType.display_order)
        .order_by(PropertyType.display_order)
    ).all()
    return [Bucket(code, name, count) for code, name, count in rows]


def _by_status(db: Session) -> list[Bucket]:
    """คำขอค้างอยู่ที่ขั้นตอนใดบ้าง (M11) — เรียงตามลำดับของกระบวนการ"""
    counts = _counts_by_status(db)
    return [
        Bucket(status.value, STATUS_LABEL[status], counts.get(status.value, 0))
        for status in ApplicationStatus
    ]


def _by_authority(db: Session) -> list[AuthorityRow]:
    """จำนวนคำขอแยกตามท้องถิ่น (M11) เรียงจากที่ค้างมากที่สุด

    รวม อปท. ที่ยังไม่มีคำขอเลยด้วย (outer join) เพราะการเห็นว่าเขตไหน
    ยังไม่มีใครใช้ระบบ ก็เป็นข้อมูลเชิงระบบเหมือนกัน
    """
    waiting_officer = func.count(Application.id).filter(
        Application.status.in_([s.value for s in WAITING_ON_OFFICER])
    )
    waiting_applicant = func.count(Application.id).filter(
        Application.status.in_([s.value for s in WAITING_ON_APPLICANT])
    )
    finished = func.count(Application.id).filter(
        Application.status.in_([s.value for s in FINISHED])
    )
    # วันที่ค้างนานที่สุดของคำขอที่ยังไม่จบ — ตัวเลขที่ชี้จุดที่ควรเข้าไปช่วย
    longest = func.max(func.extract("epoch", func.now() - Application.status_changed_at)).filter(
        Application.status.in_([s.value for s in IN_PROCESS])
    )

    rows = db.execute(
        select(
            LocalAuthority.name,
            func.count(Application.id),
            waiting_officer,
            waiting_applicant,
            finished,
            longest,
        )
        .select_from(LocalAuthority)
        .join(Application, Application.local_authority_id == LocalAuthority.id, isouter=True)
        .group_by(LocalAuthority.id, LocalAuthority.name)
        .order_by(LocalAuthority.id)
    ).all()

    result = [
        AuthorityRow(
            name=name,
            total=total or 0,
            waiting_on_officer=w_officer or 0,
            waiting_on_applicant=w_applicant or 0,
            finished=done or 0,
            longest_wait_days=int((longest_seconds or 0) // 86400),
        )
        for name, total, w_officer, w_applicant, done, longest_seconds in rows
    ]
    # ค้างมากสุดขึ้นก่อน เพราะนั่นคือสิ่งที่ส่วนกลางต้องเห็นก่อน
    result.sort(
        key=lambda r: (r.waiting_on_officer + r.waiting_on_applicant, r.total), reverse=True
    )
    return result


def overview(db: Session) -> Overview:
    counts = _counts_by_status(db)

    def total_of(statuses) -> int:
        return sum(counts.get(s.value, 0) for s in statuses)

    return Overview(
        total=sum(counts.values()),
        draft=counts.get(ApplicationStatus.DRAFT.value, 0),
        waiting_on_officer=total_of(WAITING_ON_OFFICER),
        waiting_on_applicant=total_of(WAITING_ON_APPLICANT),
        finished=total_of(FINISHED),
        rejected=counts.get(ApplicationStatus.REJECTED.value, 0),
        by_property_type=_by_property_type(db),
        by_status=_by_status(db),
        by_authority=_by_authority(db),
    )
