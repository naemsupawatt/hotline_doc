"""แยกชนิดเอกสารสิทธิ์ และให้ค่าธรรมเนียม/วันหมดอายุว่างได้

ที่พักที่ "ไม่เข้าข่ายโรงแรม" ก็ต้องได้เอกสารที่พิมพ์ออกมาได้พร้อมเลขอ้างอิง
ตามที่โจทย์เขียนในตารางข้อ 5 ("พิมพ์ใบอนุญาตหรือเอกสารอ้างอิง") แต่กรณีนั้น
ไม่มีค่าธรรมเนียมและไม่มีวันหมดอายุตามตารางข้อ 4 สามคอลัมน์นี้จึงต้องว่างได้
และเพิ่ม kind ไว้แยกว่าเป็นใบอนุญาตหรือหนังสือรับรองการแจ้ง

ตารางยังว่างอยู่ตอน migrate จึงเติม kind ให้แถวเดิมด้วยค่า license ได้ปลอดภัย

Revision ID: aa7bcc106a08
Revises: 847dd66e54db
Create Date: 2026-09-19 22:56:25.863247
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "aa7bcc106a08"
down_revision: str | None = "847dd66e54db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("license", sa.Column("kind", sa.String(length=20), nullable=True))
    # แถวที่มีอยู่ก่อนหน้าทั้งหมดเป็นใบอนุญาต เพราะยังไม่มีชนิดอื่นในระบบ
    op.execute("UPDATE license SET kind = 'license' WHERE kind IS NULL")
    op.alter_column("license", "kind", nullable=False)
    op.alter_column("license", "fee_schedule_id", existing_type=sa.INTEGER(), nullable=True)
    op.alter_column(
        "license", "fee_amount", existing_type=sa.NUMERIC(precision=12, scale=2), nullable=True
    )
    op.alter_column("license", "valid_until", existing_type=sa.DATE(), nullable=True)


def downgrade() -> None:
    op.alter_column("license", "valid_until", existing_type=sa.DATE(), nullable=False)
    op.alter_column(
        "license", "fee_amount", existing_type=sa.NUMERIC(precision=12, scale=2), nullable=False
    )
    op.alter_column("license", "fee_schedule_id", existing_type=sa.INTEGER(), nullable=False)
    op.drop_column("license", "kind")
