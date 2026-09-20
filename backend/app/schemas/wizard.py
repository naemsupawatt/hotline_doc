"""M2/M3/M4 — schema ของระบบนำทางแบบถามตอบ

ใส่ examples= ทุกช่องตามกฎของทีม เพราะ FastAPI เอาไปแสดงใน /docs
ซึ่งเป็น deliverable "เอกสาร API พร้อมตัวอย่าง request/response"

ข้อมูลตัวอย่างทั้งหมดเป็นข้อมูลสมมติ (กติกาข้อ 14)
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import DocumentStatus

# เพดานที่รับได้ของช่องกรอก — ไม่ใช่เกณฑ์จำแนกประเภท
# เกณฑ์จำแนกอยู่ในตาราง classification_rule เท่านั้น ห้ามเอามาไว้ที่นี่
MAX_ROOMS_INPUT = 9999
MAX_GUESTS_INPUT = 99999


class WizardAnswers(BaseModel):
    """คำถามสามข้อที่ตารางข้อ 4 ใช้ตัดสิน"""

    rooms: int = Field(
        ge=1,
        le=MAX_ROOMS_INPUT,
        examples=[6],
        description="จำนวนห้องพักทั้งหมด",
    )
    guests: int = Field(
        ge=1,
        le=MAX_GUESTS_INPUT,
        examples=[24],
        description="จำนวนผู้เข้าพักสูงสุดที่รับได้",
    )
    has_restaurant: bool = Field(
        default=False,
        examples=[False],
        description="มีห้องอาหารในสถานที่หรือไม่",
    )
    local_authority_id: int | None = Field(
        default=None,
        examples=[5],
        description=(
            "อปท. ที่ที่พักตั้งอยู่ — ไม่บังคับตอนประเมิน "
            "แต่ต้องมีจึงจะบอกได้ว่าเอกสารหมวดขอจากหน่วยงานอื่นต้องไปติดต่อที่ใด (M4)"
        ),
    )


class FeeOut(BaseModel):
    amount: float = Field(examples=[10000.0])
    currency: str = Field(examples=["THB"])
    validity_years: int = Field(examples=[5])


class ContactPointOut(BaseModel):
    """M4: ต้องไปติดต่อหน่วยงานใด ที่ท้องถิ่นใด ใช้เวลาเท่าใด"""

    agency_name: str = Field(examples=["กองช่าง องค์กรปกครองส่วนท้องถิ่น"])
    local_authority_name: str | None = Field(default=None, examples=["เทศบาลตำบลกะรน"])
    office_name: str = Field(examples=["กองช่าง เทศบาลตำบลกะรน"])
    address: str | None = Field(default=None, examples=["ถนนกะรน ตำบลกะรน อำเภอเมืองภูเก็ต"])
    phone: str | None = Field(default=None, examples=["076-000-001"])
    office_hours: str | None = Field(default=None, examples=["จันทร์–ศุกร์ 08.30–16.30 น."])
    map_url: str | None = Field(
        default=None,
        examples=["https://www.google.com/maps/place/?q=place_id:ChIJn1ylaRoyUDARDsI7B08fRHM"],
        description="ลิงก์แผนที่ของสำนักงานที่ต้องไปติดต่อ ว่างได้ถ้ายังไม่ได้ปักหมุดไว้",
    )
    estimated_days: int | None = Field(default=None, examples=[30])
    notes: str | None = Field(default=None, examples=["ควรโทรนัดหมายล่วงหน้า"])


class UploadedFileOut(BaseModel):
    """ไฟล์หนึ่งรุ่นที่แนบไว้ — แสดงเฉพาะรุ่นปัจจุบันของแต่ละ slot"""

    id: int = Field(examples=[12])
    slot_no: int = Field(examples=[1], description="ลำดับไฟล์ในเอกสารชนิดเดียวกัน")
    version_no: int = Field(examples=[1], description="รุ่นของไฟล์นี้ (ส่งซ้ำ = รุ่นใหม่)")
    original_name: str = Field(examples=["tabien-baan.pdf"])
    size_bytes: int = Field(examples=[248_000])
    mime_type: str = Field(examples=["application/pdf"])
    uploaded_at: datetime = Field(examples=["2026-09-19T22:10:00+07:00"])


class DocumentOut(BaseModel):
    code: str = Field(examples=["B01"])
    name_th: str = Field(examples=["ใบอนุญาตก่อสร้างอาคาร (อ.1)"])
    description: str | None = Field(default=None)
    is_mandatory: bool = Field(examples=[True])

    # หน้าจอใช้ตัดสินว่าจะขึ้นปุ่ม "กรอกแบบฟอร์ม" หรือ "เลือกไฟล์"
    is_system_form: bool = Field(examples=[False])
    allows_multiple: bool = Field(examples=[False])
    accepted_mime: list[str] = Field(examples=[["application/pdf"]])

    # เอกสารย่อยที่แนบอยู่ใต้แบบฟอร์มอีกฉบับ เช่น ช่องแนบในแบบ ร.ร.1
    # หน้าจอใช้จัดกลุ่มให้แสดงซ้อน ไม่ใช่ลอยเป็นรายการแยก
    parent_code: str | None = Field(default=None, examples=[None])

    # สถานะรายฉบับ ตรงกับ legend 7 สถานะในแบบหน้าจอ
    status: str = Field(default=DocumentStatus.NOT_UPLOADED, examples=["not_uploaded"])
    files: list[UploadedFileOut] = Field(default_factory=list, description="ไฟล์รุ่นปัจจุบันของแต่ละ slot")

    # M4 — มีเฉพาะเอกสารหมวดที่ต้องขอจากหน่วยงานอื่น
    preparation_note: str | None = Field(
        default=None,
        examples=["เตรียมไปที่หน่วยงาน: สำเนาบัตรประจำตัวประชาชน, สำเนาทะเบียนบ้าน, ..."],
    )
    estimated_days: int | None = Field(default=None, examples=[30])
    contact_point: ContactPointOut | None = None


class DocumentChecklistOut(BaseModel):
    """M3: "แบ่งออกเป็น 2 หมวดชัดเจน" — แยกให้แล้วตั้งแต่ชั้น API
    หน้าจอจึงไม่ต้องรู้กติกาการแบ่ง แค่วาดสองกล่อง
    """

    self_service: list[DocumentOut] = Field(description="ผู้ประกอบการทำเองได้")
    external: list[DocumentOut] = Field(description="ต้องขอจากหน่วยงานอื่น")
    needs_local_authority: bool = Field(
        examples=[False],
        description=(
            "true = มีเอกสารที่ต้องขอจากหน่วยงานอื่น แต่ผู้ใช้ยังไม่ได้เลือก อปท. หน้าจอต้องให้เลือกก่อนจึงจะบอกจุดติดต่อได้"
        ),
    )
    max_upload_mb: int = Field(
        examples=[10],
        description="ขนาดไฟล์สูงสุดต่อหนึ่งไฟล์ — อ่านจากค่าตั้งของเซิร์ฟเวอร์ ไม่ให้หน้าจอเดาเอง",
    )


class ClassifyResult(BaseModel):
    """ผลจำแนก — M2 บังคับให้มี "เหตุผลว่าทำไมจึงได้ผลนั้น" ไม่ใช่แค่ชื่อประเภท"""

    property_type_code: str = Field(examples=["not_hotel"])
    property_type_name: str = Field(examples=["ไม่เข้าข่ายโรงแรม"])
    requires_license: bool = Field(examples=[False])
    is_out_of_scope: bool = Field(examples=[False])

    reason: str = Field(
        examples=[
            "ที่พักของคุณมี 6 ห้อง และรับผู้เข้าพักได้ 24 คน "
            "ซึ่งไม่เกินเกณฑ์ยกเว้น (ไม่เกิน 8 ห้อง และไม่เกิน 30 คน) ทั้งสองข้อ"
        ]
    )
    outcome_message: str = Field(
        examples=["ไม่ต้องขอใบอนุญาตโรงแรม แต่ต้องดำเนินการแจ้งตามแนวทางที่กำหนด ..."]
    )

    # ชี้กลับไปยังกฎที่ใช้ตัดสิน — ใช้สาธิต US-09 ว่าผลมาจากข้อมูลใน DB จริง
    matched_rule_code: str | None = Field(default=None, examples=["RULE-NOT-HOTEL"])

    fee: FeeOut | None = None
    documents: DocumentChecklistOut


class LocalAuthorityOut(BaseModel):
    id: int = Field(examples=[5])
    code: str = Field(examples=["KRN-SUB"])
    name: str = Field(examples=["เทศบาลตำบลกะรน"])
    kind: str = Field(examples=["เทศบาลตำบล"])
    district: str = Field(examples=["เมืองภูเก็ต"])

    model_config = {"from_attributes": True}
