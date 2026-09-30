"""M11 — รายงานภาพรวมสำหรับหน่วยงานส่วนกลาง

ส่วนกลาง "ดูภาพรวมโดยไม่ก้าวก่ายการพิจารณารายคำขอ" -> endpoint กลุ่มนี้
คืนเฉพาะข้อมูลสรุป ไม่มีเลขที่คำขอ ไม่มีชื่อผู้ยื่น ไม่มีชื่อเจ้าหน้าที่รายคน
และไม่มีปุ่มใดที่เปลี่ยนผลพิจารณาได้

เปิดให้ทั้ง central และ super_admin เพราะผู้ดูแลระบบต้องตรวจสอบได้ว่ารายงาน
ทำงานถูกต้องหลังแก้เกณฑ์ (US-09)

เจ้าของงานส่วนนี้: <ใส่ชื่อสมาชิก>
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import DbSession, require_role
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.reports import (
    AuthorityRowOut,
    BucketOut,
    DocumentBottleneckOut,
    MissingUploadOut,
    OverviewOut,
)
from app.services import reports as reports_svc

router = APIRouter()

CurrentViewer = Annotated[User, Depends(require_role(UserRole.CENTRAL, UserRole.SUPER_ADMIN))]


@router.get(
    "/overview",
    response_model=OverviewOut,
    summary="ภาพรวมคำขอทั้งจังหวัด แยกตามประเภท ท้องถิ่น และขั้นตอนที่ค้าง",
    responses={403: {"description": "เฉพาะหน่วยงานส่วนกลางและผู้ดูแลระบบ"}},
)
def overview(db: DbSession, current: CurrentViewer) -> OverviewOut:
    data = reports_svc.overview(db)
    return OverviewOut(
        total=data.total,
        draft=data.draft,
        waiting_on_officer=data.waiting_on_officer,
        waiting_on_applicant=data.waiting_on_applicant,
        finished=data.finished,
        rejected=data.rejected,
        by_property_type=[BucketOut(**vars(b)) for b in data.by_property_type],
        by_status=[BucketOut(**vars(b)) for b in data.by_status],
        by_authority=[AuthorityRowOut(**vars(r)) for r in data.by_authority],
    )


@router.get(
    "/document-bottlenecks",
    response_model=list[DocumentBottleneckOut],
    summary="เอกสารที่ค้างรอการตรวจ เรียงจากฉบับที่ติดขัดมากที่สุด",
    responses={403: {"description": "เฉพาะหน่วยงานส่วนกลางและผู้ดูแลระบบ"}},
)
def document_bottlenecks(db: DbSession, current: CurrentViewer) -> list[DocumentBottleneckOut]:
    """เอกสารฉบับไหนเป็นคอขวด และค้างอยู่ที่ท้องถิ่นใด

    ลงลึกกว่า /overview อีกชั้น: overview บอกว่าคำขอค้างที่ "ขั้นตอน" ใด
    ส่วนชุดนี้บอกว่าค้างที่ "เอกสารฉบับ" ใด ซึ่งนำไปสู่การแก้คนละแบบ

    นับเฉพาะคำขอที่ยังอยู่ในกระบวนการ เอกสารที่ไม่มีใครตรวจในคำขอที่ตัดสิน
    ไปแล้วไม่ใช่คอขวด เพราะไม่มีใครรออยู่
    """
    return [
        DocumentBottleneckOut(
            code=row.code,
            name_th=row.name_th,
            count=row.count,
            oldest_days=row.oldest_days,
            by_authority=[BucketOut(**vars(b)) for b in row.by_authority],
        )
        for row in reports_svc.document_bottlenecks(db)
    ]


@router.get(
    "/missing-uploads",
    response_model=list[MissingUploadOut],
    summary="เอกสารที่ผู้ประกอบการยังไม่ได้อัปโหลด เรียงจากฉบับที่ขาดมากที่สุด",
    responses={403: {"description": "เฉพาะหน่วยงานส่วนกลางและผู้ดูแลระบบ"}},
)
def missing_uploads(db: DbSession, current: CurrentViewer) -> list[MissingUploadOut]:
    """ผู้ยื่นติดตรงเอกสารฉบับไหนจนยังส่งเข้ามาไม่ได้

    คู่แฝดของ /document-bottlenecks แต่มองอีกฝั่ง: อันนั้นคือของที่ส่งมาแล้ว
    ค้างที่เจ้าหน้าที่ อันนี้คือของที่ยังไม่ถูกส่งมา ซึ่งแก้คนละทาง

    รวมคำขอที่ยังเป็นร่างด้วย เพราะนั่นคือจุดที่ผู้ประกอบการกำลังเตรียมเอกสาร
    และเป็นที่ที่คนหยุดไปกลางคันมากที่สุด
    """
    return [
        MissingUploadOut(
            code=row.code,
            name_th=row.name_th,
            count=row.count,
            mandatory_count=row.mandatory_count,
            by_authority=[BucketOut(**vars(b)) for b in row.by_authority],
        )
        for row in reports_svc.missing_uploads(db)
    ]


# TODO S5: GET /wait-times   ระยะเวลารอเฉลี่ยในแต่ละขั้นตอน
# TODO S6: GET /workload     ภาระงานเจ้าหน้าที่แบบไม่ระบุตัวตน (ใช้ pseudonym_code)
