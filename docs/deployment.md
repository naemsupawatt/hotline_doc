# Deploy HoTLinE Doc บน Vercel และ Supabase

Frontend และ FastAPI รันบน Vercel ส่วน PostgreSQL และไฟล์อยู่บน Supabase
ใช้ข้อมูลจำลองตามกติกาโปรเจกต์

## ค่าฝั่ง backend

ตั้งใน Vercel → โปรเจกต์ backend → Settings → Environments → Production

| Key | Type | Value |
|---|---|---|
| `DATABASE_URL` | Secret | URL PostgreSQL แบบ `postgresql+psycopg://…?sslmode=require` |
| `JWT_SECRET` | Secret | ค่าสุ่มที่เตรียมใน `backend/.env.supabase.local` |
| `STORAGE_BACKEND` | Config | `supabase` |
| `SUPABASE_URL` | Config | Project URL จาก Supabase |
| `SUPABASE_SECRET_KEY` | Secret | Secret key จาก Supabase → Settings → API Keys |
| `SUPABASE_STORAGE_BUCKET` | Config | `hotline-documents` |
| `MAX_UPLOAD_MB` | Config | `10` |
| `CORS_ORIGINS` | Config | `https://hotline-doc.vercel.app` |
| `APP_BASE_URL` | Config | `https://hotline-doc.vercel.app` |

ค่าลับเก็บเฉพาะ backend ไม่มีคีย์ Supabase ใน frontend การเปลี่ยน JWT secret
ทำให้ต้องเข้าสู่ระบบใหม่ ส่วน `DATABASE_URL` ใช้ Session pooler กับโค้ดปัจจุบัน
ถ้าเปลี่ยนเป็น Transaction pooler ภายหลัง ต้องปิด prepared statements และปรับ connection pool ด้วย

## เตรียมฐานข้อมูลและ Storage

ไฟล์ `backend/.env.supabase.local` ถูก Git ignore และตั้งสิทธิ์ 0600
เติม `SUPABASE_SECRET_KEY` ลงไฟล์โดยตรง ไม่ส่งคีย์ในแชทหรือ commit ลง Git

```bash
cd backend
uv run --env-file .env.supabase.local python -m scripts.setup_storage
```

คำสั่งนี้สร้าง bucket แบบ private และตั้งขนาดไฟล์ตาม `MAX_UPLOAD_MB`
ถ้าพบ bucket เดิมเป็น public จะหยุดเพื่อให้แก้เป็น private ก่อน

ฐานข้อมูลที่ตั้งค่าในรอบก่อนมี migration และ seed แล้ว ไม่ต้อง seed ซ้ำ
สำหรับฐานข้อมูลใหม่เท่านั้น:

```bash
uv run --env-file .env.supabase.local alembic upgrade head
uv run --env-file .env.supabase.local python -m app.seeds.run
```

Seed อาจเขียนทับกฎ/ข้อมูลตั้งต้นที่ admin แก้แล้ว จึงไม่ใส่ใน build command
การเปลี่ยนระบบ Storage รอบนี้ใช้คอลัมน์เดิม ไม่ต้องมี migration เพิ่ม

## Deploy และตรวจ

Frontend ตั้ง `NEXT_PUBLIC_API_URL=https://backend-ten-dusky-90.vercel.app/api/v1`
นำโค้ด backend และ frontend รุ่นนี้ขึ้น deployment โดยให้ backend พร้อมก่อน frontend
เพราะ frontend ใหม่ใช้ endpoint `prepare` และ `complete` หลังเปลี่ยน env ต้อง rebuild/redeploy

ตรวจด้วยข้อมูลจำลอง:

1. สมัคร/เข้าสู่ระบบ และเปิดคำขอ
2. แนบ PDF ขนาดเกิน 4.5 MB แต่ไม่เกิน 10 MB
3. ส่งไฟล์เดิมใหม่แล้วตรวจว่าเป็น version ใหม่ และไฟล์เก่ายังเปิดได้
4. ลงลายมือชื่อในแบบฟอร์ม ยื่นคำขอ เจ้าหน้าที่ตรวจและออกเอกสารพร้อมลายเซ็น
5. เปิดไฟล์จากฝั่งผู้ยื่นและเจ้าหน้าที่ที่มีสิทธิ์ และตรวจว่าข้ามเขตถูกปฏิเสธ
6. Redeploy backend แล้วเปิดเอกสารเดิมได้อีกครั้ง

การส่งอีเมลต้องตั้ง `EMAIL_BACKEND=smtp` และค่า `SMTP_*` เพิ่มตาม `.env.example`
ค่าเริ่มต้น outbox ใช้สำหรับพัฒนา ไม่ใช่ที่เก็บอีเมลถาวรบน Vercel

## การเก็บไฟล์และสิทธิ์

- ค่าเริ่มต้น `STORAGE_BACKEND=local` ใช้ดิสก์เหมือนเดิม เหมาะกับพัฒนา/เทสต์
- ไฟล์คลาวด์มี `supabase:` นำหน้า `stored_path` ส่วนไฟล์ local เดิมยังอ่านจากดิสก์
  จึงต้องย้ายไฟล์ local แยกหากมีข้อมูลเดิมจริง การตั้งค่า env ไม่ย้ายไฟล์ให้อัตโนมัติ
- Frontend ขออนุญาตอัปโหลดจาก backend ก่อน จากนั้น PUT ไป staging ใน Storage
  ผ่าน URL ชั่วคราว จึงไม่ชนเพดาน request body ของ Vercel
- Backend ตรวจเจ้าของ สถานะคำขอ ชนิดและขนาดจริงที่อ่านกลับจาก Storage
  แล้วเขียน bytes ที่ตรวจแล้วไปยังชื่อใหม่ที่ผู้ยื่นไม่มีสิทธิ์เขียนทับ
  บันทึกแถวและ audit หลังเขียนไฟล์สำเร็จ กฎชนิดไฟล์ยังอ่านจากฐานข้อมูล
- Ticket ผูกกับผู้ยื่น/คำขอ/ชนิดเอกสาร/slot และหมดอายุใน 30 นาที
  การยืนยันซ้ำขณะคำขอยังแก้ไขได้คืนไฟล์เดิม ไม่สร้าง version ซ้ำ
- ดาวน์โหลดผ่านการตรวจสิทธิ์ใน backend ก่อนออก URL อายุ 60 วินาที
  Frontend ดึง bytes จาก Storage โดยไม่ส่ง JWT ของแอปหรือ Secret key ไปด้วย
- ลายเซ็นเจ้าหน้าที่ที่วาดบนหน้าจอส่งผ่าน endpoint เดิม แล้วเก็บใน Storage เช่นเดียวกัน

การยกเลิกอัปโหลดอาจเหลือ staging object ซึ่งไม่นับเป็นเอกสารของคำขอ
ตรวจและลบเฉพาะ staging ที่เกิน 3 ชั่วโมง (พ้นอายุ signed upload URL 2 ชั่วโมง):

```bash
uv run --env-file .env.supabase.local python -m scripts.cleanup_staging
uv run --env-file .env.supabase.local python -m scripts.cleanup_staging --yes
```

คำสั่ง reset applications รองรับการลบไฟล์คลาวด์ผ่าน Storage API ด้วย
อย่าใช้ reset กับข้อมูลที่ต้องเก็บไว้

อ้างอิง: [Supabase signed uploads](https://supabase.com/docs/reference/python/storage-from-createsigneduploadurl),
[Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys),
[Vercel Function limits](https://vercel.com/docs/functions/limitations)
