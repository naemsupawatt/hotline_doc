"""ทดสอบ endpoint ของ wizard ผ่าน API จริง (M2, M3, M4)

ต่างจาก test_classification_rules.py ที่ทดสอบ "กฎ" ระดับโมเดล
ไฟล์นี้ทดสอบสิ่งที่ผู้ใช้ได้รับจริงจากปลายทาง API: ประเภท + เหตุผล +
ค่าธรรมเนียม + รายการเอกสาร 2 หมวด + จุดติดต่อตามเขต
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.main import app
from app.models.classification import ApplicationClassification
from app.models.property import Property

CLASSIFY = "/api/v1/wizard/classify"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def karon_id(client) -> int:
    rows = client.get("/api/v1/wizard/local-authorities").json()
    return next(r["id"] for r in rows if r["code"] == "KRN-SUB")


def ask(client, rooms, guests, restaurant=False, authority=None):
    res = client.post(
        CLASSIFY,
        json={
            "rooms": rooms,
            "guests": guests,
            "has_restaurant": restaurant,
            "local_authority_id": authority,
        },
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_all_nineteen_authorities_are_offered(client):
    """ข้อ 4: ต้องรองรับ อปท. ครบ 19 แห่ง และต้องอ่านจาก DB"""
    rows = client.get("/api/v1/wizard/local-authorities").json()
    assert len(rows) == 19


@pytest.mark.parametrize(
    "case,rooms,guests,restaurant,expected_type,expected_fee",
    [
        ("T-01 บ้านพัก 6 ห้อง 24 คน", 6, 24, False, "not_hotel", None),
        ("T-02 8 ห้อง แต่รับ 36 คน", 8, 36, False, "type_1", 10000.0),
        ("T-03 20 ห้อง ไม่มีห้องอาหาร", 20, 60, False, "type_1", 10000.0),
        ("T-04 45 ห้อง มีห้องอาหาร", 45, 120, True, "type_2", 20000.0),
        ("T-05 60 ห้อง", 60, 200, True, "out_of_scope", None),
        ("ขอบ: 8 ห้อง 30 คน ยังยกเว้น", 8, 30, False, "not_hotel", None),
        ("ขอบ: 9 ห้อง 30 คน ห้องเกิน", 9, 30, False, "type_1", 10000.0),
        ("ขอบ: 49 ห้อง ยังอยู่ในขอบเขต", 49, 150, False, "type_1", 10000.0),
        ("ขอบ: 50 ห้อง เกินขอบเขต", 50, 150, False, "out_of_scope", None),
    ],
)
def test_test_cases_from_the_brief(
    client, case, rooms, guests, restaurant, expected_type, expected_fee
):
    body = ask(client, rooms, guests, restaurant)
    assert body["property_type_code"] == expected_type, case

    if expected_fee is None:
        assert body["fee"] is None, case
    else:
        assert body["fee"]["amount"] == expected_fee, case
        assert body["fee"]["validity_years"] == 5, case


def test_t02_is_the_trap_that_checking_only_rooms_would_fail(client):
    """T-02 คือเคสที่ระบบซึ่งเช็กแต่จำนวนห้องจะตอบผิดทันที

    8 ห้อง "ไม่เกิน 8" จึงดูเหมือนได้รับยกเว้น แต่รับ 36 คนซึ่งเกิน 30
    เงื่อนไขยกเว้นเป็น AND จึงหลุด และต้องกลายเป็นต้องขอใบอนุญาต
    """
    exempt = ask(client, 8, 30)
    trapped = ask(client, 8, 36)

    assert exempt["property_type_code"] == "not_hotel"
    assert trapped["requires_license"] is True
    assert trapped["property_type_code"] == "type_1"


def test_reason_explains_why_using_the_answers(client):
    """M2: ต้องแสดง "เหตุผลว่าทำไมจึงได้ผลนั้น" ไม่ใช่แค่ชื่อประเภท"""
    body = ask(client, 6, 24)
    assert "6" in body["reason"] and "24" in body["reason"]
    assert body["matched_rule_code"] == "RULE-NOT-HOTEL"


def test_not_hotel_still_returns_documents_and_contact(client, karon_id):
    """ตารางข้อ 4 บังคับว่ากรณีไม่เข้าข่ายก็ยังต้องแสดงเอกสารและหน่วยงาน"""
    docs = ask(client, 6, 24, authority=karon_id)["documents"]

    assert [d["code"] for d in docs["self_service"]] == ["A01", "A02", "A03", "A04", "A05"]
    assert [d["code"] for d in docs["external"]] == ["B01"]
    assert docs["needs_local_authority"] is False


def test_external_document_answers_all_four_questions_of_m4(client, karon_id):
    """M4: หน่วยงานใด / ท้องถิ่นใด / ใช้เอกสารประกอบอะไร / ใช้เวลาเท่าใด"""
    b01 = ask(client, 6, 24, authority=karon_id)["documents"]["external"][0]

    assert b01["preparation_note"], "ใช้เอกสารประกอบอะไร"
    assert b01["estimated_days"] == 30, "ใช้เวลาเท่าใด"

    cp = b01["contact_point"]
    assert cp["agency_name"], "หน่วยงานใด"
    assert cp["local_authority_name"] == "เทศบาลตำบลกะรน", "ท้องถิ่นใด"
    assert "กะรน" in cp["office_name"]


def test_contact_point_differs_per_authority(client):
    """ปัญหาข้อ 3 ของโจทย์: แต่ละท้องถิ่นมีจุดติดต่อต่างกัน
    ผู้ใช้เขตหนึ่งต้องไม่เห็นที่อยู่ของอีกเขต
    """
    rows = client.get("/api/v1/wizard/local-authorities").json()
    a, b = rows[1]["id"], rows[2]["id"]

    office_a = ask(client, 6, 24, authority=a)["documents"]["external"][0]["contact_point"]
    office_b = ask(client, 6, 24, authority=b)["documents"]["external"][0]["contact_point"]

    assert office_a["office_name"] != office_b["office_name"]


def test_asks_for_authority_when_not_chosen_yet(client):
    """ถ้ายังไม่เลือกเขต ต้องบอกหน้าจอให้ถามก่อน ไม่ใช่แสดงที่อยู่มั่ว ๆ"""
    docs = ask(client, 6, 24, authority=None)["documents"]

    assert docs["needs_local_authority"] is True
    assert docs["external"][0]["contact_point"] is None


def test_upload_rules_come_from_the_database(client, karon_id):
    """M5 ตรวจชนิดไฟล์ + สเปกของทีม: A01 กรอกในระบบ, A04 แนบหลายภาพ"""
    docs = ask(client, 6, 24, authority=karon_id)["documents"]
    by_code = {d["code"]: d for d in docs["self_service"] + docs["external"]}

    assert by_code["A01"]["is_system_form"] is True
    assert by_code["A04"]["allows_multiple"] is True
    assert by_code["B01"]["accepted_mime"] == ["application/pdf"]
    assert by_code["A04"]["accepted_mime"] == ["image/jpeg", "image/png"]


def test_classify_does_not_write_anything_to_the_database(client):
    """US-01 คือ "ตอบคำถามไม่กี่ข้อแล้วรู้ผล" — คนที่แค่มาลองต้องไม่สร้างขยะใน DB

    ผลจะถูกบันทึกตอนกดเริ่มยื่นคำขอเท่านั้น
    """
    with SessionLocal() as db:
        before = (
            db.scalar(select(func.count()).select_from(Property)),
            db.scalar(select(func.count()).select_from(ApplicationClassification)),
        )

    for _ in range(3):
        ask(client, 6, 24)

    with SessionLocal() as db:
        after = (
            db.scalar(select(func.count()).select_from(Property)),
            db.scalar(select(func.count()).select_from(ApplicationClassification)),
        )

    assert before == after


@pytest.mark.parametrize("rooms,guests", [(0, 10), (-1, 10), (5, 0)])
def test_rejects_impossible_answers(client, rooms, guests):
    res = client.post(CLASSIFY, json={"rooms": rooms, "guests": guests})
    assert res.status_code == 422
