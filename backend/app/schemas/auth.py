"""M1 — schema ของการสมัครสมาชิกและเข้าสู่ระบบ

ใส่ examples= ทุกช่องตามกฎของทีม เพราะ FastAPI เอาไปแสดงใน /docs
ซึ่งเป็น deliverable "เอกสาร API พร้อมตัวอย่าง request/response"

ข้อมูลตัวอย่างทั้งหมดเป็นข้อมูลสมมติ ไม่ใช่ของบุคคลจริง (กติกาข้อ 14)
"""

import re
from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.core import thai_id

# อายุมากที่สุดที่ยังถือว่าสมเหตุสมผล — กันปีเกิดที่พิมพ์ผิดจนเป็นไปไม่ได้
# หมายเหตุ: ไม่ได้บังคับอายุขั้นต่ำ เพราะโจทย์ไม่ได้กำหนดไว้
# ถ้าภายหลังต้องการบังคับผู้ยื่นอายุ 18 ปีขึ้นไป ให้เพิ่มเงื่อนไขใน _sane_birth_date
MAX_AGE_YEARS = 120

# ตรวจรูปแบบอีเมลเอง แทนการใช้ EmailStr เพราะ EmailStr คืนข้อความผิดพลาดเป็นภาษาอังกฤษ
# ซึ่งขัดกับ NFR Usability  ความถูกต้องจริงของอีเมลยืนยันด้วย OTP อยู่แล้ว
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

MIN_PASSWORD_LENGTH = 8


class LoginRequest(BaseModel):
    # รับได้ทั้งอีเมลและเบอร์โทรตาม M1 "ช่องทางที่เข้าถึงง่าย"
    # จึงไม่ใช้ EmailStr ที่จะบล็อกเบอร์โทรทิ้งไปเลย
    identifier: str = Field(
        min_length=3,
        max_length=160,
        examples=["operator@example.com", "0812345678"],
        description="อีเมลหรือหมายเลขโทรศัพท์",
    )
    password: str = Field(min_length=1, max_length=128, examples=["demo1234"])


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80, examples=["สมชาย"])
    last_name: str = Field(min_length=1, max_length=80, examples=["ใจดี"])
    national_id: str = Field(
        examples=["1100701234561"],
        description="เลขประจำตัวประชาชน 13 หลัก (ใส่ขีดได้ ระบบตัดให้เอง)",
    )
    birth_date: date = Field(examples=["1990-05-12"], description="วันเดือนปีเกิด (ค.ศ.)")
    email: str = Field(max_length=160, examples=["somchai@example.com"])
    password: str = Field(
        max_length=128,
        examples=["demo1234"],
        description=f"อย่างน้อย {MIN_PASSWORD_LENGTH} ตัวอักษร",
    )

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("รูปแบบอีเมลไม่ถูกต้อง กรุณากรอกในรูปแบบ name@example.com")
        return v

    @field_validator("password")
    @classmethod
    def _password_length(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(f"รหัสผ่านต้องมีอย่างน้อย {MIN_PASSWORD_LENGTH} ตัวอักษร")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def _no_digits(cls, v: str) -> str:
        v = v.strip()
        if any(ch.isdigit() for ch in v):
            raise ValueError("ชื่อและนามสกุลต้องไม่มีตัวเลข")
        return v

    @field_validator("national_id")
    @classmethod
    def _valid_national_id(cls, v: str) -> str:
        digits = thai_id.normalize(v)
        if len(digits) != 13:
            raise ValueError("เลขประจำตัวประชาชนต้องมี 13 หลัก")
        if not thai_id.is_valid(digits):
            # ข้อความนี้ผู้ใช้ทั่วไปต้องเข้าใจ — NFR Usability
            raise ValueError("เลขประจำตัวประชาชนไม่ถูกต้อง กรุณาตรวจสอบตัวเลขอีกครั้ง")
        return digits

    @field_validator("birth_date")
    @classmethod
    def _sane_birth_date(cls, v: date) -> date:
        today = date.today()
        if v >= today:
            raise ValueError("วันเดือนปีเกิดต้องเป็นวันที่ผ่านมาแล้ว")
        if (today - v).days > MAX_AGE_YEARS * 365.25:
            raise ValueError("วันเดือนปีเกิดไม่ถูกต้อง กรุณาตรวจสอบปีเกิดอีกครั้ง")
        return v


class VerifyOtpRequest(BaseModel):
    email: str = Field(max_length=160, examples=["somchai@example.com"])
    code: str = Field(min_length=6, max_length=6, examples=["123456"])


class UserOut(BaseModel):
    id: int
    full_name: str = Field(examples=["สมชาย ใจดี"])
    first_name: str = Field(examples=["สมชาย"])
    last_name: str = Field(examples=["ใจดี"])
    email: str | None = Field(default=None, examples=["somchai@example.com"])
    phone: str | None = Field(default=None, examples=["0812345678"])
    role: str = Field(examples=["operator"])
    is_verified: bool = Field(examples=[True])

    # เลขบัตรออกไปแบบปิดบังเท่านั้น ห้ามเพิ่มฟิลด์ national_id ดิบลงใน schema นี้
    national_id_masked: str | None = Field(default=None, examples=["x-xxxx-xxxxx-45-1"])

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIs..."])
    token_type: str = Field(default="bearer", examples=["bearer"])
    user: UserOut


class RegisterResponse(BaseModel):
    """ยังไม่คืน token เพราะต้องยืนยันตัวตนก่อน (M1)"""

    email: str = Field(examples=["somchai@example.com"])
    message: str = Field(examples=["สมัครสมาชิกสำเร็จ กรุณายืนยันตัวตนด้วยรหัส 6 หลัก"])
    demo_code: str | None = Field(
        default=None,
        examples=["123456"],
        description="เฉพาะโหมดสาธิต — ระบบจริงต้องส่งรหัสทางอีเมล/SMS ไม่ใช่คืนมาทาง API",
    )
