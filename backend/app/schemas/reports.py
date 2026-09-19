"""M11 — schema ของรายงานภาพรวมส่วนกลาง

ทุกช่องเป็นตัวเลขรวม ไม่มีข้อมูลที่ระบุตัวผู้ยื่นหรือเจ้าหน้าที่รายคน
เพราะโจทย์กำหนดว่าส่วนกลาง "ดูภาพรวมโดยไม่ก้าวก่ายการพิจารณารายคำขอ"
"""

from pydantic import BaseModel, Field


class BucketOut(BaseModel):
    key: str = Field(examples=["not_hotel"])
    label: str = Field(examples=["ไม่เข้าข่ายโรงแรม"])
    count: int = Field(examples=[12])


class AuthorityRowOut(BaseModel):
    name: str = Field(examples=["เทศบาลตำบลกะรน"])
    total: int = Field(examples=[8])
    waiting_on_officer: int = Field(examples=[3], description="ค้างที่เจ้าหน้าที่")
    waiting_on_applicant: int = Field(examples=[1], description="ค้างที่ผู้ยื่น")
    finished: int = Field(examples=[4])
    longest_wait_days: int = Field(examples=[12], description="คำขอที่ค้างนานที่สุดในเขตนี้ (วัน)")


class OverviewOut(BaseModel):
    """ภาพรวมทั้งจังหวัด — M11

    แยก "ค้างที่เจ้าหน้าที่" ออกจาก "ค้างที่ผู้ยื่น" เพราะสองอย่างนี้
    นำไปสู่การแก้ปัญหาคนละแบบ ซึ่งคือสิ่งที่ส่วนกลางต้องตัดสินใจ
    """

    total: int = Field(examples=[120])
    draft: int = Field(examples=[10], description="ร่าง ยังไม่ยื่น")
    waiting_on_officer: int = Field(examples=[32])
    waiting_on_applicant: int = Field(examples=[18])
    finished: int = Field(examples=[70])
    rejected: int = Field(examples=[2])

    by_property_type: list[BucketOut]
    by_status: list[BucketOut]
    by_authority: list[AuthorityRowOut]
