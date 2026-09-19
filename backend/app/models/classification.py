"""การจำแนกประเภทที่พัก — หัวใจของ M2 และ US-09

โจทย์ข้อ 4 บังคับว่า "ทีมต้องออกแบบระบบให้แก้ไขเงื่อนไขและอัตราค่าธรรมเนียม
ได้ในภายหลังโดยไม่ต้องแก้โค้ด" → เงื่อนไขทุกตัวเลขอยู่ในตาราง classification_rule
โค้ดมีแต่ "เครื่องมือเทียบ" ไม่มีตัวเลขของกฎอยู่เลย

วิธีประเมิน (อยู่ใน services/classification.py):
  เรียงตาม priority น้อย→มาก  แล้วเอากฎแรกที่เงื่อนไขครบทุกข้อ (AND)
  ช่องที่เป็น NULL = "ไม่สนใจเงื่อนไขข้อนี้"

--------------------------------------------------------------------------
กับดัก T-02 และเหตุผลที่กฎถูกวางแบบนี้ (อ่านก่อนแก้ลำดับ priority)
--------------------------------------------------------------------------
ตารางข้อ 4 เขียนเงื่อนไขประเภทที่ 1/2 ว่า "ห้องพักมากกว่า 8 ห้อง แต่ไม่เกิน 49"
ถ้าแปลตรงตัวเป็น min_rooms=9 จะเกิด "ช่องโหว่" ทันที:

    T-02: ที่พัก 8 ห้อง แต่รับ 36 คน
      - ไม่เข้าเงื่อนไข "ไม่เข้าข่ายโรงแรม"  (คน 36 > 30)
      - ไม่เข้าเงื่อนไขประเภท 1/2 ด้วย       (ห้อง 8 ไม่ > 8)
      → ระบบตอบไม่ได้ ทั้งที่โจทย์เฉลยว่าต้อง "เข้าข่ายต้องขอใบอนุญาต"

อ่านให้ถูกคือ "ไม่เข้าข่ายโรงแรม" เป็นข้อ*ยกเว้น* ที่ต้องเข้าเงื่อนไขครบทั้งคู่
(ห้อง ≤ 8 และ คน ≤ 30) ถ้าหลุดข้อใดข้อหนึ่ง = เป็นโรงแรม แล้วค่อยไปแยก
ประเภทตามห้องอาหาร กฎประเภท 1/2 จึงตั้ง max_rooms=49 โดย **ไม่ใส่ min_rooms**
ให้ลำดับ priority เป็นตัวรับประกันว่ากรณียกเว้นถูกคัดออกไปก่อนแล้ว
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class PropertyType(Base, TimestampMixin):
    """ประเภทที่พัก 4 แบบตามตารางข้อ 4 — code ตรงกับ enum ClassificationResult"""

    __tablename__ = "property_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name_th: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())

    # ใช้ตัดสินว่าจะพาผู้ใช้ไป flow ยื่นคำขอ หรือ flow แจ้งเฉย ๆ
    requires_license: Mapped[bool] = mapped_column(
        Boolean, server_default="true", nullable=False
    )
    # กรณี "เกินขอบเขตของระบบ" — แสดงคำแนะนำให้ติดต่อนายทะเบียนโดยตรง
    is_out_of_scope: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )
    display_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)

    rules: Mapped[list[ClassificationRule]] = relationship(back_populates="property_type")


class ClassificationRule(Base, TimestampMixin):
    """ชุดเงื่อนไขจำแนกประเภทที่ Super Admin แก้ได้เองผ่านหน้าจอ (US-09)

    ทุกช่วงเป็น inclusive: min_rooms <= room_count <= max_rooms
    NULL = ไม่จำกัดด้านนั้น
    """

    __tablename__ = "classification_rule"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    property_type_id: Mapped[int] = mapped_column(
        ForeignKey("property_type.id"), nullable=False
    )

    # กฎแรกที่ match ชนะ — เว้นเลขห่าง ๆ (10,20,30) ให้แทรกกฎใหม่ได้โดยไม่ต้องเรียงใหม่
    priority: Mapped[int] = mapped_column(Integer, nullable=False)

    min_rooms: Mapped[int | None] = mapped_column(Integer)
    max_rooms: Mapped[int | None] = mapped_column(Integer)
    min_guests: Mapped[int | None] = mapped_column(Integer)
    max_guests: Mapped[int | None] = mapped_column(Integer)

    # tri-state: True=ต้องมีห้องอาหาร, False=ต้องไม่มี, NULL=ไม่สนใจ
    requires_restaurant: Mapped[bool | None] = mapped_column(Boolean)

    # M2 "แสดงผลสรุปพร้อมเหตุผลว่าทำไมจึงได้ผลนั้น"
    # ใส่ placeholder ได้: {rooms} {guests} {restaurant}
    reason_template: Mapped[str] = mapped_column(Text(), nullable=False)
    outcome_message: Mapped[str] = mapped_column(Text(), nullable=False)

    # กฎหมายเปลี่ยนได้ → เก็บช่วงเวลามีผล ไม่ลบกฎเก่าทิ้ง
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    property_type: Mapped[PropertyType] = relationship(back_populates="rules")

    def matches(self, rooms: int, guests: int, has_restaurant: bool) -> bool:
        """เทียบเงื่อนไขทุกข้อแบบ AND — ข้อที่เป็น NULL ถือว่าผ่าน

        เขียนไว้บน model เพื่อให้ unit test เรียกได้ตรง ๆ โดยไม่ต้องมี DB
        แต่ "ค่า" ที่เทียบมาจากฐานข้อมูลทั้งหมด ไม่มี literal ของกฎในโค้ด
        """
        if self.min_rooms is not None and rooms < self.min_rooms:
            return False
        if self.max_rooms is not None and rooms > self.max_rooms:
            return False
        if self.min_guests is not None and guests < self.min_guests:
            return False
        if self.max_guests is not None and guests > self.max_guests:
            return False
        if self.requires_restaurant is not None and has_restaurant != self.requires_restaurant:
            return False
        return True


class ApplicationClassification(Base, TimestampMixin):
    """ผลการจำแนกของคำขอแต่ละรายการ — เก็บเป็น snapshot

    ทำไมต้อง snapshot: ถ้า Super Admin แก้กฎพรุ่งนี้ คำขอที่จำแนกไว้วันนี้
    ต้องยังอธิบายได้ว่า "ตอนนั้นตัดสินด้วยกฎข้อไหน ด้วยตัวเลขอะไร"
    (เหตุผลเดียวกับที่ License ต้อง snapshot ค่าธรรมเนียม — ดู license.py)
    """

    __tablename__ = "application_classification"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("application.id"), unique=True, nullable=False
    )
    property_type_id: Mapped[int] = mapped_column(
        ForeignKey("property_type.id"), nullable=False
    )
    matched_rule_id: Mapped[int | None] = mapped_column(ForeignKey("classification_rule.id"))

    # ค่าที่ผู้ใช้ตอบใน wizard ตอนจำแนก (ไม่ใช่ค่าปัจจุบันของ property)
    answered_rooms: Mapped[int] = mapped_column(Integer, nullable=False)
    answered_guests: Mapped[int] = mapped_column(Integer, nullable=False)
    answered_has_restaurant: Mapped[bool] = mapped_column(Boolean, nullable=False)

    reason_text: Mapped[str] = mapped_column(Text(), nullable=False)
    classified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    property_type: Mapped[PropertyType] = relationship()
    matched_rule: Mapped[ClassificationRule | None] = relationship()
