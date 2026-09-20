"""ลิงก์แผนที่ของ อปท. และของจุดติดต่อ (M4)

โจทย์ข้อ 4 บังคับให้บอกว่า "ต้องไปติดต่อหน่วยงานใด ที่ท้องถิ่นใด" ชื่อกับที่อยู่
อย่างเดียวยังไม่พอสำหรับคนที่ไม่เคยไป ต้องมีแผนที่ให้กดแล้วนำทางไปได้เลย

เก็บเป็น "ลิงก์" ไม่ใช่พิกัด lat/lng เพราะสิ่งที่ผู้ใช้ต้องการคือกดแล้วเปิดแอป
แผนที่ได้ทันที และ Super Admin แก้เองได้โดยไม่ต้องรู้พิกัด (US-09) ถ้าเก็บพิกัด
ระบบจะต้องมีหน้าจอเลือกหมุดและโค้ดประกอบลิงก์เอง ซึ่งเกินสิ่งที่โจทย์ขอ

ใส่ทั้งสองตารางด้วยเหตุผลเดียวกับที่ contact_point มี address/phone ของตัวเอง
อยู่แล้ว คือจุดติดต่อไม่จำเป็นต้องอยู่ที่เดียวกับสำนักงานใหญ่ของ อปท. เสมอไป
(3NF: ตำแหน่งเป็นคุณสมบัติของสำนักงานนั้น ๆ) ตอน seed คัดลอกจาก อปท. ให้ก่อน
เหมือนที่ทำกับที่อยู่และเบอร์โทร

Revision ID: c4a91d5e77b2
Revises: 5b1e70c4a9d2
Create Date: 2026-09-20 07:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4a91d5e77b2"
down_revision: str | None = "5b1e70c4a9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ว่างได้ — แถวที่ยังไม่มีลิงก์ หน้าจอจะไม่แสดงปุ่มแผนที่
    op.add_column("local_authority", sa.Column("map_url", sa.String(length=500), nullable=True))
    op.add_column("contact_point", sa.Column("map_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("contact_point", "map_url")
    op.drop_column("local_authority", "map_url")
