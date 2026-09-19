"""ผู้ใช้ สิทธิ์ และการผูกเจ้าหน้าที่เข้ากับ อปท. ที่รับผิดชอบ

NFR ความปลอดภัย: password_hash เก็บ bcrypt เท่านั้น ห้ามเก็บ plaintext
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.thai_id import mask as mask_national_id
from app.models.base import TimestampMixin
from app.models.enums import UserRole


class User(Base, TimestampMixin):
    """M1: สมัคร/เข้าสู่ระบบด้วยอีเมลหรือเบอร์โทร

    role เก็บเป็น string ตรงกับ UserRole (enums.py) ไม่ใช้ native PG enum
    เพราะการเพิ่มบทบาทใหม่จะต้อง ALTER TYPE ซึ่งยุ่งกับ migration ตอนแข่ง
    """

    __tablename__ = "app_user"  # เลี่ยงชื่อ "user" ซึ่งเป็น reserved word ของ PostgreSQL

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str | None] = mapped_column(String(160), unique=True)

    # เก็บเป็นตัวเลขล้วนเสมอ (ดู core/phone.py) เพราะใช้เป็นกุญแจเข้าสู่ระบบ
    # อีกทางหนึ่งตาม M1 ถ้าเก็บทั้งแบบมีขีดและไม่มีขีด จะหาไม่เจอสลับกัน
    phone: Mapped[str | None] = mapped_column(String(20), unique=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    # เก็บชื่อ-นามสกุลแยกกัน ไม่เก็บ full_name ซ้ำอีกคอลัมน์
    # (ชื่อเต็มเป็นค่าที่คำนวณได้จากสองคอลัมน์นี้ การเก็บซ้ำจะผิด 3NF)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)

    # ---------- ข้อมูลส่วนบุคคลที่ต้องจำกัดการเข้าถึงเป็นพิเศษ ----------
    # ตอบ "ข้อควรคิด" ข้อสุดท้ายของโจทย์ข้อ 8 โดยตรง
    #
    # ข้อตกลงของระบบนี้:
    #   1. ห้ามใส่ national_id ลงใน response schema ใด ๆ  ใช้ national_id_masked แทน
    #   2. ห้ามเขียนเลขเต็มลง AuditLog หรือ log ไฟล์
    #   3. unique เพื่อกันสมัครซ้ำด้วยเลขเดียวกัน
    #
    # ระบบที่ใช้งานจริงต้องเข้ารหัสคอลัมน์นี้ (เช่น pgcrypto) และแยกสิทธิ์อ่าน
    # ต้นแบบนี้ยังเก็บเป็นข้อความธรรมดาเพราะ key management อยู่นอกขอบเขตการสาธิต
    # และข้อมูลทั้งหมดเป็นข้อมูลจำลองตามกติกาข้อ 14
    national_id: Mapped[str | None] = mapped_column(String(13), unique=True)

    role: Mapped[str] = mapped_column(String(20), server_default=UserRole.OPERATOR, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # S6: เลขอ้างอิงแบบไม่ระบุตัวตนสำหรับรายงานภาระงานเจ้าหน้าที่
    # เก็บที่นี่ (ไม่ใช่คำนวณสด) เพื่อให้ส่วนกลางเห็นเลขเดิมทั้งรอบรายงาน
    # แต่ยังย้อนกลับหาตัวบุคคลได้เมื่อมีสิทธิ์พอ
    pseudonym_code: Mapped[str | None] = mapped_column(String(16), unique=True)

    assignments: Mapped[list[OfficerAssignment]] = relationship(back_populates="officer")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def national_id_masked(self) -> str | None:
        """เลขบัตรแบบปิดบัง — ใช้ค่านี้ทุกครั้งที่ต้องแสดงผลหรือส่งออก API"""
        return mask_national_id(self.national_id) if self.national_id else None


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
