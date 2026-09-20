"""เอกสารประกอบคำขอ + หน่วยงานที่ออกเอกสาร + จุดติดต่อ (M3, M4)

ครอบทั้งสามเส้น: ไม่เข้าข่ายโรงแรม, ที่พักแรมประเภทที่ 1 และประเภทที่ 2

เอกสารบางฉบับใช้ร่วมกันหลายประเภท (เอกสารสิทธิ์ที่ดิน ภาพถ่ายอาคาร รูปถ่ายผู้แจ้ง)
จึงประกาศ DocumentType ครั้งเดียวแล้วผูกเข้ากับแต่ละประเภทผ่าน DOCUMENT_REQUIREMENTS
ลำดับการแสดงอยู่ที่ requirement เพราะแต่ละรายการเรียงไม่เหมือนกัน

ย้ำเหมือน classification.py: ไฟล์นี้คือค่าตั้งต้นสำหรับ import ครั้งแรกเท่านั้น
หลังจากนี้ Super Admin แก้ผ่านหน้าจอได้ (US-09) โค้ดส่วนอื่นห้ามอ่านจากไฟล์นี้

ข้อมูลจุดติดต่อทั้งหมดเป็นข้อมูลจำลองสำหรับการสาธิต (กติกาข้อ 14)
"""

from app.models.enums import DocumentCategory

PDF_ONLY = "application/pdf"
IMAGE_ONLY = "image/jpeg,image/png"
PDF_OR_IMAGE = "application/pdf,image/jpeg,image/png"


ISSUING_AGENCIES: list[dict] = [
    {
        "code": "LOCAL-WORKS",
        "name": "กองช่าง องค์กรปกครองส่วนท้องถิ่น",
        "description": (
            "ฝ่ายที่ออกใบอนุญาตก่อสร้างอาคาร (อ.1) ใบรับรองการก่อสร้าง (อ.5) "
            "และใบอนุญาตเปลี่ยนการใช้อาคาร (อ.4) โดยยื่นที่ อปท. ที่ที่พักตั้งอยู่"
        ),
    },
]


# ---------------------------------------------------------------------------
# ชนิดเอกสาร — รหัส A = ผู้ประกอบการทำเองได้, รหัส B = ต้องขอจากหน่วยงานอื่น
# ---------------------------------------------------------------------------
DOCUMENT_TYPES: list[dict] = [
    {
        "code": "A01",
        "name_th": "แบบหนังสือแจ้งสถานที่พักที่ไม่เป็นโรงแรม",
        "description": (
            "กรอกในระบบได้เลย ระบบดึงชื่อผู้แจ้งจากบัญชี และชื่อ/ที่อยู่สถานที่ "
            "จากข้อมูลที่พักที่กรอกไว้ เหลือเพียงเลือกลักษณะที่พักและลงลายมือชื่อ"
        ),
        "category": DocumentCategory.SELF,
        # ไม่ใช่ไฟล์ที่ผู้ใช้ไปหามาจากที่อื่น แต่เป็นแบบฟอร์มที่ระบบสร้างให้
        "is_system_form": True,
        "allows_multiple": False,
        # ลายมือชื่อที่วาดบนจอถูกบันทึกเป็นภาพ PNG
        "accepted_mime": "image/png",
        "display_order": 1,
    },
    {
        "code": "A02",
        "name_th": "สำเนาทะเบียนบ้านผู้แจ้ง",
        "description": "ถ่ายรูปหรือสแกนหน้าที่มีชื่อผู้แจ้ง ให้เห็นเลขที่บ้านชัดเจน",
        "category": DocumentCategory.SELF,
        "accepted_mime": PDF_OR_IMAGE,
        "display_order": 2,
    },
    {
        "code": "B01",
        "name_th": "ใบอนุญาตก่อสร้างอาคาร (อ.1)",
        "description": ("ต้องยื่นขอที่กองช่างของ อปท. ที่ที่พักตั้งอยู่ แล้วนำฉบับที่เจ้าหน้าที่ลงนามแล้วมาอัปโหลดเข้าระบบ"),
        "category": DocumentCategory.EXTERNAL,
        "issuing_agency": "LOCAL-WORKS",
        # M4 บังคับให้บอกว่า "ใช้เอกสารประกอบอะไร"
        "preparation_note": (
            "เตรียมไปที่หน่วยงาน: สำเนาบัตรประจำตัวประชาชน, สำเนาทะเบียนบ้าน, "
            "สำเนาเอกสารสิทธิ์ที่ดิน, แบบแปลนอาคาร และรูปถ่ายอาคารด้านหน้า"
        ),
        "estimated_days": 30,  # M4 บังคับให้บอกว่า "ใช้เวลาโดยประมาณเท่าใด"
        "accepted_mime": PDF_ONLY,
        "display_order": 3,
    },
    {
        "code": "A03",
        "name_th": "เอกสารสิทธิ์ที่ดิน",
        "description": "โฉนดที่ดิน น.ส.3 ก. หรือเอกสารสิทธิ์อื่นของที่ดินที่ตั้งที่พัก",
        "category": DocumentCategory.SELF,
        "accepted_mime": PDF_ONLY,
        "display_order": 4,
    },
    {
        "code": "A04",
        "name_th": "ภาพถ่ายอาคารที่ขออนุญาต",
        "description": "แนบได้หลายภาพ ควรมีทั้งด้านหน้า ด้านข้าง และภายในห้องพัก",
        "category": DocumentCategory.SELF,
        "allows_multiple": True,
        "accepted_mime": IMAGE_ONLY,
        "display_order": 5,
    },
    {
        "code": "A05",
        "name_th": "รูปถ่ายผู้แจ้ง",
        "description": "รูปถ่ายหน้าตรงของผู้แจ้ง เห็นใบหน้าชัดเจน",
        "category": DocumentCategory.SELF,
        "accepted_mime": IMAGE_ONLY,
        "display_order": 6,
    },
    # ---------------- เฉพาะที่พักแรมประเภทที่ 1 และ 2 (เข้าข่ายโรงแรม) ----------------
    {
        "code": "A06",
        "name_th": "แบบ ร.ร.1",
        "description": (
            "คำขอรับใบอนุญาตประกอบธุรกิจโรงแรม กรอกในระบบได้เลย ระบบดึงชื่อโรงแรมและที่ตั้งจากข้อมูลที่พักที่กรอกไว้"
        ),
        "category": DocumentCategory.SELF,
        "is_system_form": True,
        "accepted_mime": "image/png",  # ลายมือชื่อที่วาดบนจอ
        "display_order": 10,
    },
    # สามฉบับถัดไปเป็นช่องแนบ "ที่อยู่ในแบบ ร.ร.1" ไม่ใช่รายการลอย ๆ
    # ผู้ยื่นติ๊กว่ามีฉบับไหนแล้วค่อยแนบ จึงไม่บังคับทุกฉบับ
    {
        "code": "A07",
        "name_th": "หนังสือรับรองการจดทะเบียนนิติบุคคล",
        "description": "แนบเมื่อผู้ขออนุญาตเป็นนิติบุคคล บุคคลธรรมดาไม่ต้องแนบ",
        "category": DocumentCategory.SELF,
        "parent": "A06",
        "accepted_mime": PDF_ONLY,
        "display_order": 11,
    },
    {
        "code": "A08",
        "name_th": "สำเนาทะเบียนบ้านโรงแรม",
        "description": "สำเนาทะเบียนบ้านของอาคารที่ใช้ประกอบธุรกิจโรงแรม",
        "category": DocumentCategory.SELF,
        "parent": "A06",
        "accepted_mime": PDF_ONLY,
        "display_order": 12,
    },
    {
        "code": "A09",
        "name_th": "หลักฐานแสดงความเป็นเจ้าของสถานที่",
        "description": "เช่น สัญญาเช่า หนังสือยินยอมให้ใช้สถานที่ หรือเอกสารสิทธิ์",
        "category": DocumentCategory.SELF,
        "parent": "A06",
        "accepted_mime": PDF_ONLY,
        "display_order": 13,
    },
    {
        "code": "B02",
        "name_th": "หนังสือรับรองการดัดแปลงอาคาร (อ.5)",
        "description": (
            "ต้องยื่นขอที่กองช่างของ อปท. ที่โรงแรมตั้งอยู่ แล้วนำฉบับที่เจ้าหน้าที่ลงนามแล้วมาอัปโหลดเข้าระบบ"
        ),
        "category": DocumentCategory.EXTERNAL,
        "issuing_agency": "LOCAL-WORKS",
        "preparation_note": (
            "เตรียมไปที่หน่วยงาน: ใบอนุญาตก่อสร้างอาคารเดิม, แบบแปลนอาคารที่ดัดแปลง, "
            "สำเนาเอกสารสิทธิ์ที่ดิน และรูปถ่ายอาคารก่อน–หลังดัดแปลง"
        ),
        "estimated_days": 45,
        "accepted_mime": PDF_ONLY,
        "display_order": 14,
    },
]


# ---------------------------------------------------------------------------
# เอกสารฉบับใดบังคับกับที่พักประเภทใด
#
# ตารางข้อ 4 ของโจทย์เขียนไว้ว่ากรณีไม่เข้าข่ายโรงแรม "ไม่ต้องขอใบอนุญาต
# แต่ต้องดำเนินการแจ้งตามแนวทางที่กำหนด ระบบต้องแสดงรายการเอกสารและ
# หน่วยงานที่ต้องติดต่อ" — เส้นนี้จึงมีรายการเอกสารเหมือนกรณีอื่น
# ---------------------------------------------------------------------------
NOT_HOTEL_DOCUMENTS = [
    ("A01", True),
    ("A02", True),
    ("B01", True),
    ("A03", True),
    ("A04", True),
    ("A05", True),
]

# ประเภทที่ 1 กับประเภทที่ 2 ใช้รายการเอกสารชุดเดียวกัน
# ต่างกันแค่ค่าธรรมเนียมตามตารางข้อ 4 (มี/ไม่มีห้องอาหาร) ซึ่งไม่กระทบเอกสาร
#
# สามฉบับที่ is_mandatory=False คือช่องแนบในแบบ ร.ร.1 ที่ผู้ยื่นติ๊กว่ามีก่อน
# จึงต้องไม่บล็อกการยื่น (M6) เพราะบางฉบับไม่มีจริงตามรูปแบบกิจการ
HOTEL_DOCUMENTS = [
    ("A06", True),
    ("A07", False),
    ("A08", False),
    ("A09", False),
    ("B02", True),
    ("A03", True),
    ("A04", True),
    ("A05", True),
]


def _requirements(property_type: str, items: list[tuple[str, bool]]) -> list[dict]:
    """ลำดับการแสดงคือลำดับที่เขียนไว้ในลิสต์ ไม่ต้องนับเลขเอง"""
    return [
        {
            "property_type": property_type,
            "document_type": code,
            "is_mandatory": mandatory,
            "display_order": order,
        }
        for order, (code, mandatory) in enumerate(items, start=1)
    ]


DOCUMENT_REQUIREMENTS: list[dict] = [
    *_requirements("not_hotel", NOT_HOTEL_DOCUMENTS),
    *_requirements("type_1", HOTEL_DOCUMENTS),
    *_requirements("type_2", HOTEL_DOCUMENTS),
]


# ---------------------------------------------------------------------------
# จุดติดต่อ: หน่วยงานเดียวกันแต่คนละ อปท. คนละที่อยู่ (M4 "ที่ท้องถิ่นใด")
#
# สร้างให้ครบทั้ง 19 แห่งจาก local_authority ที่ seed ไว้แล้ว
# ที่อยู่/เบอร์เป็นข้อมูลจำลอง Super Admin แก้ผ่านหน้าจอได้ภายหลัง
# ---------------------------------------------------------------------------
CONTACT_POINT_DEFAULTS: dict = {
    "issuing_agency": "LOCAL-WORKS",
    "office_name_template": "กองช่าง {authority_name}",
    "office_hours": "จันทร์–ศุกร์ 08.30–16.30 น. (พักเที่ยง 12.00–13.00 น.)",
    "estimated_days": 30,
    "notes": "ควรโทรนัดหมายล่วงหน้า และนำเอกสารตัวจริงไปแสดงพร้อมสำเนา",
}
