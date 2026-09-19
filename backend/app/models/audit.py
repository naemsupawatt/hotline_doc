"""ร่องรอยการทำงาน และการแจ้งเตือน"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AuditLog(Base):
    """M9 + NFR Audit Trail: ใคร ทำอะไร เมื่อใด เปลี่ยนจากอะไรเป็นอะไร

    ไม่มี updated_at เพราะ log แก้ไม่ได้ตามนิยาม — เวลาประทับจาก
    server_default=func.now() ให้ฐานข้อมูลเป็นคนใส่ ผู้ใช้กรอกเองไม่ได้

    T-09 สำคัญ: ตารางนี้ไม่ได้บันทึกแค่สิ่งที่ "ทำสำเร็จ"
    เจ้าหน้าที่ข้ามเขตที่ถูกปฏิเสธต้องถูกบันทึกด้วย outcome='denied'
    โจทย์เขียนไว้ชัดว่า "ระบบปฏิเสธการเข้าถึง *และบันทึกความพยายามนั้นไว้*"
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), index=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)  # submit / approve / view ...

    # ชี้ไปยังแถวไหนก็ได้ในระบบ (application, document_file, fee_schedule, ...)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True)

    from_status: Mapped[str | None] = mapped_column(String(24))
    to_status: Mapped[str | None] = mapped_column(String(24))

    outcome: Mapped[str] = mapped_column(String(12), server_default="success", nullable=False)
    detail: Mapped[str | None] = mapped_column(Text())
    ip_address: Mapped[str | None] = mapped_column(String(45))  # รองรับ IPv6

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Notification(Base):
    """S3/T-08: แจ้งผู้ยื่นเมื่อสถานะเปลี่ยน"""

    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False, index=True)
    application_id: Mapped[int | None] = mapped_column(ForeignKey("application.id"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
