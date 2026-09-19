"""M1 — schema ของการเข้าสู่ระบบ

ใส่ examples= ทุกช่องตามกฎของทีม เพราะ FastAPI เอาไปแสดงใน /docs
ซึ่งเป็น deliverable "เอกสาร API พร้อมตัวอย่าง request/response"
"""

from pydantic import BaseModel, Field


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


class UserOut(BaseModel):
    id: int
    full_name: str = Field(examples=["สมชาย ใจดี"])
    email: str | None = Field(default=None, examples=["operator@example.com"])
    phone: str | None = Field(default=None, examples=["0812345678"])
    role: str = Field(examples=["operator"])
    is_verified: bool = Field(examples=[True])

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIs..."])
    token_type: str = Field(default="bearer", examples=["bearer"])
    user: UserOut
