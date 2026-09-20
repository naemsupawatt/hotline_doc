"""M1 — schema ของการสมัครสมาชิกและเข้าสู่ระบบ

ใส่ examples= ทุกช่องตามกฎของทีม เพราะ FastAPI เอาไปแสดงใน /docs
ซึ่งเป็น deliverable "เอกสาร API พร้อมตัวอย่าง request/response"

ข้อมูลตัวอย่างทั้งหมดเป็นข้อมูลสมมติ ไม่ใช่ของบุคคลจริง (กติกาข้อ 14)
"""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core import phone as phone_utils
from app.core import thai_id

# ตรวจรูปแบบอีเมลเอง แทนการใช้ EmailStr เพราะ EmailStr คืนข้อความผิดพลาดเป็นภาษาอังกฤษ
# ซึ่งขัดกับ NFR Usability
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")

MIN_PASSWORD_LENGTH = 8


# กฎการตรวจอยู่เป็นฟังก์ชันเพราะใช้ทั้งตอนสมัครและตอนแก้ข้อมูลบัญชี
# ถ้าเขียนซ้ำสองที่ วันหนึ่งกฎจะไม่ตรงกัน แล้วข้อมูลที่แก้ทีหลังจะหลุดกฎที่ตอนสมัครกันไว้


def clean_email(v: str) -> str:
    v = v.strip().lower()
    if not EMAIL_RE.match(v):
        raise ValueError("รูปแบบอีเมลไม่ถูกต้อง กรุณากรอกในรูปแบบ name@example.com")
    return v


def clean_phone(v: str) -> str:
    """เก็บเป็นตัวเลขล้วน เพื่อให้ค้นหาตอนเข้าสู่ระบบเจอไม่ว่าผู้ใช้จะใส่ขีดหรือไม่"""
    digits = phone_utils.normalize(v)
    if not phone_utils.is_valid(digits):
        raise ValueError("หมายเลขโทรศัพท์ไม่ถูกต้อง กรุณากรอกเบอร์มือถือ 10 หลัก เช่น 0812345678")
    return digits


def clean_person_name(v: str) -> str:
    v = v.strip()
    if any(ch.isdigit() for ch in v):
        raise ValueError("ชื่อและนามสกุลต้องไม่มีตัวเลข")
    return v


def check_password_length(v: str) -> str:
    if len(v) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"รหัสผ่านต้องมีอย่างน้อย {MIN_PASSWORD_LENGTH} ตัวอักษร")
    return v


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
    phone: str = Field(
        examples=["0812345678"],
        description="หมายเลขโทรศัพท์ (ใส่ขีดได้ ระบบตัดให้เอง) ใช้เข้าสู่ระบบได้เช่นเดียวกับอีเมล",
    )
    email: str = Field(max_length=160, examples=["somchai@example.com"])
    password: str = Field(
        max_length=128,
        examples=["demo1234"],
        description=f"อย่างน้อย {MIN_PASSWORD_LENGTH} ตัวอักษร",
    )

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        return clean_email(v)

    @field_validator("password")
    @classmethod
    def _password_length(cls, v: str) -> str:
        return check_password_length(v)

    @field_validator("first_name", "last_name")
    @classmethod
    def _no_digits(cls, v: str) -> str:
        return clean_person_name(v)

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

    @field_validator("phone")
    @classmethod
    def _valid_phone(cls, v: str) -> str:
        return clean_phone(v)


class UserOut(BaseModel):
    id: int
    full_name: str = Field(examples=["สมชาย ใจดี"])
    first_name: str = Field(examples=["สมชาย"])
    last_name: str = Field(examples=["ใจดี"])
    email: str | None = Field(default=None, examples=["somchai@example.com"])
    phone: str | None = Field(default=None, examples=["0812345678"])
    role: str = Field(examples=["operator"])

    # เลขบัตรออกไปแบบปิดบังเท่านั้น ห้ามเพิ่มฟิลด์ national_id ดิบลงใน schema นี้
    national_id_masked: str | None = Field(default=None, examples=["x-xxxx-xxxxx-45-1"])

    model_config = {"from_attributes": True}


class ProfileOut(UserOut):
    """ข้อมูลบัญชีฉบับเต็มสำหรับหน้า "บัญชีของฉัน"

    ต่อยอดจาก UserOut ไม่ได้สร้างชุดใหม่ เพื่อให้ฟิลด์ที่หน้าจออื่นใช้อยู่แล้ว
    (ชื่อ อีเมล บทบาท เลขบัตรแบบปิดบัง) ไม่มีวันเพี้ยนไปคนละแบบกับหน้านี้
    """

    created_at: datetime = Field(examples=["2026-09-19T09:00:00+07:00"])
    local_authorities: list[str] = Field(
        default_factory=list,
        examples=[["เทศบาลนครภูเก็ต"]],
        description="อปท. ที่เจ้าหน้าที่คนนี้รับผิดชอบ (T-09) บทบาทอื่นเป็นรายการว่าง",
    )


class ProfileUpdateRequest(BaseModel):
    """แก้ได้เฉพาะสิ่งที่เป็นของเจ้าของบัญชีเอง

    ไม่มี national_id เพราะหนึ่งเลขบัตรต่อหนึ่งบัญชีคือกลไกกันบัญชีขยะที่เหลืออยู่
    หลังทีมตัดสินใจไม่ทำ OTP (ดู services/auth.py) ถ้าแก้เองได้ กลไกนั้นหมดความหมาย
    ไม่มี role เพราะการเลื่อนสิทธิ์ตัวเองได้คือช่องโหว่ ไม่ใช่ฟีเจอร์
    """

    first_name: str = Field(min_length=1, max_length=80, examples=["สมชาย"])
    last_name: str = Field(min_length=1, max_length=80, examples=["ใจดี"])
    email: str = Field(max_length=160, examples=["somchai@example.com"])
    phone: str = Field(examples=["0812345678"])

    @field_validator("first_name", "last_name")
    @classmethod
    def _no_digits(cls, v: str) -> str:
        return clean_person_name(v)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        return clean_email(v)

    @field_validator("phone")
    @classmethod
    def _valid_phone(cls, v: str) -> str:
        return clean_phone(v)


class PasswordChangeRequest(BaseModel):
    """ต้องกรอกรหัสเดิมด้วยเสมอ

    โทเคนที่ถูกขโมยไปจะได้เปลี่ยนรหัสผ่านเพื่อยึดบัญชีไม่ได้ ถ้าไม่รู้รหัสเดิม
    """

    current_password: str = Field(min_length=1, max_length=128, examples=["demo1234"])
    new_password: str = Field(
        max_length=128,
        examples=["hotline2569"],
        description=f"อย่างน้อย {MIN_PASSWORD_LENGTH} ตัวอักษร",
    )

    @field_validator("new_password")
    @classmethod
    def _password_length(cls, v: str) -> str:
        return check_password_length(v)


class TokenResponse(BaseModel):
    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIs..."])
    token_type: str = Field(default="bearer", examples=["bearer"])
    user: UserOut
