"""หมายเลขโทรศัพท์ไทย — ทำให้อยู่รูปแบบเดียวกันก่อนเก็บและก่อนค้นหา

ทำไมต้อง normalize ก่อนเก็บ:
M1 ให้เข้าสู่ระบบด้วยเบอร์โทรได้ ถ้าผู้ใช้สมัครด้วย "081-234-5678"
แล้วพิมพ์ "0812345678" ตอนเข้าสู่ระบบ ระบบต้องรู้ว่าเป็นคนเดียวกัน
จึงเก็บเป็นตัวเลขล้วนเสมอ แล้วค่อยใส่ขีดตอนแสดงผล

ตรรกะเดียวกับ frontend/src/lib/phone.ts — แก้ไฟล์ใดต้องแก้อีกไฟล์ด้วย
"""

MOBILE_LENGTH = 10  # 08x-xxx-xxxx
LANDLINE_LENGTH = 9  # 076-xxx-xxx


def normalize(value: str) -> str:
    """เหลือเฉพาะตัวเลข และแปลงรูปแบบสากล (+66 81 234 5678) ให้เป็น 0812345678

    รับรูปแบบสากลด้วยเพราะผู้ประกอบการที่เคยลงทะเบียนกับแพลตฟอร์มจองที่พัก
    มักคุ้นกับการเขียนเบอร์แบบ +66
    """
    digits = "".join(ch for ch in value if ch.isdigit())
    if digits.startswith("66") and len(digits) in (LANDLINE_LENGTH + 1, MOBILE_LENGTH + 1):
        digits = "0" + digits[2:]
    return digits


def is_valid(value: str) -> bool:
    """เบอร์มือถือ 10 หลัก หรือเบอร์บ้าน 9 หลัก และต้องขึ้นต้นด้วย 0

    ไม่ตรวจละเอียดกว่านี้ (เช่น บังคับขึ้นต้น 06/08/09) เพราะช่วงหมายเลข
    ที่ กสทช. จัดสรรเปลี่ยนได้ การบล็อกเกินจำเป็นจะกันผู้ใช้จริงออกไป
    """
    digits = normalize(value)
    return len(digits) in (LANDLINE_LENGTH, MOBILE_LENGTH) and digits.startswith("0")


def format_display(value: str) -> str:
    """ใส่ขีดให้อ่านง่าย -> 081-234-5678 หรือ 076-123-456"""
    d = normalize(value)
    if len(d) not in (LANDLINE_LENGTH, MOBILE_LENGTH):
        return value
    return f"{d[:3]}-{d[3:6]}-{d[6:]}"
