"""M10 — schema ของเอกสารสิทธิ์ที่พิมพ์ได้

ข้อมูลตัวอย่างเป็นข้อมูลสมมติ (กติกาข้อ 14)
"""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.application import PropertyOut


class LicenseOut(BaseModel):
    """ทุกอย่างที่หน้าพิมพ์ต้องใช้ รวมมาในก้อนเดียว

    หน้าพิมพ์ไม่ควรต้องยิงหลาย endpoint แล้วประกอบเอง
    เพราะถ้าเรียกไม่ครบจะพิมพ์เอกสารที่ข้อมูลขาดออกไป
    """

    # M10: "มีเลขอ้างอิงสำหรับตรวจสอบย้อนกลับ"
    license_no: str = Field(examples=["NR-2569-000042"])
    kind: str = Field(
        examples=["notice_receipt"],
        description="license = ใบอนุญาต, notice_receipt = หนังสือรับรองการแจ้ง",
    )
    title: str = Field(
        examples=["หนังสือรับรองการแจ้งสถานที่พักที่ไม่เป็นโรงแรม"],
        description="ชื่อเอกสารสำหรับพิมพ์บนหัวกระดาษ",
    )

    application_no: str = Field(examples=["PKT-2569-000123"])
    property_type_name: str = Field(examples=["ไม่เข้าข่ายโรงแรม"])
    holder_name: str = Field(examples=["สมชาย ใจดี"], description="ชื่อผู้ถือเอกสาร")

    issued_at: datetime = Field(examples=["2026-09-19T22:30:00+07:00"])
    valid_from: date = Field(examples=["2026-09-19"])
    valid_until: date | None = Field(
        default=None, examples=[None], description="ว่าง = ไม่มีกำหนดหมดอายุ"
    )
    is_expired: bool = Field(examples=[False])
    is_revoked: bool = Field(examples=[False])

    fee_amount: float | None = Field(default=None, examples=[None])
    fee_currency: str | None = Field(default=None, examples=[None])

    issued_by_name: str = Field(examples=["สมหญิง รักงาน"])
    has_issuer_signature: bool = Field(
        default=False,
        examples=[True],
        description="โหลดรูปได้ที่ GET /applications/{application_no}/license/signature",
    )
    local_authority_name: str = Field(examples=["เทศบาลตำบลกะรน"])
    property: PropertyOut
