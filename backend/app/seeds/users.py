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
        "full_name": "สมชาย ใจดี (ผู้ประกอบการ)",
        "role": "operator",
        "authority_code": None,
    },
    {
        "email": "officer@example.com",
        "phone": "0800000002",
        "full_name": "สมหญิง รักงาน (เจ้าหน้าที่ เทศบาลนครภูเก็ต)",
        "role": "officer",
        "authority_code": "PKT-CITY",
        "pseudonym_code": "OFC-2569-001",
    },
    {
        "email": "central@example.com",
        "phone": "0800000003",
        "full_name": "สมศักดิ์ มองภาพรวม (ส่วนกลาง)",
        "role": "central",
        "authority_code": None,
    },
    {
        "email": "admin@example.com",
        "phone": "0800000004",
        "full_name": "ผู้ดูแลระบบ (Super Admin)",
        "role": "super_admin",
        "authority_code": None,
    },
]
