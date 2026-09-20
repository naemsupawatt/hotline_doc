"""เก็บลายมือชื่อผู้ลงนามของเอกสารที่ออกให้ (M10)

ใบอนุญาตและหนังสือรับรองการแจ้งเป็นเอกสารที่ "ออกโดยเจ้าหน้าที่" เดิมหน้าพิมพ์
มีแต่ชื่อเจ้าหน้าที่เป็นข้อความ ซึ่งยังไม่ใช่เอกสารที่ลงนามแล้ว ทีมจึงให้
เจ้าหน้าที่ลงลายมือชื่อตอนกดออกเอกสาร แล้วให้ลายมือชื่อนั้นไปอยู่บนกระดาษ

เก็บเป็น path ของไฟล์รูปเหมือนเอกสารแนบฉบับอื่น ไม่เก็บไบต์ลงฐานข้อมูล
ด้วยเหตุผลเดียวกับ document_file.stored_path คือฐานข้อมูลควรเก็บข้อเท็จจริง
ไม่ใช่เก็บไฟล์ และการสำรองข้อมูลจะหนักขึ้นโดยไม่จำเป็น

ทำไมไม่ใช้ document_file: ตารางนั้นผูกกับ "เอกสารประกอบคำขอ" ที่ต้องมี
document_type และเข้าสู่กระบวนการตรวจของเจ้าหน้าที่ ลายมือชื่อผู้ลงนามเป็น
ส่วนหนึ่งของ "เอกสารที่ระบบออกให้" ไม่ใช่เอกสารที่ผู้ยื่นส่งมาให้ตรวจ

Revision ID: 5b1e70c4a9d2
Revises: 3547ea295ce1
Create Date: 2026-09-20 03:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5b1e70c4a9d2"
down_revision: str | None = "3547ea295ce1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ว่างได้ เพราะใบที่ออกไปก่อนหน้านี้ยังไม่มีลายมือชื่อเก็บไว้
    op.add_column(
        "license", sa.Column("issuer_signature_path", sa.String(length=255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("license", "issuer_signature_path")
