"""Business logic ที่ไม่ควรอยู่ใน endpoint

  classification.py  อ่าน ClassificationRule จาก DB แล้วตัดสินประเภท + สร้างเหตุผล
  documents.py       ตัดสินว่าคำขอนี้ต้องใช้เอกสารอะไรบ้าง / ครบหรือยัง
  audit.py           เขียน AuditLog ที่เดียว ทุกการเปลี่ยนสถานะเรียกผ่านที่นี่
  fees.py            คำนวณค่าธรรมเนียมจาก FeeSchedule ที่มีผล ณ วันที่ยื่น
  storage.py         จัดการไฟล์อัปโหลด + versioning
"""
