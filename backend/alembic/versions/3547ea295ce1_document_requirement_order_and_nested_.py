"""ลำดับเอกสารย้ายไปที่ requirement และรองรับเอกสารย่อยใต้แบบฟอร์ม

สองอย่างที่โครงเดิมทำไม่ได้ พอเพิ่มรายการเอกสารของที่พักแรมประเภท 1/2:

1. เอกสารฉบับเดียวกันถูกใช้หลายประเภท (เอกสารสิทธิ์ที่ดิน ภาพถ่ายอาคาร
   รูปถ่ายผู้แจ้ง) แต่ลำดับในแต่ละรายการไม่เหมือนกัน เพราะของโรงแรมมีแบบ ร.ร.1
   กับ อ.5 นำหน้า ลำดับจึงเป็นคุณสมบัติของ "รายการ" ไม่ใช่ของ "เอกสาร" (3NF)
   -> ย้าย display_order มาไว้ที่ document_requirement

2. แบบ ร.ร.1 มีช่องแนบเอกสารย่อยอยู่ในตัว (หนังสือรับรองนิติบุคคล,
   สำเนาทะเบียนบ้านโรงแรม, หลักฐานความเป็นเจ้าของ) ซึ่งต้องแสดงซ้อนใต้ฉบับแม่
   ไม่ใช่ลอยเป็นรายการแยก -> เพิ่ม document_type.parent_id

ย้ายค่าเดิมจาก document_type.display_order มาให้ requirement ที่มีอยู่แล้ว
รายการของ "ไม่เข้าข่ายโรงแรม" จึงไม่สลับลำดับหลัง migrate

Revision ID: 3547ea295ce1
Revises: aa7bcc106a08
Create Date: 2026-09-20 00:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3547ea295ce1"
down_revision: str | None = "aa7bcc106a08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ตั้งชื่อ constraint เองเสมอ ไม่งั้น downgrade อ้างถึงไม่ได้
FK_PARENT = "fk_document_type_parent"


def upgrade() -> None:
    op.add_column(
        "document_requirement",
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.execute(
        """
        UPDATE document_requirement AS r
        SET display_order = dt.display_order
        FROM document_type AS dt
        WHERE dt.id = r.document_type_id
        """
    )

    op.add_column("document_type", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.create_foreign_key(FK_PARENT, "document_type", "document_type", ["parent_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint(FK_PARENT, "document_type", type_="foreignkey")
    op.drop_column("document_type", "parent_id")
    op.drop_column("document_requirement", "display_order")
