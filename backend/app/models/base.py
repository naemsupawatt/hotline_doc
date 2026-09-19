"""Mixin ที่ใช้ซ้ำในทุกตาราง

TimestampMixin สำคัญกับ NFR เรื่อง Audit Trail ของโจทย์:
"บันทึกเวลาอัตโนมัติจากระบบ ไม่ให้ผู้ใช้กรอกเวลาเอง"
-> ใช้ server_default=func.now() ให้ฐานข้อมูลเป็นคนประทับเวลา
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
