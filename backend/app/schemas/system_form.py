"""แบบฟอร์มที่ระบบกรอกให้ (A01 หนังสือแจ้งฯ / A06 แบบ ร.ร.1) — ข้อมูลหน้าพิมพ์

แยกจาก ApplicationOut ด้วยเหตุผลเดียวกับที่ LicenseOut แยกออกมา: หน้าพิมพ์
ต้องการข้อมูลผู้ยื่นซึ่งเป็นข้อมูลส่วนบุคคล หน้าติดตามคำขอไม่ต้องใช้
จึงไม่ควรส่งติดไปทุกครั้งที่เปิดหน้าคำขอ

ใช้ schema ตัวเดียวกับทั้งสองแบบฟอร์ม เพราะข้อมูลที่ต้องใช้เป็นชุดเดียวกัน
ต่างกันแค่การจัดหน้ากระดาษฝั่งหน้าเว็บ ถ้าแยกสอง schema จะต้องแก้สองที่ทุกครั้ง

ย้ำกฎของโปรเจกต์: ห้ามส่ง national_id ดิบ ใช้ national_id_masked เท่านั้น
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.application import PropertyOut
from app.schemas.wizard import FeeOut


class ApplicantIn(BaseModel):
    """ชื่อผู้ยื่นที่ปรากฏบนแบบฟอร์ม — แก้ได้ตราบที่คำขอยังไม่ถูกยื่น

    เก็บที่ตาราง operator ไม่ใช่ที่ app_user เพราะ "ผู้ประกอบการ" กับ "บัญชีผู้ใช้"
    เป็นคนละสิ่ง บัญชีหนึ่งอาจยื่นในนามนิติบุคคลที่ตัวเองเป็นกรรมการก็ได้
    """

    display_name: str = Field(
        min_length=1,
        max_length=160,
        examples=["บริษัท ภูเก็ตสเตย์ จำกัด"],
        description="ชื่อที่จะพิมพ์ลงบนแบบฟอร์ม — ชื่อบุคคล หรือชื่อนิติบุคคล",
    )
    is_juristic: bool = Field(default=False, examples=[False])
    juristic_reg_no: str | None = Field(
        default=None,
        max_length=20,
        examples=[None],
        description="เลขทะเบียนนิติบุคคล 13 หลัก บังคับเมื่อยื่นในนามนิติบุคคล",
    )


class ApplicantOut(ApplicantIn):
    """ผู้ยื่น — ช่อง "ข้าพเจ้า..." ในหัวแบบฟอร์ม"""

    national_id_masked: str | None = Field(
        default=None,
        examples=["3-92xx-xxxxx-xx-2"],
        description="เลขบัตรแบบปิดบัง — ระบบไม่ส่งเลขเต็มออกทาง API ทุกกรณี",
    )
    phone: str | None = Field(default=None, examples=["0899990001"])
    email: str | None = Field(default=None, examples=["somying@example.com"])


class SignatureOut(BaseModel):
    """ลายมือชื่อผู้ยื่น เก็บเป็นไฟล์รูปรุ่นหนึ่งของแบบฟอร์มนั้น

    ไม่ได้เก็บเป็นคอลัมน์ใน application เพราะเป็น "ไฟล์แนบของเอกสารฉบับหนึ่ง"
    เหมือนไฟล์อื่น จึงได้ระบบรุ่น (version) การตรวจของเจ้าหน้าที่
    และการย้อนดูไฟล์เดิมมาฟรีทั้งชุด
    """

    file_id: int = Field(examples=[42], description="ใช้กับ GET .../documents/file/{file_id}")
    version_no: int = Field(examples=[1], description="ลงลายมือชื่อใหม่ = รุ่นถัดไป ไม่ทับของเดิม")
    status: str = Field(examples=["uploaded"], description="สถานะการตรวจของเจ้าหน้าที่")
    signed_at: datetime = Field(examples=["2026-09-20T10:15:00+07:00"])


class FormAttachmentOut(BaseModel):
    """ช่องแนบที่อยู่ในตัวแบบฟอร์ม เช่น A07–A09 ในแบบ ร.ร.1

    หน้ากระดาษติ๊กให้จาก is_attached ไม่ได้เก็บช่องติ๊กไว้อีกคอลัมน์
    """

    code: str = Field(examples=["A07"])
    name_th: str = Field(examples=["หนังสือรับรองการจดทะเบียนนิติบุคคล"])
    is_mandatory: bool = Field(examples=[False])
    is_attached: bool = Field(examples=[False], description="แนบไฟล์แล้วหรือยัง")


class SystemFormOut(BaseModel):
    """ทุกอย่างที่หน้าพิมพ์แบบฟอร์มต้องใช้ ในการเรียกครั้งเดียว"""

    form_code: str = Field(examples=["A01"])
    title: str = Field(
        examples=["แบบหนังสือแจ้งสถานที่พักที่ไม่เป็นโรงแรม"],
        description="ชื่อแบบฟอร์มอ่านจากตารางเอกสาร ไม่ได้ hard-code ไว้ในโค้ด (US-09)",
    )
    application_no: str = Field(examples=["PKT-2569-000123"])
    status: str = Field(examples=["draft"])
    local_authority_name: str = Field(examples=["เทศบาลตำบลกะรน"], description="อปท. ที่ยื่นเรื่อง")
    filed_on: datetime | None = Field(
        default=None,
        examples=[None],
        description="วันที่ยื่น — ว่างตราบที่ยังเป็นร่าง หน้าพิมพ์จะเว้นเส้นประไว้",
    )

    property_type_name: str = Field(examples=["ไม่เข้าข่ายโรงแรม"])
    requires_license: bool = Field(examples=[False])
    fee: FeeOut | None = Field(default=None, description="ว่างเมื่อประเภทนี้ไม่มีค่าธรรมเนียม")

    applicant: ApplicantOut
    property: PropertyOut
    attachments: list[FormAttachmentOut] = Field(
        default_factory=list, description="ช่องแนบที่อยู่ในตัวแบบฟอร์ม (แบบ ร.ร.1 มี A07–A09)"
    )

    signature: SignatureOut | None = Field(
        default=None, description="ว่าง = ยังไม่ได้ลงลายมือชื่อ ซึ่งจะยื่นคำขอไม่ได้ (M6)"
    )
    can_sign: bool = Field(
        examples=[True],
        description="แก้ลายมือชื่อและชื่อผู้ยื่นได้เฉพาะตอนที่คำขอยังแก้ได้ (ร่าง หรือถูกตีกลับ)",
    )
