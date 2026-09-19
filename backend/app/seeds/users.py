"""บัญชีผู้ใช้จำลองสำหรับการสาธิต (กติกาข้อ 14: ห้ามใช้ข้อมูลส่วนบุคคลจริง)

ชื่อ อีเมล และเบอร์โทรทั้งหมดเป็นข้อมูลสมมติ ไม่ใช่ของบุคคลจริง
รหัสผ่านเดียวกันหมดเพื่อให้สาธิตง่าย — ของจริงต้องบังคับตั้งรหัสเอง

โหมดสาธิตเท่านั้น: อย่าใช้ค่าเหล่านี้กับระบบที่เปิดใช้งานจริง
"""

DEMO_PASSWORD = "demo1234"

DEMO_USERS: list[dict] = [
    {
        "email": "operator@example.com",
        "phone": "0800000001",
        "first_name": "สมชาย",
        "last_name": "ใจดี",
        "role": "operator",
        "authority_code": None,
    },
    {
        "email": "officer@example.com",
        "phone": "0800000002",
        "first_name": "สมหญิง",
        "last_name": "รักงาน",
        "role": "officer",
        "authority_code": "PKT-CITY",
        "pseudonym_code": "OFC-2569-001",
    },
    {
        "email": "central@example.com",
        "phone": "0800000003",
        "first_name": "สมศักดิ์",
        "last_name": "มองภาพรวม",
        "role": "central",
        "authority_code": None,
    },
    {
        "email": "admin@example.com",
        "phone": "0800000004",
        "first_name": "ผู้ดูแล",
        "last_name": "ระบบ",
        "role": "super_admin",
        "authority_code": None,
    },
]
