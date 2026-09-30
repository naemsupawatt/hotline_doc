"""M11 — สรุปภาพรวมทั้งจังหวัดสำหรับหน่วยงานส่วนกลาง

โจทย์ตารางข้อ 5: ส่วนกลาง "ดูรายงานสรุปภาพรวมของทั้งจังหวัด **โดยไม่ก้าวก่าย
การพิจารณารายคำขอ**" ไฟล์นี้จึงคืนแต่ตัวเลขรวม ไม่มีชื่อผู้ยื่น ไม่มีเลขที่คำขอ
และไม่มีชื่อเจ้าหน้าที่รายคน

ปัญหาข้อสุดท้ายที่โจทย์ยกมาคือ "ส่วนกลางไม่มีข้อมูลภาพรวมว่าคำขอทั้งจังหวัด
ติดขัดที่ขั้นตอนใดมากที่สุด จึงแก้ปัญหาเชิงระบบได้ยาก" ตัวเลขทุกชุดในนี้จึงถูก
เลือกมาเพื่อตอบคำถามนั้นโดยตรง ไม่ใช่เพื่อให้หน้าจอดูแน่น
"""

from dataclasses import dataclass

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.authority import LocalAuthority
from app.models.classification import ApplicationClassification, PropertyType
from app.models.document import DocumentFile, DocumentRequirement, DocumentType
from app.models.enums import ApplicationStatus
from app.services.officer import REVIEWED_DOCUMENT_STATUSES

# คำขอที่ยังไม่จบกระบวนการ แยกตามว่า "ลูกบอลอยู่ในมือใคร"
# แยกแบบนี้เพราะการรู้ว่าค้างที่เจ้าหน้าที่หรือค้างที่ผู้ยื่น นำไปสู่การแก้ที่ต่างกัน
WAITING_ON_OFFICER = (ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW)
WAITING_ON_APPLICANT = (ApplicationStatus.NEEDS_REVISION,)
FINISHED = (ApplicationStatus.APPROVED, ApplicationStatus.LICENSE_ISSUED)

# ร่างยังไม่ถือว่าเข้าสู่กระบวนการ เพราะผู้ยื่นยังไม่ได้ส่งมา
IN_PROCESS = WAITING_ON_OFFICER + WAITING_ON_APPLICANT

# คำขอที่ยังไม่ถูกตัดสิน — ใช้กับรายงานเอกสารที่ผู้ยื่นยังไม่ได้อัปโหลด
#
# **รวมร่างด้วย** ต่างจาก IN_PROCESS ที่ใช้กับรายงานคอขวดฝั่งเจ้าหน้าที่
# เพราะร่างคือจุดที่ผู้ประกอบการกำลังเตรียมเอกสารอยู่จริง และเป็นที่ที่คนหยุดไป
# กลางคันมากที่สุด ถ้าตัดร่างออก รายงานนี้จะเหลือแต่เอกสารไม่บังคับของคำขอที่
# ยื่นแล้ว (เพราะ M6 บังคับว่าเอกสารบังคับต้องครบก่อนยื่น) ซึ่งแทบไม่บอกอะไร
NOT_DECIDED = (ApplicationStatus.DRAFT,) + IN_PROCESS


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
class DocumentBottleneck:
    """เอกสารหนึ่งฉบับ กับจำนวนคำขอที่ติดค้างอยู่ที่ฉบับนั้น"""

    code: str
    name_th: str
    count: int
    oldest_days: int
    by_authority: list[Bucket]


@dataclass(frozen=True)
class MissingUpload:
    """เอกสารหนึ่งฉบับ กับจำนวนคำขอที่ผู้ยื่นยังไม่ได้แนบเข้ามา"""

    code: str
    name_th: str
    count: int
    mandatory_count: int
    by_authority: list[Bucket]


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


def document_bottlenecks(db: Session) -> list[DocumentBottleneck]:
    """เอกสารที่ค้างรอการตรวจ เรียงจากฉบับที่ติดขัดมากที่สุด

    โจทย์ยกปัญหาไว้ว่าส่วนกลาง "ไม่มีข้อมูลภาพรวมว่าคำขอทั้งจังหวัดติดขัดที่
    ขั้นตอนใดมากที่สุด" รายงานภาพรวมตอบได้ถึงระดับ *สถานะคำขอ* แล้ว ชุดนี้ลงลึก
    อีกชั้นว่า **เอกสารฉบับไหน** เป็นตัวที่ทำให้ช้า และกระจุกอยู่ที่ท้องถิ่นใด

    ความต่างนี้เปลี่ยนการตัดสินใจจริง: ถ้าเอกสารฉบับเดียวค้างแทบทุกเขต ปัญหาอยู่ที่
    ตัวเอกสารหรือกระบวนการ (แบบฟอร์มกำกวม ขอยาก) ไม่ใช่ที่เจ้าหน้าที่คนใดคนหนึ่ง
    แต่ถ้าค้างกระจุกอยู่เขตเดียวหลายฉบับ แปลว่าเขตนั้นกำลังมีปัญหากำลังคน

    **นับเฉพาะคำขอที่ยังอยู่ในกระบวนการ** (`IN_PROCESS`) เอกสารที่ไม่มีใครตรวจ
    ในคำขอที่ตัดสินไปแล้วไม่ใช่คอขวด เพราะไม่มีใครรออะไรอยู่ และเจ้าหน้าที่ก็
    ย้อนกลับไปตรวจไม่ได้แล้ว ส่วนร่างยังไม่นับเพราะผู้ยื่นยังไม่ได้ส่งมา

    **"ยังไม่ได้ตรวจ" ใช้นิยามเดียวกับสัญลักษณ์แจ้งเตือนในคิวเจ้าหน้าที่**
    (`REVIEWED_DOCUMENT_STATUSES` ใน `services/officer.py`) ถ้าสองที่นี้ไม่ตรงกัน
    เจ้าหน้าที่กับส่วนกลางจะเห็นตัวเลขคนละชุดแล้วเถียงกันว่าใครถูก

    นับเป็นจำนวน "คำขอ" ที่ติดค้างเอกสารฉบับนั้น ไม่ใช่จำนวนไฟล์ เพราะเอกสาร
    ฉบับเดียวแนบได้หลายไฟล์ (ภาพหลายมุม = คนละ slot) แต่ตรวจกันเป็นฉบับ

    ยิงคำสั่งเดียวแล้วค่อยจัดกลุ่มในหน่วยความจำ เพราะผลลัพธ์มีขนาดเท่ากับ
    จำนวนเอกสาร x จำนวน อปท. ซึ่งเล็กมากอยู่แล้ว (ไม่เกินหลักร้อยแถว)
    """
    rows = db.execute(
        select(
            DocumentType.code,
            DocumentType.name_th,
            LocalAuthority.code,
            LocalAuthority.name,
            func.count(func.distinct(DocumentFile.application_id)),
            func.max(func.extract("epoch", func.now() - DocumentFile.created_at)),
        )
        .select_from(DocumentFile)
        .join(DocumentType, DocumentType.id == DocumentFile.document_type_id)
        .join(Application, Application.id == DocumentFile.application_id)
        .join(LocalAuthority, LocalAuthority.id == Application.local_authority_id)
        .where(
            DocumentFile.is_current,
            DocumentFile.status.not_in([s.value for s in REVIEWED_DOCUMENT_STATUSES]),
            Application.status.in_([s.value for s in IN_PROCESS]),
        )
        .group_by(DocumentType.code, DocumentType.name_th, LocalAuthority.code, LocalAuthority.name)
    ).all()

    grouped: dict[str, dict] = {}
    for code, name_th, authority_code, authority_name, count, oldest_seconds in rows:
        entry = grouped.setdefault(
            code, {"name_th": name_th, "count": 0, "oldest": 0.0, "authorities": []}
        )
        entry["count"] += count
        entry["oldest"] = max(entry["oldest"], oldest_seconds or 0)
        entry["authorities"].append(Bucket(authority_code, authority_name, count))

    result = [
        DocumentBottleneck(
            code=code,
            name_th=entry["name_th"],
            count=entry["count"],
            oldest_days=int(entry["oldest"] // 86400),
            # ในแต่ละฉบับ เขตที่ค้างมากสุดขึ้นก่อน ด้วยเหตุผลเดียวกับตารางท้องถิ่น
            by_authority=sorted(entry["authorities"], key=lambda b: -b.count),
        )
        for code, entry in grouped.items()
    ]

    # ติดขัดมากสุดขึ้นก่อน เท่ากันให้เรียงตามรหัสเอกสารเพื่อให้ลำดับคงที่ทุกครั้ง
    result.sort(key=lambda r: (-r.count, r.code))
    return result


def missing_uploads(db: Session) -> list[MissingUpload]:
    """เอกสารที่ผู้ประกอบการยังไม่ได้อัปโหลดเข้ามา เรียงจากฉบับที่ขาดมากที่สุด

    คู่แฝดของ `document_bottlenecks` แต่มองอีกฝั่งของกระบวนการ — อันนั้นตอบว่า
    ของที่ส่งมาแล้วค้างอยู่ที่เจ้าหน้าที่ตรงไหน อันนี้ตอบว่าผู้ยื่นติดตรงไหน
    จนยังส่งของเข้ามาไม่ได้ ซึ่งแก้คนละทาง (เร่งเจ้าหน้าที่ กับ ช่วยผู้ยื่น)

    **รายการเอกสารที่ต้องใช้ ยึดจาก snapshot ผลจำแนกของแต่ละคำขอ** แล้วเทียบกับ
    ไฟล์รุ่นปัจจุบันที่มีอยู่จริง ใช้กติกาเดียวกับที่ผู้ยื่นเห็นในหน้าคำขอ
    (`classification.required_documents`) คือดูจาก `document_requirement` ของ
    ประเภทนั้น และนับเฉพาะ `document_type` ที่ยังเปิดใช้งาน ถ้าเงื่อนไขสองที่นี้
    หลุดจากกัน ตัวเลขของส่วนกลางจะไม่ตรงกับสิ่งที่ผู้ยื่นเห็นบนหน้าจอตัวเอง

    **แยกจำนวน "บังคับ" ออกมาด้วย** เพราะเอกสารไม่บังคับบางฉบับตั้งใจให้ขาดได้
    (ช่องแนบใน ร.ร.1 เช่น หนังสือรับรองนิติบุคคล ซึ่งบุคคลธรรมดาไม่มีอยู่แล้ว)
    ถ้ารวมเป็นตัวเลขเดียว ยอดจะพองด้วยของที่ไม่มีใครต้องส่ง แล้วอ่านผิดว่า
    ผู้ยื่นทิ้งงานทั้งที่ทำครบแล้ว

    ยิงคำสั่งเดียวแล้วจัดกลุ่มในหน่วยความจำ ด้วยเหตุผลเดียวกับรายงานคอขวด
    """
    rows = db.execute(
        select(
            DocumentType.code,
            DocumentType.name_th,
            LocalAuthority.code,
            LocalAuthority.name,
            func.count(func.distinct(Application.id)),
            func.count(func.distinct(Application.id)).filter(DocumentRequirement.is_mandatory),
        )
        .select_from(Application)
        .join(
            ApplicationClassification,
            ApplicationClassification.application_id == Application.id,
        )
        .join(
            DocumentRequirement,
            DocumentRequirement.property_type_id == ApplicationClassification.property_type_id,
        )
        .join(DocumentType, DocumentType.id == DocumentRequirement.document_type_id)
        .join(LocalAuthority, LocalAuthority.id == Application.local_authority_id)
        # เหลือไว้เฉพาะคู่ (คำขอ, เอกสาร) ที่ไม่มีไฟล์รุ่นปัจจุบันอยู่เลย
        .outerjoin(
            DocumentFile,
            and_(
                DocumentFile.application_id == Application.id,
                DocumentFile.document_type_id == DocumentRequirement.document_type_id,
                DocumentFile.is_current,
            ),
        )
        .where(
            Application.status.in_([s.value for s in NOT_DECIDED]),
            DocumentType.is_active,
            DocumentFile.id.is_(None),
        )
        .group_by(
            DocumentType.code,
            DocumentType.name_th,
            LocalAuthority.code,
            LocalAuthority.name,
        )
    ).all()

    grouped: dict[str, dict] = {}
    for code, name_th, authority_code, authority_name, count, mandatory in rows:
        entry = grouped.setdefault(
            code, {"name_th": name_th, "count": 0, "mandatory": 0, "authorities": []}
        )
        entry["count"] += count
        entry["mandatory"] += mandatory
        entry["authorities"].append(Bucket(authority_code, authority_name, count))

    result = [
        MissingUpload(
            code=code,
            name_th=entry["name_th"],
            count=entry["count"],
            mandatory_count=entry["mandatory"],
            by_authority=sorted(entry["authorities"], key=lambda b: -b.count),
        )
        for code, entry in grouped.items()
    ]

    # ขาดมากสุดขึ้นก่อน เท่ากันให้เรียงตามรหัสเอกสารเพื่อให้ลำดับคงที่ทุกครั้ง
    result.sort(key=lambda r: (-r.count, r.code))
    return result
