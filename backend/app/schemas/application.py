"""M6/M7 — schema ของการเปิดคำขอและติดตามสถานะ

ใส่ examples= ทุกช่องตามกฎของทีม (FastAPI เอาไปแสดงใน /docs)
ข้อมูลตัวอย่างเป็นข้อมูลสมมติ (กติกาข้อ 14)
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AccommodationKind
from app.schemas.wizard import DocumentChecklistOut, FeeOut

# ระบบนี้รับเฉพาะจังหวัดภูเก็ตตามขอบเขตของโจทย์
# เก็บค่าไว้ที่เดียวตรงนี้ ไม่กระจายเป็น literal ตามไฟล์ต่าง ๆ
DEFAULT_PROVINCE = "ภูเก็ต"

POSTAL_CODE_PATTERN = r"^\d{5}$"


class AddressIn(BaseModel):
    """ที่อยู่แยกช่องตามแบบหนังสือแจ้งสถานที่พักที่ไม่เป็นโรงแรม

    ไม่รับ "จังหวัด" จาก client — เซิร์ฟเวอร์เติมให้เป็นภูเก็ตเสมอ
    เพราะเป็นขอบเขตของระบบ ไม่ใช่สิ่งที่ผู้ใช้เลือกได้
    """

    address_no: str = Field(min_length=1, max_length=40, examples=["99/9"], description="บ้านเลขที่")
    moo: str | None = Field(default=None, max_length=20, examples=["1"], description="หมู่ที่")
    soi: str | None = Field(default=None, max_length=80, examples=[None], description="ซอย")
    road: str | None = Field(
        default=None, max_length=80, examples=["กะรน"], description="ถนน (ไม่ต้องใส่คำว่า ถนน)"
    )
    sub_district: str = Field(min_length=1, max_length=80, examples=["กะรน"], description="ตำบล")
    district: str = Field(min_length=1, max_length=80, examples=["เมืองภูเก็ต"], description="อำเภอ")
    postal_code: str = Field(
        pattern=POSTAL_CODE_PATTERN, examples=["83100"], description="รหัสไปรษณีย์ 5 หลัก"
    )


class AddressOut(AddressIn):
    province: str = Field(examples=[DEFAULT_PROVINCE])
    full_address: str = Field(
        examples=["99/9 หมู่ 1 ถนนกะรน ตำบลกะรน อำเภอเมืองภูเก็ต จังหวัดภูเก็ต 83100"],
        description="ที่อยู่บรรทัดเดียว ประกอบจากช่องย่อย ไม่ได้เก็บซ้ำในฐานข้อมูล",
    )


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
    address: AddressIn
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
    address: AddressOut
    room_count: int = Field(examples=[6])
    max_guests: int = Field(examples=[24])
    has_restaurant: bool = Field(examples=[False])
    accommodation_kind: str | None = Field(default=None, examples=["detached_house"])
    accommodation_kind_other: str | None = Field(default=None, examples=[None])
    local_authority_name: str = Field(examples=["เทศบาลตำบลกะรน"])

    model_config = {"from_attributes": True}


class MissingDocumentOut(BaseModel):
    """เอกสารบังคับที่ยังขาด — T-06 บังคับให้ระบุชัดว่าขาดฉบับใด"""

    code: str = Field(examples=["A02"])
    name_th: str = Field(examples=["สำเนาทะเบียนบ้านผู้แจ้ง"])


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

    # M10: มีค่าเมื่อเจ้าหน้าที่ออกเอกสารแล้ว หน้าจอใช้ขึ้นปุ่ม "พิมพ์เอกสาร"
    license_no: str | None = Field(default=None, examples=[None])

    # M6: หน้าจอใช้สองค่านี้ตัดสินว่าจะเปิดปุ่ม "ยื่นคำขอ" หรือไม่
    # และถ้ายังยื่นไม่ได้ ต้องบอกให้ครบว่าขาดอะไร ไม่ใช่แค่ทำปุ่มเป็นสีเทา
    can_submit: bool = Field(examples=[False])
    missing_documents: list[MissingDocumentOut] = Field(default_factory=list)


class ApplicationSummaryOut(BaseModel):
    """แถวหนึ่งในหน้ารายการคำขอของผู้ยื่น"""

    application_no: str = Field(examples=["PKT-2569-000123"])
    status: str = Field(examples=["draft"])
    days_waiting: int = Field(examples=[0])
    property_name: str = Field(examples=["บ้านพักริมเลกะรน"])
    property_type_name: str = Field(examples=["ไม่เข้าข่ายโรงแรม"])
    created_at: datetime = Field(examples=["2026-09-19T21:30:00+07:00"])
