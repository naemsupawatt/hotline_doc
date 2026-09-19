"""ตัดคอลัมน์ birth_date ออกจาก app_user

โจทย์ไม่ได้ขอวันเดือนปีเกิดในส่วนใดเลย และไม่มีโค้ดส่วนไหนอ่านค่านี้
การเก็บข้อมูลส่วนบุคคลที่ไม่มีวัตถุประสงค์ใช้งานขัดกับข้อควรคิดของโจทย์ข้อ 8
เรื่องการจำกัดข้อมูลส่วนบุคคล จึงตัดออกแทนที่จะเก็บไว้เฉย ๆ

ช่องทางติดต่อที่ระบบต้องใช้จริงคือเบอร์โทรศัพท์ (M1) ซึ่งมีคอลัมน์ phone
อยู่แล้วตั้งแต่ migration แรก รอบนี้จึงไม่ต้องเพิ่มคอลัมน์ใหม่

Revision ID: 7f21c0d94e3a
Revises: ec2dff28b63d
Create Date: 2026-09-19 20:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7f21c0d94e3a"
down_revision: str | None = "ec2dff28b63d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("app_user", "birth_date")


def downgrade() -> None:
    # กลับมาเป็น nullable เหมือนเดิม ข้อมูลเดิมกู้คืนไม่ได้เพราะถูกลบไปแล้ว
    op.add_column("app_user", sa.Column("birth_date", sa.Date(), nullable=True))
