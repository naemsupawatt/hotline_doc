"""ยิงอีเมลทดสอบหนึ่งฉบับด้วยค่าใน .env ปัจจุบัน

มีไว้เพราะการตั้งค่า SMTP พลาดง่าย (พอร์ตผิด ใช้รหัสผ่านบัญชีแทน app password
ไฟร์วอลล์บล็อก) แต่การส่งจริงเกิดใน background task หลังเจ้าหน้าที่กดตัดสิน
ซึ่ง "กลืน exception ทุกชนิด" โดยตั้งใจ (ดู services/notification.py)
ถ้าไม่มีสคริปต์นี้ ค่าที่ตั้งผิดจะเงียบ เห็นแค่ AuditLog outcome=failed
สคริปต์นี้เรียก send() ตรง ๆ จึงได้ error ดิบ ๆ มาอ่านว่าพลาดตรงไหน

    uv run python -m scripts.send_test_email someone@example.com
"""

import smtplib
import ssl
import sys

from app.core.config import settings
from app.services import notification as notify_svc

# ข้อผิดพลาดที่เจอบ่อยตอนต่อ SMTP ครั้งแรก -> สิ่งที่ต้องไปแก้
HINTS: list[tuple[type[Exception], str]] = [
    (
        smtplib.SMTPAuthenticationError,
        "เซิร์ฟเวอร์ปฏิเสธการยืนยันตัวตน — Gmail/Workspace ต้องใช้ app password\n"
        "  (16 หลักจาก myaccount.google.com/apppasswords) ไม่ใช่รหัสผ่านที่ใช้ล็อกอินปกติ\n"
        "  และบัญชีต้องเปิด 2-Step Verification ไว้ก่อนถึงจะสร้าง app password ได้",
    ),
    (
        ssl.SSLError,
        "จับมือ TLS ไม่สำเร็จ — พอร์ต 465 ต้องใช้ SSL ตั้งแต่ต้น ให้ตั้ง SMTP_PORT=587\n"
        "  คู่กับ SMTP_STARTTLS=true แทน (ช่องทางนี้รองรับ STARTTLS)",
    ),
    (
        OSError,
        "ต่อเซิร์ฟเวอร์ไม่ได้เลย — ตรวจ SMTP_HOST/SMTP_PORT และเน็ตของเครื่อง\n"
        "  เครือข่ายบางแห่งบล็อกพอร์ต 587/465 ขาออก ถ้าเป็นแบบนั้นต้องใช้เน็ตอื่น",
    ),
]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    to = sys.argv[1]
    mail = notify_svc.Mail(
        to=to,
        subject="ทดสอบระบบแจ้งเตือน HoTLinE Doc",
        body=(
            "ฉบับนี้ส่งจากสคริปต์ทดสอบ ไม่ได้เกิดจากคำขอจริง\n"
            "ถ้าคุณได้รับ แปลว่าอีเมลแจ้งผลการพิจารณาถึงผู้ยื่นได้แล้ว\n\n"
            "— ระบบ HoTLinE Doc (ต้นแบบเพื่อการสาธิต ข้อมูลทั้งหมดเป็นข้อมูลจำลอง)"
        ),
    )

    print(f"ช่องทาง : {settings.EMAIL_BACKEND}")
    print(f"ผู้ส่ง   : {settings.EMAIL_FROM}")
    if settings.EMAIL_BACKEND == "smtp":
        tls = "starttls" if settings.SMTP_STARTTLS else "ไม่เข้ารหัส"
        print(f"เซิร์ฟเวอร์: {settings.SMTP_HOST}:{settings.SMTP_PORT} ({tls})")
        print(f"บัญชี   : {settings.SMTP_USER or '(ไม่ได้ล็อกอิน)'}")
    print(f"ผู้รับ   : {to}")
    if notify_svc.redirect_target():
        print(f"เปลี่ยนปลายทางเป็น: {notify_svc.redirect_target()} (EMAIL_REDIRECT_TO)")
    print()

    try:
        channel = notify_svc.send(mail)
    except Exception as exc:  # noqa: BLE001 - สคริปต์นี้มีไว้เพื่ออ่าน error ทุกชนิด
        print(f"ส่งไม่สำเร็จ: {type(exc).__name__}: {exc}\n")
        for kind, hint in HINTS:
            if isinstance(exc, kind):
                print(hint)
                break
        return 1

    if channel == "outbox":
        newest = max(notify_svc.outbox_dir().iterdir(), key=lambda p: p.stat().st_mtime)
        print(f"เขียนลงกล่องขาออกแล้ว (ยังไม่ได้ส่งออกจริง): {newest}")
        print("ถ้าต้องการส่งจริง ให้ตั้ง EMAIL_BACKEND=smtp ใน backend/.env")
    else:
        print("ส่งออกจาก SMTP สำเร็จ — ไปเปิดกล่องจดหมายของผู้รับเพื่อยืนยันอีกชั้น")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
