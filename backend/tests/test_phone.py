"""ทดสอบการทำหมายเลขโทรศัพท์ให้อยู่รูปแบบเดียวกัน (app/core/phone.py)

สำคัญกับ M1 เพราะเบอร์โทรเป็นกุญแจเข้าสู่ระบบอีกทางหนึ่ง
ถ้า normalize ไม่ตรงกันระหว่างตอนสมัครกับตอนเข้าสู่ระบบ ผู้ใช้จะเข้าไม่ได้เลย
"""

import pytest

from app.core import phone


@pytest.mark.parametrize(
    "written,expected",
    [
        ("0812345678", "0812345678"),
        ("081-234-5678", "0812345678"),
        ("081 234 5678", "0812345678"),
        ("+66 81 234 5678", "0812345678"),  # รูปแบบสากลต้องกลายเป็นเบอร์ในประเทศ
        ("076123456", "076123456"),  # เบอร์บ้านภูเก็ต 9 หลัก
    ],
)
def test_normalize_collapses_every_way_people_write_a_number(written, expected):
    assert phone.normalize(written) == expected


@pytest.mark.parametrize("value", ["0812345678", "081-234-5678", "076123456", "+66812345678"])
def test_valid_numbers(value):
    assert phone.is_valid(value)


@pytest.mark.parametrize(
    "value,reason",
    [
        ("08123456", "สั้นเกินไป"),
        ("08123456789", "ยาวเกินไป"),
        ("1812345678", "ไม่ขึ้นต้นด้วย 0"),
        ("", "ว่าง"),
        ("โทรหาฉัน", "ไม่มีตัวเลข"),
    ],
)
def test_invalid_numbers(value, reason):
    assert not phone.is_valid(value), reason


def test_format_display_adds_dashes():
    assert phone.format_display("0812345678") == "081-234-5678"
    assert phone.format_display("076123456") == "076-123-456"


def test_format_display_leaves_unknown_shapes_alone():
    """ไม่ดัดแปลงค่าที่ไม่รู้จัก เพื่อไม่ให้ข้อมูลเพี้ยนตอนแสดงผล"""
    assert phone.format_display("12345") == "12345"
