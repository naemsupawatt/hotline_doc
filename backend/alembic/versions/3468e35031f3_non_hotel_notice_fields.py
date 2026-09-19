"""รองรับแบบหนังสือแจ้งฯ: ลักษณะที่พัก เอกสารกรอกในระบบ และแนบหลายไฟล์

เตรียมทางให้เส้น "ไม่เข้าข่ายโรงแรม" ซึ่งมีเอกสาร 6 รายการ:
  - แบบหนังสือแจ้งฯ เป็นเอกสารที่ "กรอกในระบบ" ไม่ใช่ไฟล์ที่ผู้ใช้อัปโหลด
    -> document_type.is_system_form
  - ภาพถ่ายอาคารแนบได้หลายมุม -> document_file.slot_no + แก้ unique constraint
    (แยกจาก version_no ที่แปลว่า "ไฟล์เดิมส่งใหม่" ตามกฎข้อ 5 ของทีม)
  - แต่ละฉบับรับชนิดไฟล์ต่างกัน (บางฉบับ PDF เท่านั้น) -> document_type.accepted_mime
  - ลักษณะที่พักเป็นคุณสมบัติของที่พัก ไม่ใช่ของเอกสาร -> เก็บที่ property (3NF)

Revision ID: 3468e35031f3
Revises: 7f21c0d94e3a
Create Date: 2026-09-19 20:38:45.676609
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3468e35031f3"
down_revision: str | None = "7f21c0d94e3a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_file", sa.Column("slot_no", sa.Integer(), server_default="1", nullable=False)
    )
    op.drop_constraint(op.f("uq_docfile_version"), "document_file", type_="unique")
    op.create_unique_constraint(
        "uq_docfile_version",
        "document_file",
        ["application_id", "document_type_id", "slot_no", "version_no"],
    )
    op.add_column(
        "document_type",
        sa.Column("is_system_form", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "document_type",
        sa.Column("allows_multiple", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "document_type",
        sa.Column(
            "accepted_mime",
            sa.String(length=200),
            server_default="application/pdf,image/jpeg,image/png",
            nullable=False,
        ),
    )
    op.add_column("property", sa.Column("accommodation_kind", sa.String(length=24), nullable=True))
    op.add_column(
        "property", sa.Column("accommodation_kind_other", sa.String(length=120), nullable=True)
    )


def downgrade() -> None:
    # หมายเหตุ: ถ้ามีเอกสารที่แนบหลายไฟล์อยู่แล้ว การคืน unique constraint เดิม
    # จะล้มเพราะ slot 1 กับ 2 จะกลายเป็นคู่ซ้ำ ต้องลบไฟล์ slot > 1 ก่อน downgrade
    op.drop_column("property", "accommodation_kind_other")
    op.drop_column("property", "accommodation_kind")
    op.drop_column("document_type", "accepted_mime")
    op.drop_column("document_type", "allows_multiple")
    op.drop_column("document_type", "is_system_form")
    op.drop_constraint("uq_docfile_version", "document_file", type_="unique")
    op.create_unique_constraint(
        op.f("uq_docfile_version"),
        "document_file",
        ["application_id", "document_type_id", "version_no"],
    )
    op.drop_column("document_file", "slot_no")
