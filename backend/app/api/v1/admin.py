"""US-09 — Super Admin แก้ไขเงื่อนไขและค่าธรรมเนียมได้โดยไม่ต้องแก้โค้ด

endpoint กลุ่มนี้คือสิ่งที่พิสูจน์ว่าระบบเป็น config-driven จริง
เป็นจุดที่กรรมการน่าจะขอให้สาธิต (เกณฑ์ข้อ 2, 25 คะแนน)

เจ้าของงานส่วนนี้: <ใส่ชื่อสมาชิก>
"""

from fastapi import APIRouter

router = APIRouter()

# TODO US-09: GET/PUT /classification-rules   แก้เงื่อนไขจำแนกประเภท
# TODO US-09: GET/PUT /fee-schedules          แก้อัตราค่าธรรมเนียม (มีผลตามช่วงเวลา)
# TODO US-09: GET/PUT /document-types         แก้รายการเอกสารและหมวด
# TODO US-09: GET/PUT /local-authorities      แก้จุดติดต่อของแต่ละท้องถิ่น
# TODO M1:    GET/PUT /users                  จัดการบัญชีและสิทธิ์
