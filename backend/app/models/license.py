"""ค่าธรรมเนียม และใบอนุญาต"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class FeeSchedule(Base, TimestampMixin):
    """อัตราค่าธรรมเนียม "ที่มีผลตามช่วงเวลา" (ข้อ 8 ของโจทย์)

    แก้อัตราไม่ใช่การ UPDATE แถวเดิม แต่คือปิด effective_to ของแถวเก่า
    แล้วเพิ่มแถวใหม่ — อัตราเดิมจึงยังอยู่ให้ย้อนดูได้เสมอ
    """

    __tablename__ = "fee_schedule"

    id: Mapped[int] = mapped_column(primary_key=True)
    property_type_id: Mapped[int] = mapped_column(ForeignKey("property_type.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), server_default="THB", nullable=False)
    validity_years: Mapped[int] = mapped_column(Integer, nullable=False)  # ตารางข้อ 4 = 5 ปี

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    note: Mapped[str | None] = mapped_column(Text())


class License(Base, TimestampMixin):
    """เอกสารสิทธิ์ที่ระบบออกให้หลังอนุมัติ (M10)

    เก็บสองแบบไว้ในตารางเดียว แยกด้วย kind:
      license         — ใบอนุญาตของที่พักแรมประเภท 1/2 มีค่าธรรมเนียมและวันหมดอายุ
      notice_receipt  — หนังสือรับรองการแจ้งของที่พักที่ "ไม่เข้าข่ายโรงแรม"
                        ไม่มีค่าธรรมเนียมและไม่มีวันหมดอายุ

    รวมไว้ตารางเดียวเพราะทั้งสองแบบมีสิ่งเดียวกันครบ: ผูกกับคำขอหนึ่งใบ
    มีเลขอ้างอิงไม่ซ้ำ ออกโดยเจ้าหน้าที่คนหนึ่ง ณ ท้องถิ่นหนึ่ง และพิมพ์ได้
    ถ้าแยกสองตารางจะต้องเขียน query รวมทุกครั้งที่ทำรายงานส่วนกลาง (M11)

    บทบาทของทั้งคู่ตรงกับที่โจทย์เขียนในตารางข้อ 5 ว่าผู้ประกอบการต้อง
    "พิมพ์ใบอนุญาตหรือเอกสารอ้างอิงเมื่อได้รับอนุมัติ"

    ตอบ "ข้อควรคิด" ข้อ 1 ของโจทย์ข้อ 8 โดยตรง:
    "เมื่ออัตราค่าธรรมเนียมเปลี่ยน ใบอนุญาตที่ออกไปแล้วต้องยังคงอ้างอิงอัตราเดิม"
    → เก็บทั้ง fee_schedule_id (ชี้กลับไปยังอัตราที่ใช้) และ fee_amount
      (คัดลอกตัวเลขมาไว้เลย) ถ้าเก็บแค่ FK แล้วมีคนไปแก้แถวนั้น ใบอนุญาตจะเพี้ยน
    """

    __tablename__ = "license"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("application.id"), unique=True, nullable=False
    )
    # M10: "มีเลขอ้างอิงสำหรับตรวจสอบย้อนกลับ" (C3 ใช้เลขนี้ค้นหา)
    license_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)

    kind: Mapped[str] = mapped_column(String(20), nullable=False)  # LicenseKind

    property_type_id: Mapped[int] = mapped_column(ForeignKey("property_type.id"), nullable=False)
    issued_by_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    local_authority_id: Mapped[int] = mapped_column(
        ForeignKey("local_authority.id"), nullable=False
    )

    # ว่างได้เฉพาะ notice_receipt ซึ่งไม่มีค่าธรรมเนียมตามตารางข้อ 4
    fee_schedule_id: Mapped[int | None] = mapped_column(ForeignKey("fee_schedule.id"))
    fee_amount: Mapped[float | None] = mapped_column(Numeric(12, 2))  # snapshot

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    # ว่าง = ไม่มีกำหนดหมดอายุ (หนังสือรับรองการแจ้ง)
    valid_until: Mapped[date | None] = mapped_column(Date)  # S4: เตือนก่อนหมดอายุ
    is_revoked: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # ลายมือชื่อเจ้าหน้าที่ผู้ลงนาม เก็บเป็นไฟล์รูปเหมือน document_file.stored_path
    # ว่างได้เฉพาะใบที่ออกก่อนระบบจะเก็บลายมือชื่อ (ดู migration 5b1e70c4a9d2)
    issuer_signature_path: Mapped[str | None] = mapped_column(String(255))

    fee_schedule: Mapped[FeeSchedule | None] = relationship()
