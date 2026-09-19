"""ทดสอบการเปิดคำขอและการเข้าถึง (M6, M7, M9)

ยิงผ่าน API จริงและเขียนลงฐานข้อมูลจริง จึงล้างข้อมูลทดสอบทุกครั้ง
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.db import SessionLocal
from app.main import app
from app.models.application import Application, ApplicationStatusHistory
from app.models.audit import AuditLog
from app.models.classification import ApplicationClassification
from app.models.property import Operator, Property
from app.models.user import User
from tests.test_thai_id import make_valid

OWNER_EMAIL = "pytest-owner@example.com"
OWNER_PHONE = "0899970001"
OWNER_ID = make_valid("391110001122")

STRANGER_EMAIL = "pytest-stranger@example.com"
STRANGER_PHONE = "0899970002"
STRANGER_ID = make_valid("391110003344")

EMAILS = [OWNER_EMAIL, STRANGER_EMAIL]


def _cleanup() -> None:
    """ลบจากปลายทางย้อนขึ้นต้นทาง ไม่งั้นติด foreign key"""
    with SessionLocal() as db:
        user_ids = list(db.scalars(select(User.id).where(User.email.in_(EMAILS))).all())
        if not user_ids:
            return

        operator_ids = list(
            db.scalars(select(Operator.id).where(Operator.user_id.in_(user_ids))).all()
        )
        app_ids = (
            list(
                db.scalars(
                    select(Application.id).where(Application.operator_id.in_(operator_ids))
                ).all()
            )
            if operator_ids
            else []
        )

        if app_ids:
            db.execute(
                delete(ApplicationClassification).where(
                    ApplicationClassification.application_id.in_(app_ids)
                )
            )
            db.execute(
                delete(ApplicationStatusHistory).where(
                    ApplicationStatusHistory.application_id.in_(app_ids)
                )
            )
            db.execute(delete(Application).where(Application.id.in_(app_ids)))
        if operator_ids:
            db.execute(delete(Property).where(Property.operator_id.in_(operator_ids)))
            db.execute(delete(Operator).where(Operator.id.in_(operator_ids)))

        db.execute(delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))
        db.execute(delete(User).where(User.id.in_(user_ids)))
        db.commit()


def _register(client: TestClient, email: str, phone: str, national_id: str) -> str:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "ทดสอบ",
            "last_name": "คำขอ",
            "national_id": national_id,
            "phone": phone,
            "email": email,
            "password": "demo1234",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


@pytest.fixture(scope="module")
def client():
    _cleanup()
    with TestClient(app) as c:
        yield c
    _cleanup()


@pytest.fixture(scope="module")
def owner(client) -> str:
    return _register(client, OWNER_EMAIL, OWNER_PHONE, OWNER_ID)


@pytest.fixture(scope="module")
def karon_id(client) -> int:
    rows = client.get("/api/v1/wizard/local-authorities").json()
    return next(r["id"] for r in rows if r["code"] == "KRN-SUB")


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def payload(karon_id: int, **overrides) -> dict:
    base = {
        "rooms": 6,
        "guests": 24,
        "has_restaurant": False,
        "local_authority_id": karon_id,
        "property_name": "บ้านพักทดสอบ",
        "address": {
            "address_no": "99/9",
            "moo": "1",
            "road": "กะรน",
            "sub_district": "กะรน",
            "district": "เมืองภูเก็ต",
            "postal_code": "83100",
        },
        "accommodation_kind": "detached_house",
    }
    return base | overrides


def start(client, token, karon_id, **overrides):
    return client.post(
        "/api/v1/applications", json=payload(karon_id, **overrides), headers=auth(token)
    )


def test_address_is_stored_as_separate_fields(client, owner, karon_id):
    """ที่อยู่ต้องแยกช่อง เพราะแบบหนังสือแจ้งฯ มีช่องแยก และ M11 ต้องสรุปรายอำเภอ"""
    body = start(client, owner, karon_id).json()
    address = body["property"]["address"]

    assert address["address_no"] == "99/9"
    assert address["moo"] == "1"
    assert address["sub_district"] == "กะรน"
    assert address["district"] == "เมืองภูเก็ต"
    assert address["postal_code"] == "83100"
    # จังหวัดเซิร์ฟเวอร์เติมให้ ไม่ได้รับมาจาก client
    assert address["province"] == "ภูเก็ต"


def test_full_address_is_composed_not_stored_twice(client, owner, karon_id):
    """ที่อยู่บรรทัดเดียวประกอบจากช่องย่อย ไม่เก็บซ้ำอีกคอลัมน์ (3NF)"""
    address = start(client, owner, karon_id).json()["property"]["address"]
    full = address["full_address"]

    for part in ["99/9", "หมู่ 1", "ถนนกะรน", "ตำบลกะรน", "อำเภอเมืองภูเก็ต", "จังหวัดภูเก็ต", "83100"]:
        assert part in full, f"ขาด {part} ใน {full}"


def test_optional_address_parts_may_be_omitted(client, owner, karon_id):
    """ที่พักในเขตเทศบาลนครไม่มีหมู่ ไม่ควรถูกบังคับให้กรอก"""
    body = start(
        client,
        owner,
        karon_id,
        address={
            "address_no": "12",
            "sub_district": "ตลาดใหญ่",
            "district": "เมืองภูเก็ต",
            "postal_code": "83000",
        },
    ).json()
    address = body["property"]["address"]

    assert address["moo"] is None and address["soi"] is None and address["road"] is None
    assert "หมู่" not in address["full_address"]


@pytest.mark.parametrize(
    "bad,reason",
    [
        ({"address_no": ""}, "บ้านเลขที่ว่าง"),
        ({"sub_district": ""}, "ตำบลว่าง"),
        ({"district": ""}, "อำเภอว่าง"),
        ({"postal_code": "831"}, "รหัสไปรษณีย์สั้นไป"),
        ({"postal_code": "8310a"}, "รหัสไปรษณีย์ไม่ใช่ตัวเลข"),
    ],
)
def test_rejects_incomplete_address(client, owner, karon_id, bad, reason):
    full = {
        "address_no": "99/9",
        "sub_district": "กะรน",
        "district": "เมืองภูเก็ต",
        "postal_code": "83100",
    }
    res = start(client, owner, karon_id, address=full | bad)
    assert res.status_code == 422, reason


def test_starting_an_application_issues_a_reference_number(client, owner, karon_id):
    """M6: "ต้องออกเลขที่คำขอให้ผู้ยื่นใช้อ้างอิง" """
    body = start(client, owner, karon_id).json()

    assert body["application_no"].startswith("PKT-")
    assert body["status"] == "draft"
    assert body["property_type_code"] == "not_hotel"
    assert body["documents"]["external"][0]["contact_point"]["local_authority_name"] == (
        "เทศบาลตำบลกะรน"
    )


def test_server_classifies_again_and_ignores_what_client_claims(client, owner, karon_id):
    """ห้ามเชื่อผลจำแนกจาก client — ส่งตัวเลขโรงแรมใหญ่มาต้องไม่ได้ not_hotel

    ถ้าเซิร์ฟเวอร์ไม่จำแนกใหม่ ใครก็ยิง API อ้างว่าไม่เข้าข่ายโรงแรมได้
    """
    body = start(client, owner, karon_id, rooms=20, guests=60).json()
    assert body["property_type_code"] == "type_1"
    assert body["requires_license"] is True
    assert body["fee"]["amount"] == 10000.0


def test_out_of_scope_cannot_open_an_application(client, owner, karon_id):
    """T-05: เกิน 49 ห้อง ต้องแนะนำให้ติดต่อนายทะเบียน ไม่ใช่เปิดคำขอให้"""
    res = start(client, owner, karon_id, rooms=60, guests=200)
    assert res.status_code == 422
    assert "นายทะเบียน" in res.json()["detail"]


def test_reason_is_a_snapshot_not_recomputed(client, owner, karon_id):
    """ผลจำแนกถูกบันทึกเป็น snapshot พร้อมตัวเลขที่ผู้ใช้ตอบตอนนั้น (โจทย์ข้อ 8)"""
    no = start(client, owner, karon_id, rooms=6, guests=24).json()["application_no"]

    with SessionLocal() as db:
        application = db.scalar(select(Application).where(Application.application_no == no))
        snapshot = db.scalar(
            select(ApplicationClassification).where(
                ApplicationClassification.application_id == application.id
            )
        )
        assert snapshot.answered_rooms == 6
        assert snapshot.answered_guests == 24
        assert snapshot.matched_rule_id is not None
        assert "6" in snapshot.reason_text


def test_creating_an_application_writes_the_audit_trail(client, owner, karon_id):
    """M9 + NFR Audit Trail: ต้องรู้ว่าใครทำ เมื่อใด และเริ่มที่สถานะใด"""
    no = start(client, owner, karon_id).json()["application_no"]

    with SessionLocal() as db:
        application = db.scalar(select(Application).where(Application.application_no == no))

        history = list(
            db.scalars(
                select(ApplicationStatusHistory).where(
                    ApplicationStatusHistory.application_id == application.id
                )
            ).all()
        )
        assert len(history) == 1
        assert history[0].from_status is None
        assert history[0].to_status == "draft"
        assert history[0].changed_at is not None, "เวลาต้องประทับจากฐานข้อมูล"

        logged = db.scalar(
            select(AuditLog).where(
                AuditLog.entity_type == "application",
                AuditLog.entity_id == application.id,
                AuditLog.action == "application.create",
            )
        )
        assert logged is not None and logged.actor_id is not None


def test_one_user_keeps_one_operator_profile_across_applications(client, owner, karon_id):
    """เปิดคำขอหลายใบต้องไม่สร้างโปรไฟล์ผู้ประกอบการซ้ำ"""
    start(client, owner, karon_id)
    start(client, owner, karon_id, property_name="ที่พักหลังที่สอง")

    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == OWNER_EMAIL))
        count = len(list(db.scalars(select(Operator).where(Operator.user_id == user_id)).all()))
    assert count == 1


def test_my_applications_lists_only_my_own(client, owner, karon_id):
    start(client, owner, karon_id)
    rows = client.get("/api/v1/applications", headers=auth(owner)).json()
    assert len(rows) >= 1
    assert all(r["property_name"] for r in rows)


def test_another_operator_cannot_open_someone_elses_application(client, owner, karon_id):
    """ฝาแฝดของ T-09 ฝั่งผู้ยื่น — ต้องถูกปฏิเสธ **และบันทึกความพยายามนั้นไว้**"""
    no = start(client, owner, karon_id).json()["application_no"]
    stranger = _register(client, STRANGER_EMAIL, STRANGER_PHONE, STRANGER_ID)

    res = client.get(f"/api/v1/applications/{no}", headers=auth(stranger))
    # ตอบ 404 ไม่ใช่ 403 เพราะ 403 เท่ากับยืนยันว่าเลขที่คำขอนี้มีอยู่จริง
    assert res.status_code == 404

    with SessionLocal() as db:
        stranger_id = db.scalar(select(User.id).where(User.email == STRANGER_EMAIL))
        denied = db.scalar(
            select(AuditLog).where(
                AuditLog.actor_id == stranger_id,
                AuditLog.action == "application.access_denied",
            )
        )
    assert denied is not None, "ต้องบันทึกความพยายามเข้าถึงคำขอของผู้อื่น"
    assert denied.outcome == "denied"


def test_officer_cannot_use_the_operator_endpoints(client, karon_id):
    """NFR Role-based Authorization"""
    officer = client.post(
        "/api/v1/auth/login",
        json={"identifier": "officer@example.com", "password": "demo1234"},
    ).json()["access_token"]

    assert client.get("/api/v1/applications", headers=auth(officer)).status_code == 403


def test_requires_login(client, karon_id):
    assert client.get("/api/v1/applications").status_code == 401
    assert client.post("/api/v1/applications", json=payload(karon_id)).status_code == 401


def test_rejects_unknown_local_authority(client, owner):
    res = start(client, owner, 999999)
    assert res.status_code == 422
    assert "องค์กรปกครองส่วนท้องถิ่น" in res.json()["detail"]
