"""ทดสอบกฎจำแนกประเภทตามตาราง test case ของโจทย์ (ข้อ 13)

ทดสอบโดย "อ่านกฎจากฐานข้อมูลจริง" ไม่ใช่จาก constant ในโค้ด
เพราะสิ่งที่ต้องพิสูจน์คือระบบตัดสินจากข้อมูลใน DB ตาม US-09
ถ้าใครเผลอย้ายเงื่อนไขกลับไป hard-code ในโค้ด เทสต์ชุดนี้จะยังผ่าน
แต่ test_rules_are_loaded_from_database จะจับได้

รัน: cd backend && uv run pytest
"""

import pytest
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.classification import ClassificationRule


@pytest.fixture(scope="module")
def rules() -> list[ClassificationRule]:
    with SessionLocal() as db:
        loaded = db.scalars(
            select(ClassificationRule)
            .where(ClassificationRule.is_active)
            .order_by(ClassificationRule.priority)
        ).all()
        for r in loaded:
            _ = r.property_type.code  # โหลดก่อนปิด session
        return list(loaded)


def classify(rules: list[ClassificationRule], rooms: int, guests: int, restaurant: bool) -> str:
    """กฎแรกที่เข้าเงื่อนไขครบชนะ — ตรรกะเดียวกับ services/classification.py"""
    hit = next((r for r in rules if r.matches(rooms, guests, restaurant)), None)
    return hit.property_type.code if hit else "no_match"


def test_rules_are_loaded_from_database(rules):
    """กันการถอยกลับไป hard-code: ต้องมีกฎอยู่ใน DB จริง"""
    assert len(rules) >= 4, "ไม่พบกฎในฐานข้อมูล — รัน uv run python -m app.seeds.run ก่อน"


@pytest.mark.parametrize(
    "case,rooms,guests,restaurant,expected",
    [
        ("T-01 บ้านพัก 6 ห้อง 24 คน", 6, 24, False, "not_hotel"),
        # T-02 คือกับดักหลักของโจทย์: ห้องไม่เกิน 8 แต่คนเกิน 30
        # ต้องตอบว่า "เข้าข่ายต้องขอใบอนุญาต" ไม่ใช่ได้รับยกเว้น
        ("T-02 ที่พัก 8 ห้อง 36 คน", 8, 36, False, "type_1"),
        ("T-02 แบบมีห้องอาหาร", 8, 36, True, "type_2"),
        ("T-03 20 ห้อง ไม่มีห้องอาหาร", 20, 40, False, "type_1"),
        ("T-04 45 ห้อง มีห้องอาหาร", 45, 90, True, "type_2"),
        ("T-05 60 ห้อง", 60, 120, True, "out_of_scope"),
        # ขอบเขตที่พลาดง่าย — เงื่อนไขยกเว้นเป็น "ไม่เกิน" ทั้งคู่ (inclusive)
        ("ขอบ: 8 ห้อง 30 คน ยังได้รับยกเว้น", 8, 30, False, "not_hotel"),
        ("ขอบ: 8 ห้อง 31 คน หลุดยกเว้นแล้ว", 8, 31, False, "type_1"),
        ("ขอบ: 9 ห้อง 20 คน", 9, 20, False, "type_1"),
        ("ขอบ: 49 ห้อง ยังอยู่ในขอบเขต", 49, 98, False, "type_1"),
        ("ขอบ: 50 ห้อง เกินขอบเขต", 50, 100, False, "out_of_scope"),
    ],
)
def test_classification(rules, case, rooms, guests, restaurant, expected):
    assert classify(rules, rooms, guests, restaurant) == expected, case


def test_no_gap_in_rule_coverage(rules):
    """ไม่ว่าผู้ใช้กรอกอะไรมา ต้องมีกฎรองรับเสมอ — ห้ามมีช่องโหว่แบบ T-02 อีก"""
    for rooms in range(1, 61):
        for guests in (1, 30, 31, 200):
            for restaurant in (True, False):
                got = classify(rules, rooms, guests, restaurant)
                assert got != "no_match", f"ไม่มีกฎรองรับ: {rooms} ห้อง {guests} คน rest={restaurant}"
