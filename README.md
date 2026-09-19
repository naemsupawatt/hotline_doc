# HoTLinE Doc

ระบบยื่นขอใบอนุญาตประกอบธุรกิจโรงแรมและที่พักแรมแบบออนไลน์ จังหวัดภูเก็ต
— โจทย์ Hackathon ที่ 2 ชุดวิชา 977-121 วิทยาลัยการคอมพิวเตอร์ ม.อ. ภูเก็ต

> **ข้อมูลทั้งหมดในระบบนี้เป็นข้อมูลจำลองสำหรับการสาธิตเท่านั้น**
> ไม่มีข้อมูลส่วนบุคคลจริงของผู้ใด ตามกติกาข้อ 14 ของโจทย์

## เทคโนโลยี

| ส่วน | เทคโนโลยี | พอร์ต |
|---|---|---|
| Frontend | Next.js 16 (App Router) + TypeScript + Tailwind v4 | 3000 |
| Backend | FastAPI + SQLAlchemy 2 + Alembic (Python 3.13) | 8000 |
| Database | PostgreSQL 16 | 5432 |

เอกสาร API สร้างอัตโนมัติจาก FastAPI ที่ **http://localhost:8000/docs**
ใช้เป็นส่งมอบข้อ "เอกสาร API พร้อมตัวอย่าง request/response" ได้เลย

## เริ่มใช้งาน

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1     # ครั้งแรกครั้งเดียว
powershell -ExecutionPolicy Bypass -File scripts\git-setup.ps1 # ตั้งชื่อสมาชิกก่อนใช้
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1       # เปิดทั้ง 2 ฝั่ง
```

เปิด http://localhost:3000 จะเห็นหน้าตรวจสอบระบบดีไซน์
(โลโก้ มาสคอต สถานะ 7 แบบ คอมโพเนนต์กลาง) — ถ้าหน้านี้ขึ้นครบแปลว่าโครงพร้อม

## โครงสร้างโปรเจกต์

```
backend/
  app/
    main.py            จุดเริ่มแอป + CORS + mount router
    core/              config (อ่านจาก .env) / db / security (hash, JWT)
    models/            SQLAlchemy models + enums (สถานะทั้งระบบ)
    schemas/           Pydantic request/response -> กลายเป็น /docs อัตโนมัติ
    api/v1/            endpoint แยกตามโดเมน 7 กลุ่ม
    services/          business logic (ไม่ปนใน endpoint)
    seeds/             ข้อมูลตั้งต้น เช่น อปท. 19 แห่ง
  alembic/             migration
  storage/             ไฟล์ที่ผู้ใช้อัปโหลด (ไม่ commit)

frontend/
  public/brand/        โลโก้ 3 แบบ x 3 ขนาด (webp)
  public/mascot/       มาสคอต 6 ท่า x 3 ขนาด (webp)
  src/app/             App Router แยกตามบทบาทผู้ใช้
    (public)/          หน้าสาธารณะ + wizard ประเมินที่พัก
    (operator)/        ผู้ประกอบการ
    (officer)/         เจ้าหน้าที่ท้องถิ่น
    (central)/         หน่วยงานส่วนกลาง
    (admin)/           Super Admin
  src/components/
    brand/             Logo, Mascot
    common/            คอมโพเนนต์กลางที่ใช้ซ้ำทุกหน้า
    ui/                (เผื่อ shadcn/ui — npx shadcn@latest add <name>)
  src/lib/             api client, utils
  src/types/           enums ที่ต้องตรงกับฝั่ง backend

docs/                  ส่งมอบข้อ 1, 2, 3, 5, 6
scripts/               setup / dev / git-setup
```

## กติกาของโค้ดที่ทีมตกลงกัน

1. **ห้าม hard-code กฎเกณฑ์** — เงื่อนไขจำแนกประเภท ค่าธรรมเนียม รายการเอกสาร
   และข้อมูล อปท. ต้องอ่านจากฐานข้อมูล เพราะโจทย์บังคับว่าต้องแก้ได้โดยไม่แก้โค้ด
2. **สีอยู่ที่ `globals.css` ที่เดียว** ห้ามเขียน `#xxxxxx` ในคอมโพเนนต์
3. **สถานะ -> สี/ข้อความ อยู่ที่ `StatusPill.tsx` ที่เดียว**
4. **เวลาประทับจากฐานข้อมูลเสมอ** (`server_default=func.now()`) ห้ามให้ผู้ใช้กรอกเวลาเอง
5. **อัปโหลดไฟล์ซ้ำ = สร้างรุ่นใหม่** ไม่ทับของเดิม เพราะต้องย้อนดูไฟล์ที่เจ้าหน้าที่เคยตรวจได้
6. **`git push` ทุกครั้งที่สลับคนจับคีย์บอร์ด** — เครื่องมีเครื่องเดียว push คือ backup เดียวที่มี

## ข้อควรระวังที่เสียคะแนนง่าย

- **T-02**: เงื่อนไข "ไม่เข้าข่ายโรงแรม" คือ ห้อง ≤ 8 **และ** คน ≤ 30
  ที่พัก 8 ห้องแต่รับ 36 คน ต้องตอบว่า **เข้าข่ายต้องขอใบอนุญาต**
- **T-09**: เจ้าหน้าที่เปิดคำขอข้ามเขตต้องถูกปฏิเสธ **และบันทึกความพยายามนั้นไว้**
- **M6**: ต้องบล็อกการยื่นเมื่อเอกสารบังคับไม่ครบ พร้อมระบุว่าขาดฉบับใด
