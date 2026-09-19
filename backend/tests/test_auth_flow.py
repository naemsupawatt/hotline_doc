"""ทดสอบเส้นทางสมัคร -> ยืนยันตัวตน -> เข้าสู่ระบบ (M1)

ใช้ TestClient ยิงผ่าน API จริงและเขียนลงฐานข้อมูลจริง
จึงล้างผู้ใช้ทดสอบทิ้งทุกครั้งก่อนและหลังรัน
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.db import SessionLocal
from app.main import app
from app.models.audit import AuditLog
from app.models.user import User
from app.services.auth import DEMO_OTP
from tests.test_thai_id import make_valid

TEST_EMAIL = "pytest-user@example.com"
TEST_ID = make_valid("390990123456")


def payload(**overrides):
    base = {
        "first_name": "ทดสอบ",
        "last_name": "อัตโนมัติ",
        "national_id": TEST_ID,
        "birth_date": "1992-07-21",
        "email": TEST_EMAIL,
        "password": "demo1234",
    }
    return base | overrides


@pytest.fixture
def client():
    def cleanup():
        """ลบ AuditLog ก่อนเสมอ — audit_log.actor_id อ้างถึง app_user
        ถ้าลบผู้ใช้ก่อนจะติด foreign key constraint ทันที
        """
        with SessionLocal() as db:
            ids = db.scalars(
                select(User.id).where(
                    (User.email == TEST_EMAIL) | (User.national_id == TEST_ID)
                )
            ).all()
            if ids:
                db.execute(delete(AuditLog).where(AuditLog.actor_id.in_(ids)))
                db.execute(delete(User).where(User.id.in_(ids)))
            db.commit()

    cleanup()
    with TestClient(app) as c:
        yield c
    cleanup()


def test_register_then_verify_then_login(client):
    created = client.post("/api/v1/auth/register", json=payload())
    assert created.status_code == 201, created.text

    # M1: ยังเข้าระบบไม่ได้จนกว่าจะยืนยันตัวตน
    blocked = client.post(
        "/api/v1/auth/login", json={"identifier": TEST_EMAIL, "password": "demo1234"}
    )
    assert blocked.status_code == 401
    assert "ยืนยันตัวตน" in blocked.json()["detail"]

    verified = client.post(
        "/api/v1/auth/verify-otp", json={"email": TEST_EMAIL, "code": DEMO_OTP}
    )
    assert verified.status_code == 200
    assert verified.json()["user"]["is_verified"] is True

    ok = client.post("/api/v1/auth/login", json={"identifier": TEST_EMAIL, "password": "demo1234"})
    assert ok.status_code == 200


def test_verified_account_cannot_mint_token_with_wrong_otp(client):
    """กันบั๊กที่เคยเกิด: บัญชีที่ยืนยันแล้วเคยได้ token กลับมาแม้กรอกรหัสผิด

    ใครที่รู้อีเมลก็จะยิง endpoint นี้แล้วได้สิทธิ์เข้าระบบไปเลย
    """
    client.post("/api/v1/auth/register", json=payload())
    client.post("/api/v1/auth/verify-otp", json={"email": TEST_EMAIL, "code": DEMO_OTP})

    res = client.post("/api/v1/auth/verify-otp", json={"email": TEST_EMAIL, "code": "999999"})
    assert res.status_code == 400
    assert "access_token" not in res.text


def test_wrong_otp_is_rejected(client):
    client.post("/api/v1/auth/register", json=payload())
    res = client.post("/api/v1/auth/verify-otp", json={"email": TEST_EMAIL, "code": "000000"})
    assert res.status_code == 400
    assert "access_token" not in res.text


@pytest.mark.parametrize(
    "overrides,field",
    [
        ({"national_id": "1100701234560"}, "เลขประจำตัวประชาชน"),
        ({"national_id": "123"}, "13 หลัก"),
        ({"birth_date": "2099-01-01"}, "วันเดือนปีเกิด"),
        ({"password": "sml"}, "รหัสผ่าน"),
        ({"email": "not-an-email"}, "อีเมล"),
        ({"first_name": "ชื่อ1"}, "ตัวเลข"),
    ],
)
def test_validation_messages_are_thai(client, overrides, field):
    res = client.post("/api/v1/auth/register", json=payload(**overrides))
    assert res.status_code == 422
    assert field in res.text, res.text


def test_duplicate_email_and_national_id_rejected(client):
    assert client.post("/api/v1/auth/register", json=payload()).status_code == 201

    other_id = make_valid("390990999888")
    same_email = client.post("/api/v1/auth/register", json=payload(national_id=other_id))
    assert same_email.status_code == 409
    assert "อีเมล" in same_email.json()["detail"]

    same_id = client.post("/api/v1/auth/register", json=payload(email="other@example.com"))
    assert same_id.status_code == 409
    assert "เลขประจำตัวประชาชน" in same_id.json()["detail"]


def test_national_id_never_returned_raw(client):
    client.post("/api/v1/auth/register", json=payload())
    res = client.post("/api/v1/auth/verify-otp", json={"email": TEST_EMAIL, "code": DEMO_OTP})
    assert TEST_ID not in res.text, "เลขบัตรเต็มต้องไม่หลุดออกไปกับ response"
    assert res.json()["user"]["national_id_masked"].startswith("x-xxxx")
