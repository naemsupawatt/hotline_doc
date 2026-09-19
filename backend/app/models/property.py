"""ผู้ประกอบการ และที่พัก (ข้อมูลตั้งต้นของการจำแนกประเภท)"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
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
    address: Mapped[str] = mapped_column(Text(), nullable=False)

    room_count: Mapped[int] = mapped_column(Integer, nullable=False)
    max_guests: Mapped[int] = mapped_column(Integer, nullable=False)
    has_restaurant: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # ผู้ประกอบการปักหมุดบนแผนที่ (ข้อ 5 ของโจทย์)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))

    operator: Mapped[Operator] = relationship(back_populates="properties")
