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
from app.schemas.reports import AuthorityRowOut, BucketOut, OverviewOut
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


# TODO S5: GET /wait-times   ระยะเวลารอเฉลี่ยในแต่ละขั้นตอน
# TODO S6: GET /workload     ภาระงานเจ้าหน้าที่แบบไม่ระบุตัวตน (ใช้ pseudonym_code)
