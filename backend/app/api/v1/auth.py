"""M1 — สมัครสมาชิก / เข้าสู่ระบบ / ยืนยันตัวตนด้วย OTP

เจ้าของงานส่วนนี้: <ใส่ชื่อสมาชิก>
"""

from fastapi import APIRouter

router = APIRouter()

# TODO M1: POST /register        สมัครด้วยเบอร์โทรหรืออีเมล
# TODO M1: POST /verify-otp      ยืนยันตัวตน (โหมดสาธิตใช้ OTP คงที่ 6 หลัก)
# TODO M1: POST /login           คืน JWT + role
# TODO M1: GET  /me              ข้อมูลผู้ใช้ปัจจุบัน
