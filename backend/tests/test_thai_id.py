"""ทดสอบการตรวจเลขประจำตัวประชาชน

เลขทั้งหมดในไฟล์นี้สร้างขึ้นให้ผ่านสูตร check digit เท่านั้น
ไม่ใช่เลขของบุคคลจริง (กติกาข้อ 14)
"""

import pytest

from app.core.thai_id import format_display, is_valid, mask, normalize


def make_valid(prefix12: str) -> str:
    total = sum(int(prefix12[i]) * (13 - i) for i in range(12))
    return prefix12 + str((11 - total % 11) % 10)


VALID = make_valid("110070123456")


def test_valid_id_passes():
    assert is_valid(VALID)


def test_accepts_dashes_and_spaces():
    assert is_valid(format_display(VALID))
    assert normalize("1-1007-01234-56-1") == "1100701234561"


@pytest.mark.parametrize("bad", ["", "123", "1" * 13, "abcdefghijklm", "1100701234560"])
def test_invalid_ids_rejected(bad):
    assert not is_valid(bad)


def test_single_digit_typo_is_mostly_caught():
    """จุดประสงค์หลักของ check digit — พิมพ์ผิดหนึ่งหลักควรถูกจับได้เกือบทั้งหมด

    หมายเหตุ: จับได้ไม่ครบ 100% โดยธรรมชาติของสูตร
    หลักตรวจสอบคำนวณจาก (11 - ผลรวม % 11) % 10  การ mod 10 ตอนท้ายทำให้
    ผลรวมที่เหลือเศษ 0 กับ 10 ให้หลักตรวจสอบเดียวกันคือ 1  จึงมีการพิมพ์ผิด
    บางกรณีที่เล็ดลอดไปได้ ~19%

    ข้อสรุปสำหรับทีม: หลักตรวจสอบช่วยกรองการพิมพ์ผิดได้มาก แต่ไม่ใช่การพิสูจน์
    ว่าเลขนี้มีตัวตนจริง การยืนยันตัวตนจริงยังต้องดูจากสำเนาบัตร (เอกสาร A02)
    """
    total = caught = 0
    for i in range(12):
        for d in "0123456789":
            if d == VALID[i]:
                continue
            total += 1
            if not is_valid(VALID[:i] + d + VALID[i + 1 :]):
                caught += 1

    assert caught / total >= 0.8, f"จับการพิมพ์ผิดได้เพียง {caught}/{total}"


def test_mask_hides_everything_but_last_digits():
    masked = mask(VALID)
    assert masked == "x-xxxx-xxxxx-45-1"
    # 9 หลักแรกต้องไม่ปรากฏในผลลัพธ์
    assert VALID[:9] not in masked
