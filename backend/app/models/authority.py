"""หน่วยงาน: อปท. 19 แห่ง + หน่วยงานที่ออกเอกสาร + จุดติดต่อ

โจทย์ข้อ 4: "ระบบจึงต้องเก็บข้อมูลของท้องถิ่นเป็นข้อมูลในฐานข้อมูล
ไม่ใช่เขียนตายตัวไว้ในโค้ด" — ทุกแถวในนี้ Super Admin แก้ได้ (US-09)
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin


class LocalAuthority(Base, TimestampMixin):
    """องค์กรปกครองส่วนท้องถิ่น — เขตรับผิดชอบของเจ้าหน้าที่ (M8, T-09)"""

    __tablename__ = "local_authority"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)      # อบจ. / เทศบาลนคร / อบต.
    district: Mapped[str] = mapped_column(String(60), nullable=False)  # อำเภอ
    address: Mapped[str | None] = mapped_column(Text())
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(120))
    office_hours: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    contact_points: Mapped[list[ContactPoint]] = relationship(back_populates="local_authority")


class IssuingAgency(Base, TimestampMixin):
    """หน่วยงานที่ออกเอกสารหมวด B (M4) เช่น สำนักงานโยธาฯ, กรมพัฒนาธุรกิจการค้า"""

    __tablename__ = "issuing_agency"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    website: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    contact_points: Mapped[list[ContactPoint]] = relationship(back_populates="issuing_agency")


class ContactPoint(Base, TimestampMixin):
    """จุดติดต่อของหน่วยงาน "ที่ท้องถิ่นใด" (M4)

    แยกตารางเพราะหน่วยงานเดียวกันมีจุดติดต่อต่างกันในแต่ละ อปท.
    (3NF: ที่อยู่/เบอร์ ขึ้นกับคู่ agency+authority ไม่ได้ขึ้นกับ agency อย่างเดียว)
    """

    __tablename__ = "contact_point"
    __table_args__ = (
        UniqueConstraint(
            "issuing_agency_id", "local_authority_id", name="uq_contact_agency_authority"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    issuing_agency_id: Mapped[int] = mapped_column(ForeignKey("issuing_agency.id"), nullable=False)
    local_authority_id: Mapped[int | None] = mapped_column(ForeignKey("local_authority.id"))
    office_name: Mapped[str] = mapped_column(String(160), nullable=False)
    address: Mapped[str | None] = mapped_column(Text())
    phone: Mapped[str | None] = mapped_column(String(40))
    office_hours: Mapped[str | None] = mapped_column(String(120))
    estimated_days: Mapped[int | None] = mapped_column(Integer)  # M4: ใช้เวลาโดยประมาณเท่าใด
    notes: Mapped[str | None] = mapped_column(Text())

    issuing_agency: Mapped[IssuingAgency] = relationship(back_populates="contact_points")
    local_authority: Mapped[LocalAuthority | None] = relationship(back_populates="contact_points")
