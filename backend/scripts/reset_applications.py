"""ล้างคำขอทดสอบทั้งหมด เพื่อเริ่มทดสอบหรือเดโมจากศูนย์

    cd backend && uv run python -m scripts.reset_applications          # ดูว่าจะลบอะไรบ้าง
    cd backend && uv run python -m scripts.reset_applications --yes    # ลบจริง

**ลบ** คำขอและทุกอย่างที่งอกจากคำขอ: ผลจำแนก ประวัติสถานะ ไฟล์เอกสาร (ทั้งแถว
และไฟล์บนดิสก์) ผลตรวจรายฉบับ เอกสารสิทธิ์ที่ออกไปแล้วพร้อมลายมือชื่อผู้ลงนาม
ที่พักที่ผูกกับคำขอ และรายการ audit ของสิ่งเหล่านั้น

**ไม่ลบ** บัญชีผู้ใช้ (เดโมล็อกอินได้เหมือนเดิม) โปรไฟล์ผู้ประกอบการ และข้อมูล
ตั้งต้นทั้งหมด — กฎจำแนกประเภท ค่าธรรมเนียม รายการเอกสาร หน่วยงาน และ อปท. 19 แห่ง
ถ้าต้องการล้างข้อมูลตั้งต้นด้วย ให้ใช้ alembic downgrade แล้ว seed ใหม่แทน

ลำดับการลบต้องไล่จากลูกไปหาแม่ตาม foreign key ไม่งั้นฐานข้อมูลจะปฏิเสธ
"""

import shutil
import sys

from sqlalchemy import delete, select, text

from app.core.db import SessionLocal
from app.models.application import Application, ApplicationStatusHistory
from app.models.audit import AuditLog
from app.models.classification import ApplicationClassification
from app.models.document import DocumentFile, DocumentReview
from app.models.license import License
from app.models.property import Property
from app.services import document as doc_svc

# entity_type ของ audit ที่เกิดจากคำขอ — แถวเรื่องบัญชีผู้ใช้ (app_user) เก็บไว้
APPLICATION_AUDIT_ENTITIES = ("application", "document_file", "license")

COUNT_SQL = """
select 'คำขอ', count(*) from application
union all select 'ผลจำแนก (snapshot)', count(*) from application_classification
union all select 'ประวัติการเปลี่ยนสถานะ', count(*) from application_status_history
union all select 'ไฟล์เอกสารที่อัปโหลด', count(*) from document_file
union all select 'ผลตรวจรายฉบับ', count(*) from document_review
union all select 'ใบอนุญาต/หนังสือรับรอง', count(*) from license
union all select 'ที่พัก', count(*) from property
"""


def show_counts(db, title: str) -> None:
    print(f"\n{title}")
    for label, count in db.execute(text(COUNT_SQL)):
        print(f"  {label:<26} {count}")


def main() -> int:
    confirmed = "--yes" in sys.argv

    with SessionLocal() as db:
        show_counts(db, "ข้อมูลตอนนี้")

        audit_rows = db.scalar(
            select(AuditLog)
            .where(AuditLog.entity_type.in_(APPLICATION_AUDIT_ENTITIES))
            .with_only_columns(text("count(*)"))
        )
        print(f"  {'รายการ audit ที่เกี่ยวข้อง':<26} {audit_rows}")

        if not confirmed:
            print("\nยังไม่ได้ลบอะไร — สั่งอีกครั้งด้วย --yes ถ้าต้องการลบจริง")
            return 0

        # เก็บชื่อโฟลเดอร์ไฟล์ไว้ก่อน เพราะหลังลบแถวแล้วจะหาไม่ได้อีก
        application_numbers = list(db.scalars(select(Application.application_no)).all())

        db.execute(delete(DocumentReview))
        db.execute(delete(DocumentFile))
        db.execute(delete(License))
        db.execute(delete(ApplicationClassification))
        db.execute(delete(ApplicationStatusHistory))
        db.execute(delete(Application))
        # ที่พักถูกสร้างพร้อมคำขอเสมอ พอไม่มีคำขอก็ไม่มีใครอ้างถึงอีก
        db.execute(delete(Property))
        db.execute(delete(AuditLog).where(AuditLog.entity_type.in_(APPLICATION_AUDIT_ENTITIES)))
        db.commit()

        root = doc_svc.storage_root()
        removed = 0
        for no in application_numbers:
            folder = root / no
            if folder.exists():
                shutil.rmtree(folder, ignore_errors=True)
                removed += 1
        # ลายมือชื่อผู้ลงนามของใบที่ออกไปแล้ว เก็บแยกจากโฟลเดอร์คำขอ
        signatures = root / "licenses"
        if signatures.exists():
            shutil.rmtree(signatures, ignore_errors=True)

        print(f"\nลบไฟล์แนบของคำขอ {removed} ชุด และลายมือชื่อผู้ลงนามทั้งหมดแล้ว")
        show_counts(db, "หลังล้าง")
        print("\nบัญชีผู้ใช้ กฎเกณฑ์ ค่าธรรมเนียม รายการเอกสาร และ อปท. ยังอยู่ครบ")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
