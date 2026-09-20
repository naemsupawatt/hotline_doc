"""แจ้งเตือนผู้ยื่นทางอีเมลเมื่อเจ้าหน้าที่ตัดสินคำขอ

ปัญหาที่แก้: เดิมผู้ยื่นรู้ผลก็ต่อเมื่อเปิดเว็บมาดูเอง คนที่ถูกตีกลับจึงอาจ
ค้างอยู่หลายวันโดยไม่รู้ตัว แล้วจบลงที่การโทรถามเจ้าหน้าที่ ซึ่งเป็นภาระ
ที่โจทย์อยากลด อีเมลส่งไปยังที่อยู่ที่ใช้สมัครสมาชิก (M1)

**ส่งเมื่อเจ้าหน้าที่ลงมือเท่านั้น** — ขอให้แก้ไข / อนุมัติ / ไม่อนุมัติ /
ออกเอกสาร ไม่ส่งตอนผู้ยื่นทำอะไรเอง เพราะเขารู้อยู่แล้วว่าตัวเองเพิ่งทำอะไร

**การส่งอีเมลต้องไม่ทำให้การตัดสินของเจ้าหน้าที่ล้มเหลว** ถ้าเซิร์ฟเวอร์เมล
ล่มหรือช้า คำขอต้องเปลี่ยนสถานะสำเร็จอยู่ดี ฟังก์ชันในไฟล์นี้จึงถูกเรียก
แบบ background task หลัง commit และกลืนข้อผิดพลาดทุกชนิด โดยบันทึกผลลง
AuditLog ไว้แทน ทั้งกรณีส่งสำเร็จและล้มเหลว (NFR Audit Trail)

**สองช่องทางส่ง เลือกด้วย EMAIL_BACKEND**
  outbox (ค่าเริ่มต้น) — เขียนไฟล์ลง STORAGE_DIR/outbox ไม่ต้องมีเซิร์ฟเวอร์เมล
                         ใช้ตอนพัฒนาและตอนสาธิต เปิดไฟล์ดูได้ว่าจะส่งอะไรออกไป
  smtp                 — ส่งจริงผ่าน SMTP ตามค่าใน .env
ไม่ตั้ง EMAIL_BACKEND=smtp แล้วยังไม่ได้ใส่ค่า SMTP ระบบจะไม่พยายามส่งเงียบ ๆ
แต่จะบันทึก AuditLog ว่าส่งไม่ได้เพราะยังไม่ได้ตั้งค่า
"""

import logging
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage as MimeMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.application import Application
from app.models.audit import AuditLog
from app.models.classification import ApplicationClassification
from app.models.enums import ApplicationStatus
from app.models.property import Operator, Property
from app.models.user import User
from app.services import document as doc_svc

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Mail:
    to: str
    subject: str
    body: str


@dataclass(frozen=True)
class Template:
    subject: str
    headline: str
    what_next: str


# ข้อความอีเมลอยู่ที่นี่ที่เดียว แนวคิดเดียวกับ StatusPill ฝั่งหน้าเว็บที่รวม
# "สถานะ -> ข้อความ" ไว้จุดเดียว ถ้ากระจายไปตาม endpoint ข้อความจะเริ่มไม่ตรงกัน
#
# ตั้งใจไม่เล่าโครงสร้าง 4 ขั้นซ้ำในอีเมล เพราะคำอธิบายขั้นตอนอยู่ที่หน้าเว็บ
# (frontend/src/lib/progress.ts) การเขียนซ้ำสองที่แปลว่าวันหนึ่งจะไม่ตรงกัน
TEMPLATES: dict[str, Template] = {
    ApplicationStatus.NEEDS_REVISION: Template(
        subject="เจ้าหน้าที่ขอให้แก้ไขเอกสาร คำขอ {application_no}",
        headline="เจ้าหน้าที่ตรวจคำขอของคุณแล้ว และขอให้แก้ไขเอกสารบางส่วนก่อนพิจารณาต่อ",
        what_next=(
            "เปิดหน้าคำขอ แนบไฟล์ใหม่ที่เอกสารฉบับที่ต้องแก้ "
            "(ระบบเก็บเป็นรุ่นใหม่โดยไม่ลบไฟล์เดิม) แล้วกดยื่นอีกครั้ง "
            "เรื่องจะกลับเข้าคิวเจ้าหน้าที่ทันที"
        ),
    ),
    ApplicationStatus.APPROVED: Template(
        subject="อนุมัติคำขอ {application_no} แล้ว",
        headline="เจ้าหน้าที่พิจารณาอนุมัติคำขอของคุณแล้ว",
        what_next="ขั้นต่อไปเจ้าหน้าที่จะลงนามออกเอกสาร ระบบจะส่งอีเมลแจ้งอีกครั้งเมื่อเอกสารพร้อมให้พิมพ์",
    ),
    ApplicationStatus.REJECTED: Template(
        subject="ผลการพิจารณาคำขอ {application_no}",
        headline="เจ้าหน้าที่พิจารณาแล้วไม่อนุมัติคำขอนี้",
        what_next=(
            "หากต้องการยื่นใหม่ กรุณาแก้ไขตามเหตุผลข้างต้นแล้วเริ่มคำขอใหม่ "
            "หรือสอบถามรายละเอียดเพิ่มเติมกับเจ้าหน้าที่ของท้องถิ่นที่รับเรื่อง"
        ),
    ),
    ApplicationStatus.LICENSE_ISSUED: Template(
        subject="เอกสารของคำขอ {application_no} พร้อมให้พิมพ์แล้ว",
        headline="เจ้าหน้าที่ลงนามและออกเอกสารให้คำขอของคุณเรียบร้อยแล้ว",
        what_next="เปิดหน้าเอกสารในระบบเพื่อสั่งพิมพ์ หรือเลือกบันทึกเป็น PDF เก็บไว้",
    ),
}


def outbox_dir() -> Path:
    """กล่องจดหมายขาออกตอนยังไม่ได้ต่อเซิร์ฟเวอร์เมลจริง"""
    return doc_svc.storage_root() / "outbox"


# ---------------------------------------------------------------- ประกอบข้อความ


def _application_url(application_no: str, status: str) -> str:
    base = settings.APP_BASE_URL.rstrip("/")
    path = f"/operator/applications/{application_no}"
    if status == ApplicationStatus.LICENSE_ISSUED:
        path += "/license"
    return f"{base}{path}"


def build_mail(
    *,
    recipient_email: str,
    recipient_name: str,
    application: Application,
    property_name: str,
    property_type_name: str,
) -> Mail | None:
    """คืน None เมื่อสถานะนี้ไม่ได้ตั้งใจให้แจ้งเตือน"""
    template = TEMPLATES.get(application.status)
    if template is None:
        return None

    lines = [
        f"เรียน {recipient_name}",
        "",
        template.headline,
        "",
        f"เลขที่คำขอ: {application.application_no}",
        f"ชื่อที่พัก: {property_name}",
        f"ประเภทที่จำแนกได้: {property_type_name}",
    ]

    if application.decision_reason:
        lines += ["", f"เหตุผลจากเจ้าหน้าที่: {application.decision_reason}"]

    lines += [
        "",
        f"สิ่งที่ต้องทำต่อ: {template.what_next}",
        "",
        f"เปิดดูในระบบ: {_application_url(application.application_no, application.status)}",
        "",
        "— ระบบ HoTLinE Doc (อีเมลฉบับนี้ส่งอัตโนมัติ กรุณาอย่าตอบกลับ)",
        "ต้นแบบเพื่อการสาธิต ข้อมูลทั้งหมดเป็นข้อมูลจำลอง",
    ]

    return Mail(
        to=recipient_email,
        subject=template.subject.format(application_no=application.application_no),
        body="\n".join(lines),
    )


# ---------------------------------------------------------------- ช่องทางส่ง


def redirect_target() -> str:
    """ที่อยู่ปลายทางของโหมดทดสอบ ว่าง = ปิดโหมดนี้"""
    return settings.EMAIL_REDIRECT_TO.strip()


def _redirected(mail: Mail) -> Mail:
    """โหมดทดสอบ: เปลี่ยนปลายทางทุกฉบับไปที่อยู่เดียว

    มีไว้เพราะบัญชีผู้ยื่นที่ใช้ทดสอบเป็นข้อมูลจำลอง อีเมลเป็น @example.com
    ซึ่งไม่มีใครเปิดอ่านได้ ถ้าอยากเห็นของจริงในกล่องจดหมายต้องเปลี่ยนปลายทาง

    ที่อยู่อยู่ใน .env ไม่ได้ฝังในโค้ด เพราะโค้ดขึ้น git (กติกาข้อ 7) และการฝังไว้
    แปลว่าวันสาธิตเมลจะยังเด้งไปหาคนเดิมโดยไม่มีใครทันสังเกต

    ผู้รับที่ตั้งใจไว้เดิมถูกเขียนไว้ในเนื้อจดหมายเสมอ ไม่งั้นทดสอบไปก็ไม่รู้ว่า
    ฉบับไหนของใคร
    """
    target = redirect_target()
    if not target or target == mail.to:
        return mail

    banner = f"[โหมดทดสอบ] จดหมายฉบับนี้ควรถึง {mail.to} แต่ถูกส่งมาที่นี่เพราะตั้ง EMAIL_REDIRECT_TO ไว้ใน .env"
    return Mail(to=target, subject=f"[ทดสอบ] {mail.subject}", body=f"{banner}\n\n{mail.body}")


def send(mail: Mail) -> str:
    """ส่งจริง คืนชื่อช่องทางที่ใช้ และโยน exception เมื่อส่งไม่สำเร็จ"""
    mail = _redirected(mail)

    if settings.EMAIL_BACKEND == "smtp":
        _send_smtp(mail)
        return "smtp"

    _write_outbox(mail)
    return "outbox"


def _write_outbox(mail: Mail) -> None:
    folder = outbox_dir()
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    # ชื่อไฟล์ไม่เอาอีเมลผู้รับมาใส่ เพราะเป็นข้อมูลส่วนบุคคลที่ไม่ควรไปโผล่ในชื่อไฟล์
    path = folder / f"{stamp}.txt"
    path.write_text(
        f"To: {mail.to}\nFrom: {settings.EMAIL_FROM}\nSubject: {mail.subject}\n\n{mail.body}\n",
        encoding="utf-8",
    )


def _send_smtp(mail: Mail) -> None:
    if not settings.SMTP_HOST:
        raise RuntimeError("ยังไม่ได้ตั้งค่า SMTP_HOST ใน .env")

    message = MimeMessage()
    message["From"] = settings.EMAIL_FROM
    message["To"] = mail.to
    message["Subject"] = mail.subject
    # ใส่เองไม่รอให้เซิร์ฟเวอร์เติมให้ เพราะจดหมายที่ไม่มี Date/Message-ID
    # โดนตัวกรองสแปมหักคะแนน และผู้ยื่นที่ไม่เห็นอีเมลคือคนที่ค้างอยู่เฉย ๆ
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid(domain="hotline-doc.local")
    # RFC 3834: บอกว่าเป็นจดหมายที่เครื่องส่ง ปลายทางจะได้ไม่ตอบกลับอัตโนมัติ
    # วนกลับมา และตัวกรองรู้ว่าไม่ใช่คนพิมพ์เอง
    message["Auto-Submitted"] = "auto-generated"
    message.set_content(mail.body)

    # timeout สั้น ๆ เสมอ เพราะงานนี้รันหลังตอบ response แล้ว ไม่ควรค้างยาว
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT) as s:
        if settings.SMTP_STARTTLS:
            s.starttls()
        if settings.SMTP_USER:
            s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        s.send_message(message)


# ---------------------------------------------------------------- จุดเรียกใช้


def notify_status_change(application_id: int, actor_id: int | None = None) -> None:
    """แจ้งผู้ยื่นว่าคำขอเปลี่ยนสถานะแล้ว — ใช้เป็น background task หลัง commit

    เปิด session ของตัวเองเพราะรันหลังจาก request ปิด session ไปแล้ว
    และห้ามโยน exception ออกไปไม่ว่ากรณีใด เพราะงานนี้ไม่ควรทำให้อะไรพังตามได้
    """
    try:
        with SessionLocal() as db:
            application = db.get(Application, application_id)
            if application is None:  # pragma: no cover - ถูกลบระหว่างทาง
                return

            recipient = db.scalar(
                select(User)
                .join(Operator, Operator.user_id == User.id)
                .where(Operator.id == application.operator_id)
            )
            prop = db.get(Property, application.property_id)
            snapshot = db.scalar(
                select(ApplicationClassification).where(
                    ApplicationClassification.application_id == application.id
                )
            )

            # M1 ให้สมัครด้วยอีเมลหรือเบอร์โทรก็ได้ คนที่สมัครด้วยเบอร์จึงไม่มีอีเมล
            if recipient is None or not recipient.email:
                _audit(
                    db,
                    actor_id=actor_id,
                    application=application,
                    outcome="skipped",
                    detail="ไม่ได้ส่งอีเมลแจ้งเตือน เพราะบัญชีผู้ยื่นไม่มีอีเมล",
                )
                db.commit()
                return

            mail = build_mail(
                recipient_email=recipient.email,
                recipient_name=recipient.full_name,
                application=application,
                property_name=prop.name if prop else "-",
                property_type_name=snapshot.property_type.name_th if snapshot else "-",
            )
            if mail is None:
                return

            try:
                channel = send(mail)
            except Exception as exc:  # noqa: BLE001 - ต้องกลืนทุกชนิดจริง ๆ
                log.warning("ส่งอีเมลแจ้งเตือนไม่สำเร็จ: %s", exc)
                _audit(
                    db,
                    actor_id=actor_id,
                    application=application,
                    outcome="failed",
                    detail=f"ส่งอีเมลแจ้งเตือนไม่สำเร็จ: {exc}",
                )
            else:
                _audit(
                    db,
                    actor_id=actor_id,
                    application=application,
                    outcome="success",
                    # ไม่เขียนอีเมลเต็มลง log ตามกฎข้อมูลส่วนบุคคลของโปรเจกต์
                    detail=(
                        f"ส่งอีเมลแจ้งเตือนสถานะ {application.status} ทาง {channel}"
                        + (" (โหมดทดสอบ เปลี่ยนปลายทางไม่ได้ส่งถึงผู้ยื่น)" if redirect_target() else "")
                    ),
                )
            db.commit()
    except Exception as exc:  # noqa: BLE001 - background task ห้ามพังเงียบ ๆ แบบไม่มีร่องรอย
        log.exception("แจ้งเตือนไม่สำเร็จโดยไม่คาดคิด: %s", exc)


def _audit(
    db, *, actor_id: int | None, application: Application, outcome: str, detail: str
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            action="notification.email",
            entity_type="application",
            entity_id=application.id,
            to_status=application.status,
            outcome=outcome,
            detail=detail,
        )
    )
