"""ข้อมูลตั้งต้นของการจำแนกประเภทและค่าธรรมเนียม (ตารางข้อ 4 ของโจทย์)

ย้ำ: ไฟล์นี้คือ "ค่าตั้งต้นสำหรับ import ครั้งแรก" เท่านั้น
โจทย์กำหนดว่าหลังจากนี้ Super Admin ต้องแก้ได้เองผ่านหน้าจอ (US-09)
โค้ดส่วนอื่นห้ามอ่านค่าจากไฟล์นี้ ต้อง query จากตารางเสมอ
"""

from datetime import date

# วันที่กฎชุดแรกเริ่มมีผล — ใช้วันเริ่มกิจกรรม Hackathon
EFFECTIVE_FROM = date(2026, 9, 19)

PROPERTY_TYPES: list[dict] = [
    {
        "code": "not_hotel",
        "name_th": "ไม่เข้าข่ายโรงแรม",
        "description": "ที่พักขนาดเล็กที่ได้รับยกเว้น ไม่ต้องขอใบอนุญาตโรงแรม",
        "requires_license": False,
        "is_out_of_scope": False,
        "display_order": 1,
    },
    {
        "code": "type_1",
        "name_th": "ที่พักแรม ประเภทที่ 1",
        "description": "ห้องพักไม่เกิน 49 ห้อง และไม่มีห้องอาหาร",
        "requires_license": True,
        "is_out_of_scope": False,
        "display_order": 2,
    },
    {
        "code": "type_2",
        "name_th": "ที่พักแรม ประเภทที่ 2",
        "description": "ห้องพักไม่เกิน 49 ห้อง และมีห้องอาหาร",
        "requires_license": True,
        "is_out_of_scope": False,
        "display_order": 3,
    },
    {
        "code": "out_of_scope",
        "name_th": "เกินขอบเขตของระบบ",
        "description": "ห้องพักเกิน 49 ห้อง ต้องติดต่อนายทะเบียนโดยตรง",
        "requires_license": True,
        "is_out_of_scope": True,
        "display_order": 4,
    },
]

# ลำดับ priority คือส่วนหนึ่งของความถูกต้อง ไม่ใช่แค่การจัดเรียง
# เว้นเลขห่าง 10 ไว้ให้ Super Admin แทรกกฎใหม่ได้โดยไม่ต้องเรียงใหม่ทั้งชุด
CLASSIFICATION_RULES: list[dict] = [
    {
        # ข้อยกเว้น — ต้องเข้าเงื่อนไขครบ *ทั้งสองข้อ* จึงจะได้รับยกเว้น
        # หลุดข้อใดข้อหนึ่ง = เป็นโรงแรม แล้วตกไปให้กฎถัดไปตัดสิน (กับดัก T-02)
        "code": "RULE-NOT-HOTEL",
        "property_type": "not_hotel",
        "priority": 10,
        "min_rooms": None,
        "max_rooms": 8,
        "min_guests": None,
        "max_guests": 30,
        "requires_restaurant": None,
        "reason_template": (
            "ที่พักของคุณมี {rooms} ห้อง และรับผู้เข้าพักได้ {guests} คน "
            "ซึ่งไม่เกินเกณฑ์ยกเว้น (ไม่เกิน 8 ห้อง และไม่เกิน 30 คน) ทั้งสองข้อ"
        ),
        "outcome_message": (
            "ไม่ต้องขอใบอนุญาตโรงแรม แต่ต้องดำเนินการแจ้งตามแนวทางที่กำหนด "
            "ระบบได้แสดงรายการเอกสารและหน่วยงานที่ต้องติดต่อไว้ด้านล่าง"
        ),
    },
    {
        # ต้องมาก่อนประเภท 1/2 เพราะกฎสองข้อนั้นไม่ได้กำหนดเพดานบนไว้ซ้ำ
        "code": "RULE-OUT-OF-SCOPE",
        "property_type": "out_of_scope",
        "priority": 20,
        "min_rooms": 50,
        "max_rooms": None,
        "min_guests": None,
        "max_guests": None,
        "requires_restaurant": None,
        "reason_template": "ที่พักของคุณมี {rooms} ห้อง ซึ่งเกิน 49 ห้อง",
        "outcome_message": (
            "ที่พักของคุณอยู่นอกขอบเขตของแพลตฟอร์มในระยะนี้ "
            "กรุณาติดต่อนายทะเบียนโดยตรงเพื่อดำเนินการ"
        ),
    },
    {
        # ไม่ใส่ min_rooms โดยตั้งใจ — ดูคำอธิบายกับดัก T-02 ใน models/classification.py
        "code": "RULE-TYPE-1",
        "property_type": "type_1",
        "priority": 30,
        "min_rooms": None,
        "max_rooms": 49,
        "min_guests": None,
        "max_guests": None,
        "requires_restaurant": False,
        "reason_template": (
            "ที่พักของคุณมี {rooms} ห้อง รับผู้เข้าพักได้ {guests} คน และไม่มีห้องอาหาร "
            "จึงเข้าข่ายต้องขอใบอนุญาตในฐานะที่พักแรมประเภทที่ 1"
        ),
        "outcome_message": "ต้องขอใบอนุญาต ค่าธรรมเนียม 10,000 บาท ต่อระยะเวลา 5 ปี",
    },
    {
        "code": "RULE-TYPE-2",
        "property_type": "type_2",
        "priority": 40,
        "min_rooms": None,
        "max_rooms": 49,
        "min_guests": None,
        "max_guests": None,
        "requires_restaurant": True,
        "reason_template": (
            "ที่พักของคุณมี {rooms} ห้อง รับผู้เข้าพักได้ {guests} คน และมีห้องอาหาร "
            "จึงเข้าข่ายต้องขอใบอนุญาตในฐานะที่พักแรมประเภทที่ 2"
        ),
        "outcome_message": "ต้องขอใบอนุญาต ค่าธรรมเนียม 20,000 บาท ต่อระยะเวลา 5 ปี",
    },
]

FEE_SCHEDULES: list[dict] = [
    {"property_type": "type_1", "amount": 10000, "validity_years": 5,
     "note": "อัตราตั้งต้นตามตารางข้อ 4 ของโจทย์"},
    {"property_type": "type_2", "amount": 20000, "validity_years": 5,
     "note": "อัตราตั้งต้นตามตารางข้อ 4 ของโจทย์"},
]
