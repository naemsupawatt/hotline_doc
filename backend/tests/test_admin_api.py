"""ทดสอบหน้าตั้งค่าของ Super Admin (US-09)

เคสสำคัญที่สุดคือ test_changing_a_rule_changes_the_answer_without_touching_code
เพราะนั่นคือสิ่งที่โจทย์ข้อ 4 บังคับ และเป็นสิ่งที่กรรมการน่าจะขอให้สาธิต

ทุกเคสคืนค่าเดิมกลับหลังทดสอบเสร็จ เพราะกฎกับอัตราค่าธรรมเนียมเป็นข้อมูล
ที่ใช้ร่วมกันทั้งระบบ ถ้าปล่อยค้างไว้ เทสต์ไฟล์อื่นจะพังตามไปด้วย
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.db import SessionLocal
from app.main import app
from app.models.audit import AuditLog
from app.models.classification import ClassificationRule
from app.models.license import FeeSchedule
from app.models.user import User

RULES = "/api/v1/admin/classification-rules"
FEES = "/api/v1/admin/fee-schedules"
CLASSIFY = "/api/v1/wizard/classify"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def login(client: TestClient, email: str) -> dict:
    token = client.post(
        "/api/v1/auth/login", json={"identifier": email, "password": "demo1234"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin(client) -> dict:
    return login(client, "admin@example.com")


@pytest.fixture(autouse=True)
def restore_config():
    """คืนกฎและอัตราให้เหมือนเดิมหลังทุกเคส"""
    with SessionLocal() as db:
        rules = {
            r.code: (r.min_rooms, r.max_rooms, r.min_guests, r.max_guests, r.priority)
            for r in db.scalars(select(ClassificationRule)).all()
        }
        fee_ids = set(db.scalars(select(FeeSchedule.id)).all())
        fee_ends = {f.id: f.effective_to for f in db.scalars(select(FeeSchedule)).all()}

    yield

    with SessionLocal() as db:
        for rule in db.scalars(select(ClassificationRule)).all():
            if rule.code in rules:
                (
                    rule.min_rooms,
                    rule.max_rooms,
                    rule.min_guests,
                    rule.max_guests,
                    rule.priority,
                ) = rules[rule.code]
        db.execute(delete(FeeSchedule).where(FeeSchedule.id.not_in(fee_ids)))
        for fee in db.scalars(select(FeeSchedule)).all():
            fee.effective_to = fee_ends.get(fee.id)
        db.execute(delete(AuditLog).where(AuditLog.action.like("admin.%")))
        db.commit()


def classify(client, rooms: int, guests: int, restaurant: bool = False) -> dict:
    return client.post(
        CLASSIFY,
        json={"rooms": rooms, "guests": guests, "has_restaurant": restaurant},
    ).json()


def test_changing_a_rule_changes_the_answer_without_touching_code(client, admin):
    """โจทย์ข้อ 4: "แก้ไขเงื่อนไข... ได้ในภายหลังโดยไม่ต้องแก้โค้ด"

    นี่คือการสาธิต US-09 ทั้งดุ้น: ถามคำถามเดิมก่อนและหลังแก้เกณฑ์
    แล้วได้คำตอบต่างกัน โดยไม่มีการ deploy หรือแก้ไฟล์ใด ๆ
    """
    assert classify(client, 8, 36)["property_type_code"] == "type_1"

    updated = client.patch(f"{RULES}/RULE-NOT-HOTEL", headers=admin, json={"max_guests": 40})
    assert updated.status_code == 200, updated.text
    assert updated.json()["max_guests"] == 40

    after = classify(client, 8, 36)
    assert after["property_type_code"] == "not_hotel"
    assert after["matched_rule_code"] == "RULE-NOT-HOTEL"
    assert "40" in after["reason"] or "36" in after["reason"]


def test_rule_edit_is_recorded_in_the_audit_trail(client, admin):
    """เปลี่ยนเกณฑ์กระทบคำขอทุกใบที่จะเข้ามา ต้องรู้ว่าใครแก้อะไรเมื่อไร"""
    client.patch(f"{RULES}/RULE-NOT-HOTEL", headers=admin, json={"max_guests": 35})

    with SessionLocal() as db:
        admin_id = db.scalar(select(User.id).where(User.email == "admin@example.com"))
        logged = db.scalar(
            select(AuditLog)
            .where(AuditLog.actor_id == admin_id, AuditLog.action == "admin.rule_update")
            .order_by(AuditLog.id.desc())
        )
    assert logged is not None
    assert "30" in logged.detail and "35" in logged.detail, "ต้องบันทึกค่าก่อนและหลัง"


def test_rejects_values_that_would_break_the_rule(client, admin):
    """กันค่าที่ทำให้กฎไม่มีทางเข้าเงื่อนไขได้เลย

    ถ้าปล่อยผ่าน ผู้ใช้จริงจะเจอ "ไม่มีเกณฑ์สำหรับที่พักลักษณะนี้"
    โดยที่ผู้ดูแลระบบไม่รู้ตัวว่าทำพัง
    """
    res = client.patch(
        f"{RULES}/RULE-TYPE-1", headers=admin, json={"min_rooms": 100, "max_rooms": 49}
    )
    assert res.status_code == 422
    assert "ขั้นต่ำ" in res.json()["detail"]

    # ต้องไม่ถูกบันทึกลงฐานข้อมูลเลย
    assert classify(client, 20, 60)["property_type_code"] == "type_1"


def test_clearing_a_limit_means_unlimited(client, admin):
    """เว้นว่าง = ไม่จำกัดเงื่อนไขข้อนั้น ต่างจาก "ไม่ได้ส่งมา" ซึ่งแปลว่าไม่แก้"""
    res = client.patch(f"{RULES}/RULE-NOT-HOTEL", headers=admin, json={"clear": ["max_guests"]})
    assert res.status_code == 200
    assert res.json()["max_guests"] is None

    # ไม่จำกัดจำนวนคนแล้ว 8 ห้อง 500 คนจึงยังไม่เข้าข่าย
    assert classify(client, 8, 500)["property_type_code"] == "not_hotel"


def test_preview_does_not_save_anything(client, admin):
    before = classify(client, 8, 36)["property_type_code"]

    res = client.post(
        f"{RULES}/preview", headers=admin, json={"rooms": 8, "guests": 36, "has_restaurant": False}
    )
    assert res.status_code == 200
    assert res.json()["matched"] is True

    assert classify(client, 8, 36)["property_type_code"] == before


def test_changing_a_fee_adds_a_row_and_keeps_the_old_one(client, admin):
    """ข้อควรคิดข้อ 1 ของโจทย์ข้อ 8

    เปลี่ยนอัตราต้องไม่ทับแถวเดิม เพราะใบอนุญาตที่ออกไปแล้วชี้กลับมาที่แถวนั้น
    """
    fees = client.get(FEES, headers=admin).json()
    current = next(f for f in fees if f["property_type_code"] == "type_1" and f["is_current"])

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    res = client.post(
        f"{FEES}/{current['id']}/supersede",
        headers=admin,
        json={"amount": 12000, "validity_years": 5, "effective_from": tomorrow},
    )
    assert res.status_code == 201, res.text

    rows = [f for f in res.json() if f["property_type_code"] == "type_1"]
    assert len(rows) == 2, "อัตราเดิมต้องยังอยู่"

    old = next(f for f in rows if f["id"] == current["id"])
    new = next(f for f in rows if f["id"] != current["id"])
    assert old["amount"] == 10000.0, "อัตราเดิมต้องไม่ถูกแก้ตัวเลข"
    assert old["effective_to"] is not None, "อัตราเดิมต้องถูกปิดช่วงเวลา"
    assert new["amount"] == 12000.0


def test_fee_change_must_start_after_the_current_one(client, admin):
    fees = client.get(FEES, headers=admin).json()
    current = next(f for f in fees if f["is_current"])

    res = client.post(
        f"{FEES}/{current['id']}/supersede",
        headers=admin,
        json={
            "amount": 9000,
            "validity_years": 5,
            "effective_from": current["effective_from"],
        },
    )
    assert res.status_code == 422
    assert "หลังอัตราเดิม" in res.json()["detail"]


@pytest.mark.parametrize(
    "email", ["operator@example.com", "officer@example.com", "central@example.com"]
)
def test_only_super_admin_can_open_settings(client, email):
    assert client.get(RULES, headers=login(client, email)).status_code == 403


def test_settings_require_login(client):
    assert client.get(RULES).status_code == 401
