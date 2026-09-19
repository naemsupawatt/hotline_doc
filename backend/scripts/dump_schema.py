"""สร้าง docs/schema.sql ใหม่จากโมเดลปัจจุบัน (deliverable ข้อ 2)

ใช้โมเดลเป็นต้นทาง ไม่ใช่ alembic offline SQL เพราะ alembic จะพ่นออกมา
เป็นลำดับ CREATE แล้วตามด้วย ALTER ของทุก migration ซึ่งอ่านยากสำหรับกรรมการ
ไฟล์นี้ให้ CREATE TABLE ชุดสุดท้ายที่ตรงกับฐานข้อมูลจริง ณ ตอนนี้

รันใหม่ทุกครั้งที่ schema เปลี่ยน:
    cd backend && uv run python -m scripts.dump_schema > ../docs/schema.sql
"""

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

import app.models  # noqa: F401  ต้อง import ก่อน metadata จึงจะเห็นครบทุกตาราง
from app.core.db import Base

HEADER = """-- HoTLinE Doc — โครงสร้างฐานข้อมูล (PostgreSQL)
--
-- ไฟล์นี้สร้างอัตโนมัติ อย่าแก้ด้วยมือ
-- สร้างใหม่ด้วย: cd backend && uv run python -m scripts.dump_schema > ../docs/schema.sql
--
-- คำอธิบายความสัมพันธ์และการนอร์มัลไลเซชันถึง 3NF อยู่ที่ docs/database.md
"""


def main() -> None:
    dialect = postgresql.dialect()
    print(HEADER)

    for table in Base.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=dialect)).strip()
        print(f"{ddl};")
        for index in sorted(table.indexes, key=lambda i: i.name or ""):
            print(f"{str(CreateIndex(index).compile(dialect=dialect)).strip()};")
        print()


if __name__ == "__main__":
    main()
