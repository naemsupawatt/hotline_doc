"""ผู้ใช้ สิทธิ์ และการผูกเจ้าหน้าที่เข้ากับ อปท. ที่รับผิดชอบ

NFR ความปลอดภัย: password_hash เก็บ bcrypt เท่านั้น ห้ามเก็บ plaintext
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin
from app.models.enums import UserRole


class User(Base, TimestampMixin):
    """M1: สมัคร/เข้าสู่ระบบด้วยอีเมลหรือเบอร์โทร + ยืนยันตัวตน

    role เก็บเป็น string ตรงกับ UserRole (enums.py) ไม่ใช้ native PG enum
    เพราะการเพิ่มบทบาทใหม่จะต้อง ALTER TYPE ซึ่งยุ่งกับ migration ตอนแข่ง
    """

    __tablename__ = "app_user"  # เลี่ยงชื่อ "user" ซึ่งเป็น reserved word ของ PostgreSQL

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str | None] = mapped_column(String(160), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str] = mapped_column(String(20), server_default=UserRole.OPERATOR, nullable=False)

    # M1 "กลไกยืนยันตัวตนเพื่อแยกผู้ใช้จริงออกจากบัญชีขยะ"
    is_verified: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_code: Mapped[str | None] = mapped_column(String(10))

    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # S6: เลขอ้างอิงแบบไม่ระบุตัวตนสำหรับรายงานภาระงานเจ้าหน้าที่
    # เก็บที่นี่ (ไม่ใช่คำนวณสด) เพื่อให้ส่วนกลางเห็นเลขเดิมทั้งรอบรายงาน
    # แต่ยังย้อนกลับหาตัวบุคคลได้เมื่อมีสิทธิ์พอ
    pseudonym_code: Mapped[str | None] = mapped_column(String(16), unique=True)

    assignments: Mapped[list[OfficerAssignment]] = relationship(back_populates="officer")


class OfficerAssignment(Base, TimestampMixin):
    """ผูกเจ้าหน้าที่เข้ากับ อปท. — ฐานของการกันข้ามเขต (M8, T-09)

    แยกเป็นตาราง many-to-many แทนคอลัมน์เดียวใน User เพราะเจ้าหน้าที่
    หนึ่งคนอาจดูแลมากกว่าหนึ่ง อปท. (เช่น อบจ. ที่ครอบทั้งจังหวัด)
    """

    __tablename__ = "officer_assignment"
    __table_args__ = (
        UniqueConstraint("officer_id", "local_authority_id", name="uq_officer_authority"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    officer_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    local_authority_id: Mapped[int] = mapped_column(
        ForeignKey("local_authority.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    officer: Mapped[User] = relationship(back_populates="assignments")
