"""คำขอ และประวัติการเปลี่ยนสถานะ"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin
from app.models.enums import ApplicationStatus


class Application(Base, TimestampMixin):
    """คำขอหนึ่งใบ

    local_authority_id ทำสำเนามาไว้ที่นี่ (แม้จะหาผ่าน property ได้)
    เพราะทุก query ของเจ้าหน้าที่กรองด้วยเขตนี้ (M8, T-09) และเขตที่ใช้
    ตัดสินต้องเป็นเขต ณ วันยื่น ไม่ใช่เขตปัจจุบันของ property ถ้าถูกแก้ทีหลัง
    """

    __tablename__ = "application"

    id: Mapped[int] = mapped_column(primary_key=True)
    # M6: "ต้องออกเลขที่คำขอให้ผู้ยื่นใช้อ้างอิง" เช่น PKT-2569-000123
    application_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)

    operator_id: Mapped[int] = mapped_column(ForeignKey("operator.id"), nullable=False)
    property_id: Mapped[int] = mapped_column(ForeignKey("property.id"), nullable=False)
    local_authority_id: Mapped[int] = mapped_column(
        ForeignKey("local_authority.id"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(
        String(24), server_default=ApplicationStatus.DRAFT, nullable=False, index=True
    )
    # M7: "ใครกำลังดำเนินการ"
    assigned_officer_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))

    # M7: "รออยู่กี่วันแล้ว" = now() - status_changed_at (คำนวณตอน query ไม่เก็บค่า)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision_reason: Mapped[str | None] = mapped_column(Text())  # บังคับเมื่อไม่อนุมัติ

    history: Mapped[list[ApplicationStatusHistory]] = relationship(
        back_populates="application", order_by="ApplicationStatusHistory.changed_at"
    )


class ApplicationStatusHistory(Base):
    """ประวัติการเปลี่ยนสถานะของคำขอ (M9)

    ไม่ใช้ TimestampMixin เพราะแถวนี้ "ไม่มีวันถูกแก้" — มีแต่ changed_at
    ที่ประทับจากฐานข้อมูล ตาม NFR "บันทึกเวลาอัตโนมัติจากระบบ"
    """

    __tablename__ = "application_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("application.id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(24))  # NULL = ตอนสร้างคำขอ
    to_status: Mapped[str] = mapped_column(String(24), nullable=False)
    changed_by_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"))
    note: Mapped[str | None] = mapped_column(Text())
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    application: Mapped[Application] = relationship(back_populates="history")
