"""US-09 — schema ของหน้าตั้งค่าสำหรับ Super Admin

ข้อมูลตัวอย่างเป็นข้อมูลสมมติ (กติกาข้อ 14)
"""

from datetime import date

from pydantic import BaseModel, Field


class RuleOut(BaseModel):
    """กฎจำแนกประเภทหนึ่งข้อ ตามที่เก็บอยู่ในฐานข้อมูลจริง"""

    code: str = Field(examples=["RULE-NOT-HOTEL"])
    property_type_code: str = Field(examples=["not_hotel"])
    property_type_name: str = Field(examples=["ไม่เข้าข่ายโรงแรม"])
    priority: int = Field(examples=[10], description="เลขน้อยตัดสินก่อน")

    min_rooms: int | None = Field(default=None, examples=[None])
    max_rooms: int | None = Field(default=None, examples=[8])
    min_guests: int | None = Field(default=None, examples=[None])
    max_guests: int | None = Field(default=None, examples=[30])
    requires_restaurant: bool | None = Field(
        default=None,
        examples=[None],
        description="true = ต้องมีห้องอาหาร, false = ต้องไม่มี, ว่าง = ไม่สนใจ",
    )

    reason_template: str = Field(
        examples=["ที่พักของคุณมี {rooms} ห้อง และรับผู้เข้าพักได้ {guests} คน ..."],
        description="ใส่ {rooms} {guests} {restaurant} ได้",
    )
    outcome_message: str = Field(examples=["ไม่ต้องขอใบอนุญาตโรงแรม แต่ต้อง..."])
    is_active: bool = Field(examples=[True])
    effective_from: date = Field(examples=["2026-09-19"])

    # เตือนก่อนแก้ — กฎนี้เคยตัดสินคำขอไปแล้วกี่ใบ
    applications_classified: int = Field(examples=[12])


class RuleUpdate(BaseModel):
    """ส่งมาเฉพาะช่องที่ต้องการแก้ ช่องที่ไม่ส่งจะไม่ถูกแตะ"""

    priority: int | None = Field(default=None, ge=1, examples=[10])
    min_rooms: int | None = Field(default=None, ge=0, examples=[None])
    max_rooms: int | None = Field(default=None, ge=0, examples=[8])
    min_guests: int | None = Field(default=None, ge=0, examples=[None])
    max_guests: int | None = Field(default=None, ge=0, examples=[30])
    requires_restaurant: bool | None = Field(default=None, examples=[None])
    reason_template: str | None = Field(default=None, min_length=1, examples=[None])
    outcome_message: str | None = Field(default=None, min_length=1, examples=[None])
    is_active: bool | None = Field(default=None, examples=[None])

    # ระบุช่องที่ตั้งใจล้างค่าให้เป็นว่าง เพราะ null เฉย ๆ แปลว่า "ไม่แก้ช่องนี้"
    clear: list[str] = Field(
        default_factory=list,
        examples=[["max_guests"]],
        description="ชื่อช่องที่ต้องการล้างให้เป็นค่าว่าง (ไม่จำกัดเงื่อนไขข้อนั้น)",
    )


class FeeOut(BaseModel):
    id: int = Field(examples=[1])
    property_type_code: str = Field(examples=["type_1"])
    property_type_name: str = Field(examples=["ที่พักแรม ประเภทที่ 1"])
    amount: float = Field(examples=[10000.0])
    currency: str = Field(examples=["THB"])
    validity_years: int = Field(examples=[5])
    effective_from: date = Field(examples=["2026-09-19"])
    effective_to: date | None = Field(default=None, examples=[None])
    is_current: bool = Field(examples=[True], description="เป็นอัตราที่มีผลอยู่ตอนนี้หรือไม่")
    note: str | None = Field(default=None)


class FeeSupersede(BaseModel):
    """เปลี่ยนอัตรา = เพิ่มแถวใหม่ ไม่ทับแถวเดิม (ข้อควรคิดข้อ 1 ของโจทย์ข้อ 8)"""

    amount: float = Field(ge=0, examples=[12000.0])
    validity_years: int = Field(ge=1, examples=[5])
    effective_from: date = Field(examples=["2027-01-01"])
    note: str | None = Field(default=None, max_length=500, examples=["ปรับตามระเบียบใหม่"])


class PreviewRequest(BaseModel):
    rooms: int = Field(ge=1, examples=[8])
    guests: int = Field(ge=1, examples=[36])
    has_restaurant: bool = Field(default=False, examples=[False])


class PreviewResult(BaseModel):
    """ผลลองจำแนกด้วยกฎปัจจุบัน ไม่บันทึกอะไรลงฐานข้อมูล"""

    matched: bool = Field(examples=[True])
    property_type_name: str | None = Field(default=None, examples=["ที่พักแรม ประเภทที่ 1"])
    reason: str | None = Field(default=None)
    rule_code: str | None = Field(default=None, examples=["RULE-TYPE-1"])
