"""เลขประจำตัวประชาชนไทย — ตรวจความถูกต้องและปิดบังเพื่อแสดงผล

ทำไมต้องตรวจ checksum ไม่ใช่แค่นับ 13 หลัก:
เลขบัตรมีหลักตรวจสอบในตัว การพิมพ์ผิดหนึ่งหลักจะตรวจจับได้ทันทีตั้งแต่หน้าสมัคร
แทนที่จะไปพบตอนเจ้าหน้าที่ตรวจเอกสาร ซึ่งเสียเวลาทั้งสองฝ่าย
"""


def normalize(value: str) -> str:
    """ตัดขีดและช่องว่างออก เหลือเฉพาะตัวเลข"""
    return "".join(ch for ch in value if ch.isdigit())


def is_valid(value: str) -> bool:
    """ตรวจด้วยหลักตรวจสอบ (check digit) ตามสูตรของกรมการปกครอง

    ผลรวมของ 12 หลักแรกคูณด้วยน้ำหนัก 13 ลงมาถึง 2
    แล้ว (11 - ผลรวม % 11) % 10 ต้องเท่ากับหลักที่ 13
    """
    digits = normalize(value)
    if len(digits) != 13:
        return False

    total = sum(int(digits[i]) * (13 - i) for i in range(12))
    return (11 - total % 11) % 10 == int(digits[12])


def mask(value: str) -> str:
    """ปิดบังไว้แสดงผล เหลือเฉพาะ 4 หลักท้าย -> x-xxxx-xxxxx-12-3

    ใช้ทุกที่ที่ต้องแสดงเลขบัตรบนหน้าจอหรือใน log
    เพียงพอให้เจ้าของยืนยันว่าเป็นเลขของตน แต่ไม่พอให้คนอื่นนำไปใช้ต่อ
    """
    digits = normalize(value)
    if len(digits) != 13:
        return "x-xxxx-xxxxx-xx-x"
    return f"x-xxxx-xxxxx-{digits[9:11]}-{digits[12]}"


def format_display(value: str) -> str:
    """จัดรูปแบบเต็ม 1-2345-67890-12-3 — ใช้เฉพาะกับผู้มีสิทธิ์เห็นเลขเต็ม"""
    d = normalize(value)
    if len(d) != 13:
        return value
    return f"{d[0]}-{d[1:5]}-{d[5:10]}-{d[10:12]}-{d[12]}"
