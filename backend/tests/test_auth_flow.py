"""ทดสอบเส้นทางสมัคร -> เข้าสู่ระบบ (M1)

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
from tests.test_thai_id import make_valid

TEST_EMAIL = "pytest-user@example.com"
TEST_ID = make_valid("390990123456")
# ต้องไม่ชนกับเบอร์ของบัญชีสาธิตใน seeds/users.py (08000000xx)
TEST_PHONE = "0899990001"
# เบอร์สำรองที่ใช้ตอนทดสอบเงื่อนไขอื่นซ้ำ — ต้องล้างทิ้งด้วย ไม่งั้นรันรอบถัดไปจะชน
SPARE_PHONES = ["0899990002", "0899990003", "0899990004"]


def payload(**overrides):
    base = {
        "first_name": "ทดสอบ",
        "last_name": "อัตโนมัติ",
        "national_id": TEST_ID,
        "phone": TEST_PHONE,
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
                    (User.email == TEST_EMAIL)
                    | (User.national_id == TEST_ID)
                    | (User.phone.in_([TEST_PHONE, *SPARE_PHONES]))
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


def test_register_then_login(client):
    created = client.post("/api/v1/auth/register", json=payload())
    assert created.status_code == 201, created.text
    # สมัครเสร็จได้ token ทันที ไม่มีขั้นยืนยันตัวตนคั่น
    assert created.json()["access_token"]

    ok = client.post("/api/v1/auth/login", json={"identifier": TEST_EMAIL, "password": "demo1234"})
    assert ok.status_code == 200


def test_login_with_phone_number(client):
    """M1 ระบุว่าเข้าสู่ระบบด้วย "หมายเลขโทรศัพท์หรืออีเมล" ได้ทั้งคู่

    หน้าเข้าสู่ระบบเขียน label ว่ารับเบอร์โทร เทสต์นี้กันไม่ให้ช่องทางนั้น
    กลายเป็นทางตันเวลาที่ผู้ใช้สมัครบัญชีใหม่เอง
    """
    assert client.post("/api/v1/auth/register", json=payload()).status_code == 201

    by_phone = client.post(
        "/api/v1/auth/login", json={"identifier": TEST_PHONE, "password": "demo1234"}
    )
    assert by_phone.status_code == 200, by_phone.text
    assert by_phone.json()["user"]["phone"] == TEST_PHONE


def test_login_accepts_phone_written_with_dashes(client):
    """เบอร์เก็บเป็นตัวเลขล้วน แต่ผู้ใช้พิมพ์มีขีดได้ ต้องหาเจอเป็นคนเดียวกัน"""
    client.post("/api/v1/auth/register", json=payload())

    dashed = client.post(
        "/api/v1/auth/login", json={"identifier": "089-999-0001", "password": "demo1234"}
    )
    assert dashed.status_code == 200, dashed.text


def test_duplicate_phone_rejected(client):
    """หนึ่งเบอร์ต่อหนึ่งบัญชี — ถ้าซ้ำได้ การเข้าสู่ระบบด้วยเบอร์จะกำกวมทันที"""
    assert client.post("/api/v1/auth/register", json=payload()).status_code == 201

    other = client.post(
        "/api/v1/auth/register",
        json=payload(email="another@example.com", national_id=make_valid("390990555444")),
    )
    assert other.status_code == 409
    assert "โทรศัพท์" in other.json()["detail"]


def test_wrong_password_rejected_after_register(client):
    client.post("/api/v1/auth/register", json=payload())
    res = client.post("/api/v1/auth/login", json={"identifier": TEST_EMAIL, "password": "wrong"})
    assert res.status_code == 401
    assert "access_token" not in res.text


@pytest.mark.parametrize(
    "overrides,field",
    [
        ({"national_id": "1100701234560"}, "เลขประจำตัวประชาชน"),
        ({"national_id": "123"}, "13 หลัก"),
        ({"phone": "08123"}, "หมายเลขโทรศัพท์"),
        ({"phone": "1812345678"}, "หมายเลขโทรศัพท์"),
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

    same_id = client.post(
        "/api/v1/auth/register",
        json=payload(email="other@example.com", phone="0899990002"),
    )
    assert same_id.status_code == 409
    assert "เลขประจำตัวประชาชน" in same_id.json()["detail"]


def test_national_id_never_returned_raw(client):
    res = client.post("/api/v1/auth/register", json=payload())
    assert TEST_ID not in res.text, "เลขบัตรเต็มต้องไม่หลุดออกไปกับ response"
    assert res.json()["user"]["national_id_masked"].startswith("x-xxxx")

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {res.json()['access_token']}"},
    )
    assert TEST_ID not in me.text


def test_duplicate_national_id_is_the_remaining_bot_guard(client):
    """หลังตัด OTP ออก กลไกกันบัญชีขยะที่เหลืออยู่คือเลขบัตรประชาชน

    หนึ่งเลขบัตรต่อหนึ่งบัญชี และเลขต้องผ่านหลักตรวจสอบ
    ทำให้สร้างบัญชีจำนวนมากด้วยเลขมั่ว ๆ ไม่ได้
    เทสต์นี้มีไว้เป็นหลักฐานตอนตอบกรรมการเรื่อง M1
    """
    assert client.post("/api/v1/auth/register", json=payload()).status_code == 201

    # เปลี่ยนทั้งอีเมลและเบอร์ เพื่อให้เหลือเลขบัตรเป็นเหตุผลเดียวที่ทำให้ถูกปฏิเสธ
    again = client.post(
        "/api/v1/auth/register",
        json=payload(email="someone-else@example.com", phone="0899990003"),
    )
    assert again.status_code == 409
    assert "เลขประจำตัวประชาชน" in again.json()["detail"]

    fake_id = client.post(
        "/api/v1/auth/register",
        json=payload(email="fake@example.com", phone="0899990004", national_id="1111111111111"),
    )
    assert fake_id.status_code == 422


# ---------------------------------------------------------------- บัญชีของฉัน


def auth_header(client, **overrides) -> dict:
    """สมัครแล้วคืน header ที่แนบโทเคนของบัญชีนั้น"""
    res = client.post("/api/v1/auth/register", json=payload(**overrides))
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_profile_shows_who_you_are_without_the_full_national_id(client):
    headers = auth_header(client)

    body = client.get("/api/v1/auth/me", headers=headers).json()

    assert body["full_name"] == "ทดสอบ อัตโนมัติ"
    assert body["email"] == TEST_EMAIL
    assert body["role"] == "operator"
    assert body["created_at"], "ต้องบอกว่าเปิดบัญชีเมื่อใด"
    assert body["national_id_masked"], "ต้องยืนยันได้ว่าผูกกับเลขบัตรใบไหน"
    assert TEST_ID not in str(body), "ห้ามส่งเลขบัตรเต็มออกจากระบบไม่ว่ากรณีใด"


def test_can_fix_your_own_name_and_contact(client):
    """คนกรอกชื่อผิดตอนสมัครต้องแก้เองได้ ไม่ใช่ต้องขอให้แก้ในฐานข้อมูลให้"""
    headers = auth_header(client)
    new_phone = SPARE_PHONES[0]

    res = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "first_name": "สมชาย",
            "last_name": "ใจดี",
            "email": TEST_EMAIL,
            "phone": f"{new_phone[:3]}-{new_phone[3:6]}-{new_phone[6:]}",
        },
    )

    assert res.status_code == 200, res.text
    assert res.json()["full_name"] == "สมชาย ใจดี"
    assert res.json()["phone"] == new_phone, "เบอร์ต้องถูกเก็บเป็นตัวเลขล้วนแม้ผู้ใช้ใส่ขีด"

    # เบอร์คือกุญแจเข้าสู่ระบบอีกทางหนึ่ง (M1) แก้แล้วต้องใช้เข้าได้จริง
    login = client.post(
        "/api/v1/auth/login", json={"identifier": new_phone, "password": "demo1234"}
    )
    assert login.status_code == 200


def test_cannot_take_an_email_that_belongs_to_someone_else(client):
    headers = auth_header(client)
    other_email = "pytest-user-other@example.com"
    client.post(
        "/api/v1/auth/register",
        json=payload(
            email=other_email,
            phone=SPARE_PHONES[1],
            national_id=make_valid("390990654321"),
        ),
    )

    res = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "first_name": "ทดสอบ",
            "last_name": "อัตโนมัติ",
            "email": other_email,
            "phone": TEST_PHONE,
        },
    )

    assert res.status_code == 409
    assert "อีเมล" in res.json()["detail"]


def test_profile_update_cannot_touch_role_or_national_id(client):
    """เลขบัตรคือกลไกกันบัญชีขยะที่เหลืออยู่ และไม่มีใครเลื่อนสิทธิ์ตัวเองได้"""
    headers = auth_header(client)
    before = client.get("/api/v1/auth/me", headers=headers).json()

    res = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "first_name": "ทดสอบ",
            "last_name": "อัตโนมัติ",
            "email": TEST_EMAIL,
            "phone": TEST_PHONE,
            "role": "super_admin",
            "national_id": make_valid("390990999999"),
        },
    )

    assert res.status_code == 200
    assert res.json()["role"] == "operator"
    assert res.json()["national_id_masked"] == before["national_id_masked"]


def test_changing_password_needs_the_current_one(client):
    headers = auth_header(client)

    wrong = client.post(
        "/api/v1/auth/me/password",
        headers=headers,
        json={"current_password": "ไม่ใช่รหัสนี้", "new_password": "hotline2569"},
    )
    assert wrong.status_code == 400
    assert "รหัสผ่านเดิม" in wrong.json()["detail"]

    # ความพยายามที่ล้มเหลวต้องถูกบันทึกไว้ เหมือนการล็อกอินไม่สำเร็จ
    with SessionLocal() as db:
        denied = db.scalar(
            select(AuditLog)
            .where(AuditLog.action == "password.change", AuditLog.outcome == "denied")
            .order_by(AuditLog.id.desc())
        )
    assert denied is not None

    ok = client.post(
        "/api/v1/auth/me/password",
        headers=headers,
        json={"current_password": "demo1234", "new_password": "hotline2569"},
    )
    assert ok.status_code == 204

    assert (
        client.post(
            "/api/v1/auth/login", json={"identifier": TEST_EMAIL, "password": "demo1234"}
        ).status_code
        == 401
    ), "รหัสเดิมต้องใช้ไม่ได้อีก"
    assert (
        client.post(
            "/api/v1/auth/login", json={"identifier": TEST_EMAIL, "password": "hotline2569"}
        ).status_code
        == 200
    )


def test_new_password_must_be_long_enough_and_different(client):
    headers = auth_header(client)

    short = client.post(
        "/api/v1/auth/me/password",
        headers=headers,
        json={"current_password": "demo1234", "new_password": "sun"},
    )
    assert short.status_code == 422
    assert "8 ตัวอักษร" in short.text

    same = client.post(
        "/api/v1/auth/me/password",
        headers=headers,
        json={"current_password": "demo1234", "new_password": "demo1234"},
    )
    assert same.status_code == 400
    assert "ซ้ำกับรหัสผ่านเดิม" in same.json()["detail"]
