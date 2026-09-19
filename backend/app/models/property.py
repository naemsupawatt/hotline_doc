"""ผู้ประกอบการ และที่พัก (ข้อมูลตั้งต้นของการจำแนกประเภท)"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class Operator(Base, TimestampMixin):
    """ผู้ประกอบการ — แยกจาก User เพราะบัญชีหนึ่งอาจถือหลายกิจการ
    และข้อมูลนิติบุคคลไม่ใช่คุณสมบัติของ "บัญชีผู้ใช้" (3NF)
    """

    __tablename__ = "operator"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_juristic: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    juristic_reg_no: Mapped[str | None] = mapped_column(String(20))  # เลขทะเบียนนิติบุคคล
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    contact_email: Mapped[str | None] = mapped_column(String(160))

    properties: Mapped[list[Property]] = relationship(back_populates="operator")


class Property(Base, TimestampMixin):
    """ที่พัก — room_count / max_guests / has_restaurant คือ 3 ตัวแปรที่
    ClassificationRule ใช้ตัดสิน (ตารางข้อ 4) ห้ามเก็บผลจำแนกไว้ที่นี่
    เพราะกฎแก้ได้ ผลจึงต้องผูกกับคำขอ+กฎที่ใช้ตอนนั้น (ดู classification.py)
    """

    __tablename__ = "property"

    id: Mapped[int] = mapped_column(primary_key=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("operator.id"), nullable=False)
    local_authority_id: Mapped[int] = mapped_column(
        ForeignKey("local_authority.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # ---------- ที่อยู่ แยกเป็นช่องตามแบบฟอร์มราชการ ----------
    # เก็บแยกช่องเพราะแบบหนังสือแจ้งฯ มีช่องว่างให้กรอกทีละช่อง
    # ถ้าเก็บเป็นข้อความก้อนเดียว ระบบจะสร้างเอกสารให้อัตโนมัติไม่ได้
    # และค้นหา/สรุปรายอำเภอหรือรายตำบลก็ทำไม่ได้ (M11 ต้องการ)
    #
    # เก็บ "อำเภอ" กับ "จังหวัด" ไว้ที่นี่ด้วย ทั้งที่ดูเหมือนหาจาก อปท. ได้
    # ด้วยเหตุผลเดียวกับที่ application คัดลอก local_authority_id มาเก็บเอง
    # และ license คัดลอก fee_amount มาเก็บเอง คือ **ที่อยู่บนเอกสารทางกฎหมาย
    # เป็นข้อเท็จจริง ณ วันยื่น** ถ้าดึงสดจากตาราง อปท. แล้ววันหนึ่งมีคนแก้แถวนั้น
    # ที่อยู่บนเอกสารที่ออกไปแล้วจะเปลี่ยนตามย้อนหลัง ซึ่งผิด
    #
    # อีกเหตุผล: อบจ.ภูเก็ต มี district = "ทั้งจังหวัด" ซึ่งไม่ใช่ชื่ออำเภอจริง
    # ที่พักใต้ อบจ. จึงหาอำเภอจาก อปท. ไม่ได้อยู่ดี
    address_no: Mapped[str] = mapped_column(String(40), nullable=False)  # บ้านเลขที่
    moo: Mapped[str | None] = mapped_column(String(20))  # หมู่ที่
    soi: Mapped[str | None] = mapped_column(String(80))  # ซอย
    road: Mapped[str | None] = mapped_column(String(80))  # ถนน
    sub_district: Mapped[str] = mapped_column(String(80), nullable=False)  # ตำบล
    district: Mapped[str] = mapped_column(String(80), nullable=False)  # อำเภอ
    province: Mapped[str] = mapped_column(String(80), nullable=False)  # จังหวัด
    postal_code: Mapped[str] = mapped_column(String(5), nullable=False)  # รหัสไปรษณีย์

    room_count: Mapped[int] = mapped_column(Integer, nullable=False)
    max_guests: Mapped[int] = mapped_column(Integer, nullable=False)
    has_restaurant: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # ลักษณะที่พัก (AccommodationKind) — ช่องหนึ่งในแบบหนังสือแจ้งฯ
    # เก็บที่นี่ ไม่ใช่ที่ตัวหนังสือแจ้ง เพราะเป็นคุณสมบัติของ "ที่พัก" ไม่ใช่ของ "เอกสาร"
    # ถ้าเก็บซ้ำในเอกสารจะผิด 3NF และแก้ที่เดียวไม่ครบเมื่อข้อมูลเปลี่ยน
    accommodation_kind: Mapped[str | None] = mapped_column(String(24))
    accommodation_kind_other: Mapped[str | None] = mapped_column(String(120))

    # ผู้ประกอบการปักหมุดบนแผนที่ (ข้อ 5 ของโจทย์)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))

    operator: Mapped[Operator] = relationship(back_populates="properties")

    @property
    def full_address(self) -> str:
        """ที่อยู่แบบบรรทัดเดียวสำหรับแสดงผล

        คำนวณจากช่องย่อย ไม่เก็บซ้ำอีกคอลัมน์ (3NF) เพราะเป็นค่าที่ได้จาก
        ข้อมูลที่มีอยู่แล้ว ถ้าเก็บไว้ด้วยจะมีโอกาสไม่ตรงกับช่องย่อย
        """
        parts = [
            self.address_no,
            f"หมู่ {self.moo}" if self.moo else None,
            f"ซอย{self.soi}" if self.soi else None,
            f"ถนน{self.road}" if self.road else None,
            f"ตำบล{self.sub_district}",
            f"อำเภอ{self.district}",
            f"จังหวัด{self.province}",
            self.postal_code,
        ]
        return " ".join(p for p in parts if p)
