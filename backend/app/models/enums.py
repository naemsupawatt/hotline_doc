"""ค่าคงที่ของสถานะทั้งระบบ

เก็บรวมไว้ที่เดียวเพื่อให้ backend กับ frontend อ้างอิงชุดเดียวกัน
(frontend อ่านผ่าน API ไม่ต้องประกาศซ้ำ)
"""

from enum import StrEnum


class UserRole(StrEnum):
    """บทบาทผู้ใช้ 4 บทบาทตามข้อ 5 ของโจทย์"""

    OPERATOR = "operator"  # ผู้ประกอบการ (ผู้ขอ)
    OFFICER = "officer"  # เจ้าหน้าที่ท้องถิ่น
    CENTRAL = "central"  # หน่วยงานส่วนกลาง
    SUPER_ADMIN = "super_admin"  # ผู้ดูแลระบบสูงสุด


class ClassificationResult(StrEnum):
    """ผลการจำแนกประเภทตามตารางข้อ 4

    หมายเหตุ: เงื่อนไขจริง (จำนวนห้อง/จำนวนคน/ค่าธรรมเนียม) เก็บในตาราง
    classification_rule ไม่ใช่ใน enum นี้ เพื่อให้แก้ได้โดยไม่ต้องแก้โค้ด
    """

    NOT_HOTEL = "not_hotel"  # ไม่เข้าข่ายโรงแรม
    TYPE_1 = "type_1"  # ที่พักแรมประเภทที่ 1 (ไม่มีห้องอาหาร)
    TYPE_2 = "type_2"  # ที่พักแรมประเภทที่ 2 (มีห้องอาหาร)
    OUT_OF_SCOPE = "out_of_scope"  # เกินขอบเขตของแพลตฟอร์ม


class ApplicationStatus(StrEnum):
    """สถานะคำขอ — ทุกการเปลี่ยนสถานะต้องเขียน AuditLog (M9)"""

    DRAFT = "draft"  # ร่าง ยังไม่ยื่น
    SUBMITTED = "submitted"  # ยื่นแล้ว รอเจ้าหน้าที่รับเรื่อง
    UNDER_REVIEW = "under_review"  # เจ้าหน้าที่กำลังตรวจเอกสาร
    NEEDS_REVISION = "needs_revision"  # รอผู้ยื่นแก้ไข/ส่งเอกสารเพิ่ม
    APPROVED = "approved"  # อนุมัติแล้ว
    REJECTED = "rejected"  # ไม่อนุมัติ
    LICENSE_ISSUED = "license_issued"  # ออกใบอนุญาตแล้ว


class DocumentStatus(StrEnum):
    """สถานะเอกสารรายฉบับ — ตรงกับ legend 7 สถานะในแบบหน้าจอ

    frontend map สีจากค่านี้ค่าเดียว ห้ามกระจาย logic สีไว้หลายที่
    """

    NOT_UPLOADED = "not_uploaded"  # เทา   — ยังไม่ได้อัปโหลด
    UPLOADED = "uploaded"  # ฟ้า   — อัปโหลดแล้ว รอตรวจ
    SYSTEM_FLAGGED = "system_flagged"  # แดง   — ระบบตรวจพบปัญหา (S1/OCR)
    OFFICER_REVIEWING = "officer_reviewing"  # ม่วง — เจ้าหน้าที่กำลังตรวจ
    REVISION_REQUESTED = "revision_requested"  # ส้ม — เจ้าหน้าที่ขอให้แก้ไข
    APPROVED = "approved"  # เขียว — ผ่านการตรวจ
    NOT_REQUIRED = "not_required"  # ขาว  — ไม่จำเป็นสำหรับกรณีนี้


class DocumentCategory(StrEnum):
    """M3: รายการเอกสารต้องแบ่ง 2 หมวดชัดเจน"""

    SELF = "self"  # ผู้ประกอบการทำเองได้  (รหัส A01, A02, ...)
    EXTERNAL = "external"  # ต้องขอจากหน่วยงานอื่น (รหัส B01, B02, ...)


class AccommodationKind(StrEnum):
    """ลักษณะที่พักในแบบหนังสือแจ้งสถานที่พักที่ไม่เป็นโรงแรม

    เป็นชุดตัวเลือกตายตัวที่มาจากแบบฟอร์มราชการ ไม่ใช่ "กฎเกณฑ์" ที่โจทย์
    บังคับให้ Super Admin แก้เองได้ (ข้อนั้นหมายถึงเงื่อนไขจำแนกประเภท
    ค่าธรรมเนียม รายการเอกสาร และ อปท.) จึงเก็บเป็น enum เหมือนสถานะอื่น
    ถ้าวันหนึ่งแบบฟอร์มเปลี่ยน ค่อยย้ายขึ้นเป็นตารางทีหลัง
    """

    DETACHED_HOUSE = "detached_house"  # บ้านเดี่ยว
    SEMI_DETACHED = "semi_detached"  # บ้านแฝด
    ROW_HOUSE = "row_house"  # ห้องแถว / ตึกแถว
    OTHER = "other"  # อื่น ๆ — ต้องกรอกข้อความระบุเพิ่ม


class ReviewDecision(StrEnum):
    """M8: ผลการตรวจของเจ้าหน้าที่ 3 ทาง"""

    PASS = "pass"  # ผ่าน
    REQUEST_REVISION = "request_revision"  # ขอเอกสารเพิ่ม/ขอแก้ไข
    FAIL = "fail"  # ไม่ผ่าน (ต้องระบุเหตุผล)
