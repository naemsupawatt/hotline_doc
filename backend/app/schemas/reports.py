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


class DocumentBottleneckOut(BaseModel):
    """เอกสารหนึ่งฉบับ กับจำนวนคำขอที่ติดค้างอยู่ที่ฉบับนั้น

    ยังเป็นข้อมูลสรุปล้วนตามข้อกำหนดของหน้าส่วนกลาง — ไม่มีเลขที่คำขอ
    ไม่มีชื่อผู้ยื่น และไม่มีชื่อเจ้าหน้าที่ที่รับผิดชอบ
    """

    code: str = Field(examples=["A02"])
    name_th: str = Field(examples=["สำเนาทะเบียนบ้านผู้แจ้ง"])
    count: int = Field(examples=[7], description="จำนวนคำขอที่เอกสารฉบับนี้ยังไม่ได้ตรวจ")
    oldest_days: int = Field(examples=[12], description="ฉบับที่ค้างรอตรวจนานที่สุดกี่วัน")
    by_authority: list[BucketOut] = Field(
        default_factory=list,
        description="กระจายตัวตามท้องถิ่น เฉพาะเขตที่มีของค้างจริง เรียงจากมากไปน้อย",
    )


class MissingUploadOut(BaseModel):
    """เอกสารหนึ่งฉบับ กับจำนวนคำขอที่ผู้ยื่นยังไม่ได้แนบเข้ามา

    เป็นคู่แฝดของ DocumentBottleneckOut แต่มองอีกฝั่งของกระบวนการ:
    อันนั้นคือของที่ส่งมาแล้วค้างที่เจ้าหน้าที่ อันนี้คือของที่ยังไม่ถูกส่งมา
    """

    code: str = Field(examples=["A03"])
    name_th: str = Field(examples=["เอกสารสิทธิ์ที่ดิน"])
    count: int = Field(examples=[9], description="จำนวนคำขอที่ยังไม่ได้แนบเอกสารฉบับนี้")
    mandatory_count: int = Field(
        examples=[6],
        description=(
            "ในจำนวนนั้น เป็นคำขอที่เอกสารฉบับนี้บังคับกี่ใบ — แยกไว้เพราะเอกสาร"
            "ไม่บังคับบางฉบับตั้งใจให้ขาดได้ (เช่น ช่องแนบใน ร.ร.1 ที่บุคคลธรรมดาไม่มี)"
        ),
    )
    by_authority: list[BucketOut] = Field(
        default_factory=list,
        description="กระจายตัวตามท้องถิ่น เฉพาะเขตที่มีของขาดจริง เรียงจากมากไปน้อย",
    )


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
