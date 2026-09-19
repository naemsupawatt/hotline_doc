"""M8/M9 — schema ของหน้าทำงานเจ้าหน้าที่

ใส่ examples= ทุกช่องตามกฎของทีม (FastAPI เอาไปแสดงใน /docs)
ข้อมูลตัวอย่างเป็นข้อมูลสมมติ (กติกาข้อ 14)
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ReviewDecision
from app.schemas.application import PropertyOut
from app.schemas.wizard import DocumentChecklistOut, FeeOut


class QueueItemOut(BaseModel):
    """หนึ่งแถวในคิวงานของเจ้าหน้าที่"""

    application_no: str = Field(examples=["PKT-2569-000123"])
    status: str = Field(examples=["submitted"])
    days_waiting: int = Field(examples=[3], description="ค้างอยู่ในสถานะนี้มากี่วันแล้ว (M7)")
    property_name: str = Field(examples=["บ้านพักริมเลกะรน"])
    property_type_name: str = Field(examples=["ไม่เข้าข่ายโรงแรม"])
    local_authority_name: str = Field(examples=["เทศบาลตำบลกะรน"])
    submitted_at: datetime | None = Field(default=None, examples=["2026-09-19T21:30:00+07:00"])


class OfficerApplicationOut(BaseModel):
    """หน้าตรวจคำขอหนึ่งใบของเจ้าหน้าที่"""

    application_no: str = Field(examples=["PKT-2569-000123"])
    status: str = Field(examples=["under_review"])
    days_waiting: int = Field(examples=[3])
    submitted_at: datetime | None = Field(default=None)
    decided_at: datetime | None = Field(default=None)
    decision_reason: str | None = Field(default=None)

    property_type_name: str = Field(examples=["ไม่เข้าข่ายโรงแรม"])
    requires_license: bool = Field(examples=[False])
    reason: str = Field(examples=["ที่พักของคุณมี 6 ห้อง และรับผู้เข้าพักได้ 24 คน ..."])
    fee: FeeOut | None = None

    property: PropertyOut
    documents: DocumentChecklistOut

    # ใช้เปิด/ปิดปุ่มอนุมัติ และบอกเหตุผลเมื่อยังกดไม่ได้
    can_approve: bool = Field(examples=[False])
    pending_documents: list[str] = Field(
        default_factory=list,
        examples=[["A02 สำเนาทะเบียนบ้านผู้แจ้ง"]],
        description="เอกสารบังคับที่ยังไม่ผ่านการตรวจ",
    )

    # M10 — ปุ่มออกเอกสารขึ้นเมื่ออนุมัติแล้วและยังไม่เคยออก
    can_issue_license: bool = Field(default=False, examples=[False])
    license_no: str | None = Field(default=None, examples=[None])


class ReviewDocumentRequest(BaseModel):
    decision: ReviewDecision = Field(
        examples=[ReviewDecision.PASS],
        description="pass = ผ่าน, request_revision = ขอให้แก้ไข, fail = ไม่ผ่าน",
    )
    comment: str | None = Field(
        default=None,
        max_length=1000,
        examples=["ภาพเบลอจนอ่านเลขที่บ้านไม่ออก กรุณาถ่ายใหม่"],
        description="บังคับเมื่อขอให้แก้ไขหรือไม่ผ่าน",
    )


class DecisionRequest(BaseModel):
    decision: str = Field(
        examples=["approve"],
        description="approve = อนุมัติ, reject = ไม่อนุมัติ, request_revision = ขอให้แก้ไข",
    )
    reason: str | None = Field(
        default=None,
        max_length=1000,
        examples=[None],
        description="บังคับเมื่อไม่อนุมัติหรือขอให้แก้ไข",
    )
