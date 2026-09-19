"""M6/M7 — schema ของการเปิดคำขอและติดตามสถานะ

ใส่ examples= ทุกช่องตามกฎของทีม (FastAPI เอาไปแสดงใน /docs)
ข้อมูลตัวอย่างเป็นข้อมูลสมมติ (กติกาข้อ 14)
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AccommodationKind
from app.schemas.wizard import DocumentChecklistOut, FeeOut


class StartApplicationRequest(BaseModel):
    """คำตอบจาก wizard + ข้อมูลที่พักที่ต้องมีก่อนเปิดคำขอ

    ไม่รับ "ประเภทที่พัก" จาก client โดยตั้งใจ — เซิร์ฟเวอร์จำแนกใหม่เองเสมอ
    ไม่งั้นใครก็อ้างได้ว่าตัวเองไม่เข้าข่ายโรงแรม
    """

    rooms: int = Field(ge=1, le=9999, examples=[6])
    guests: int = Field(ge=1, le=99999, examples=[24])
    has_restaurant: bool = Field(default=False, examples=[False])
    local_authority_id: int = Field(examples=[5], description="อปท. ที่ที่พักตั้งอยู่ — บังคับตอนเปิดคำขอ")

    property_name: str = Field(min_length=1, max_length=200, examples=["บ้านพักริมเลกะรน"])
    address: str = Field(
        min_length=1, examples=["99/9 หมู่ 1 ถนนกะรน ตำบลกะรน อำเภอเมืองภูเก็ต จังหวัดภูเก็ต 83100"]
    )
    accommodation_kind: AccommodationKind = Field(
        examples=[AccommodationKind.DETACHED_HOUSE],
        description="ลักษณะที่พักตามแบบหนังสือแจ้งฯ",
    )
    accommodation_kind_other: str | None = Field(
        default=None,
        max_length=120,
        examples=[None],
        description='ข้อความระบุ เมื่อเลือกลักษณะที่พักเป็น "อื่น ๆ"',
    )

    latitude: float | None = Field(default=None, ge=-90, le=90, examples=[7.8449])
    longitude: float | None = Field(default=None, ge=-180, le=180, examples=[98.2952])


class PropertyOut(BaseModel):
    name: str = Field(examples=["บ้านพักริมเลกะรน"])
    address: str = Field(examples=["99/9 หมู่ 1 ถนนกะรน ..."])
    room_count: int = Field(examples=[6])
    max_guests: int = Field(examples=[24])
    has_restaurant: bool = Field(examples=[False])
    accommodation_kind: str | None = Field(default=None, examples=["detached_house"])
    accommodation_kind_other: str | None = Field(default=None, examples=[None])
    local_authority_name: str = Field(examples=["เทศบาลตำบลกะรน"])

    model_config = {"from_attributes": True}


class ApplicationOut(BaseModel):
    """หน้าคำขอหนึ่งใบ — ใช้ทั้งตอนเปิดคำขอและตอนเปิดดูภายหลัง"""

    application_no: str = Field(
        examples=["PKT-2569-000123"], description="เลขที่คำขอสำหรับใช้อ้างอิง (M6)"
    )
    status: str = Field(examples=["draft"])
    days_waiting: int = Field(examples=[0], description="อยู่ในสถานะนี้มากี่วันแล้ว (M7)")
    created_at: datetime = Field(examples=["2026-09-19T21:30:00+07:00"])
    submitted_at: datetime | None = Field(default=None, examples=[None])

    property_type_code: str = Field(examples=["not_hotel"])
    property_type_name: str = Field(examples=["ไม่เข้าข่ายโรงแรม"])
    requires_license: bool = Field(examples=[False])
    reason: str = Field(examples=["ที่พักของคุณมี 6 ห้อง และรับผู้เข้าพักได้ 24 คน ซึ่งไม่เกินเกณฑ์ยกเว้น ..."])
    matched_rule_code: str | None = Field(default=None, examples=["RULE-NOT-HOTEL"])

    fee: FeeOut | None = None
    property: PropertyOut
    documents: DocumentChecklistOut


class ApplicationSummaryOut(BaseModel):
    """แถวหนึ่งในหน้ารายการคำขอของผู้ยื่น"""

    application_no: str = Field(examples=["PKT-2569-000123"])
    status: str = Field(examples=["draft"])
    days_waiting: int = Field(examples=[0])
    property_name: str = Field(examples=["บ้านพักริมเลกะรน"])
    property_type_name: str = Field(examples=["ไม่เข้าข่ายโรงแรม"])
    created_at: datetime = Field(examples=["2026-09-19T21:30:00+07:00"])
