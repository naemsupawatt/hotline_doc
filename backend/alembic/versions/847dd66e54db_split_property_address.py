"""แยกที่อยู่ที่พักเป็นช่องย่อยตามแบบฟอร์มราชการ

เดิมเก็บที่อยู่เป็นข้อความก้อนเดียว ซึ่งเอาไปกรอกลงแบบหนังสือแจ้งฯ
ที่มีช่องแยก (บ้านเลขที่ / หมู่ / ซอย / ถนน / ตำบล / อำเภอ / จังหวัด /
รหัสไปรษณีย์) ไม่ได้ และสรุปรายอำเภอรายตำบลให้ส่วนกลางก็ไม่ได้ (M11)

การย้ายข้อมูลเดิม: ข้อความก้อนเดิมแยกเป็นช่องด้วยโปรแกรมอย่างแม่นยำไม่ได้
จึงยกไปไว้ที่ address_no ทั้งก้อน (ไม่ทิ้งข้อมูล) แล้วเติมช่องที่เหลือด้วย
ค่าแทนที่ซึ่งมองออกทันทีว่าต้องกรอกใหม่ ส่วน "อำเภอ" ดึงจาก อปท. ให้เท่าที่ทำได้
โปรเจกต์นี้ตอนย้ายมีที่พักอยู่แถวเดียวซึ่งเป็นข้อมูลทดสอบ

Revision ID: 847dd66e54db
Revises: 3468e35031f3
Create Date: 2026-09-19 21:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "847dd66e54db"
down_revision: str | None = "3468e35031f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ระบบนี้รับเฉพาะจังหวัดภูเก็ตตามขอบเขตของโจทย์
DEFAULT_PROVINCE = "ภูเก็ต"
PLACEHOLDER = "-"
PLACEHOLDER_POSTAL = "00000"

NEW_COLUMNS = [
    ("address_no", sa.String(length=40)),
    ("moo", sa.String(length=20)),
    ("soi", sa.String(length=80)),
    ("road", sa.String(length=80)),
    ("sub_district", sa.String(length=80)),
    ("district", sa.String(length=80)),
    ("province", sa.String(length=80)),
    ("postal_code", sa.String(length=5)),
]

# ช่องที่บังคับกรอก — เพิ่มแบบ nullable ก่อนเสมอ แล้วค่อยบังคับหลัง backfill
# ถ้าใส่ NOT NULL ตั้งแต่แรก migration จะล้มทันทีบนตารางที่มีข้อมูลอยู่
REQUIRED = ["address_no", "sub_district", "district", "province", "postal_code"]


def upgrade() -> None:
    for name, type_ in NEW_COLUMNS:
        op.add_column("property", sa.Column(name, type_, nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE property AS p
            SET address_no   = COALESCE(NULLIF(left(trim(p.address), 40), ''), :ph),
                sub_district = :ph,
                district     = CASE
                                 WHEN la.district IS NULL THEN :ph
                                 WHEN la.district = 'ทั้งจังหวัด' THEN :ph
                                 ELSE la.district
                               END,
                province     = :province,
                postal_code  = :postal
            FROM local_authority AS la
            WHERE la.id = p.local_authority_id
            """
        ).bindparams(ph=PLACEHOLDER, province=DEFAULT_PROVINCE, postal=PLACEHOLDER_POSTAL)
    )

    # เผื่อแถวที่ local_authority_id ชี้ไปยังแถวที่ไม่มีอยู่ (ไม่ควรเกิด แต่กันไว้)
    op.execute(
        sa.text(
            """
            UPDATE property
            SET address_no   = COALESCE(address_no, :ph),
                sub_district = COALESCE(sub_district, :ph),
                district     = COALESCE(district, :ph),
                province     = COALESCE(province, :province),
                postal_code  = COALESCE(postal_code, :postal)
            WHERE address_no IS NULL
               OR sub_district IS NULL
               OR district IS NULL
               OR province IS NULL
               OR postal_code IS NULL
            """
        ).bindparams(ph=PLACEHOLDER, province=DEFAULT_PROVINCE, postal=PLACEHOLDER_POSTAL)
    )

    for name in REQUIRED:
        op.alter_column("property", name, nullable=False)

    op.drop_column("property", "address")


def downgrade() -> None:
    op.add_column("property", sa.Column("address", sa.TEXT(), nullable=True))

    # ประกอบช่องย่อยกลับเป็นข้อความก้อนเดียว
    op.execute(
        sa.text(
            """
            UPDATE property
            SET address = concat_ws(' ',
                    address_no,
                    NULLIF(concat('หมู่ ', moo), 'หมู่ '),
                    NULLIF(concat('ซอย', soi), 'ซอย'),
                    NULLIF(concat('ถนน', road), 'ถนน'),
                    concat('ตำบล', sub_district),
                    concat('อำเภอ', district),
                    concat('จังหวัด', province),
                    postal_code)
            """
        )
    )
    op.alter_column("property", "address", nullable=False)

    for name, _ in reversed(NEW_COLUMNS):
        op.drop_column("property", name)
