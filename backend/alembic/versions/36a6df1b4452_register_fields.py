"""เพิ่มฟิลด์สำหรับการสมัครสมาชิก: ชื่อ-นามสกุล เลขบัตรประชาชน วันเกิด

แยก full_name เดิมออกเป็น first_name + last_name เพื่อไม่เก็บค่าที่คำนวณได้ซ้ำ
(ชื่อเต็มกลายเป็น property ในโมเดลแทน)

Revision ID: 36a6df1b4452
Revises: be2a1464a844
Create Date: 2026-09-19 15:17:50.657950
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "36a6df1b4452"
down_revision: str | None = "be2a1464a844"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UQ_NATIONAL_ID = "uq_app_user_national_id"


def upgrade() -> None:
    # เพิ่มแบบ nullable ก่อน เพราะตารางมีข้อมูลผู้ใช้อยู่แล้ว
    # ถ้าใส่ NOT NULL ตั้งแต่แรก migration จะล้มทันทีบนฐานข้อมูลที่ไม่ว่าง
    op.add_column("app_user", sa.Column("first_name", sa.String(length=80), nullable=True))
    op.add_column("app_user", sa.Column("last_name", sa.String(length=80), nullable=True))
    op.add_column("app_user", sa.Column("national_id", sa.String(length=13), nullable=True))
    op.add_column("app_user", sa.Column("birth_date", sa.Date(), nullable=True))

    # ย้ายข้อมูลเดิม: ตัดคำแรกเป็นชื่อ ที่เหลือเป็นนามสกุล
    # แถวที่ไม่มีช่องว่างเลยจะได้ last_name = '-' เพื่อให้ NOT NULL ผ่าน
    op.execute(
        """
        UPDATE app_user
        SET first_name = split_part(full_name, ' ', 1),
            last_name  = COALESCE(
                NULLIF(substr(full_name, strpos(full_name, ' ') + 1), full_name),
                '-'
            )
        """
    )

    op.alter_column("app_user", "first_name", nullable=False)
    op.alter_column("app_user", "last_name", nullable=False)

    # ตั้งชื่อ constraint เองเสมอ ไม่งั้น downgrade จะอ้างถึงไม่ได้
    op.create_unique_constraint(UQ_NATIONAL_ID, "app_user", ["national_id"])

    op.drop_column("app_user", "full_name")


def downgrade() -> None:
    op.add_column("app_user", sa.Column("full_name", sa.VARCHAR(length=160), nullable=True))
    op.execute("UPDATE app_user SET full_name = trim(first_name || ' ' || last_name)")
    op.alter_column("app_user", "full_name", nullable=False)

    op.drop_constraint(UQ_NATIONAL_ID, "app_user", type_="unique")
    op.drop_column("app_user", "birth_date")
    op.drop_column("app_user", "national_id")
    op.drop_column("app_user", "last_name")
    op.drop_column("app_user", "first_name")
