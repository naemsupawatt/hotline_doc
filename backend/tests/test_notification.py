"""อีเมลแจ้งเตือนผู้ยื่นเมื่อเจ้าหน้าที่ตัดสินคำขอ

ใช้ backend "outbox" ที่เขียนไฟล์ลงดิสก์ เทสต์จึงอ่านข้อความจริงที่ระบบจะส่ง
ได้โดยไม่ต้องมีเซิร์ฟเวอร์เมล (ดูเหตุผลใน services/notification.py)

TestClient รัน background task ให้เสร็จก่อนคืน response จึงตรวจกล่องขาออก
ได้ทันทีหลังเรียก API

ใช้ตัวช่วยสมัครผู้ใช้/เปิดคำขอร่วมกับ test_officer_api เพราะเป็นชุดเดียวกัน
และใช้ EMAIL_PREFIX เดียวกัน การล้างข้อมูลจึงครอบคลุมทั้งสองไฟล์
"""

import shutil

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal
from app.main import app
from app.models.audit import AuditLog
from app.models.user import User
from app.services import notification as notify_svc
from tests.test_officer_api import (
    _cleanup,
    _make_officer,
    _register,
    approve_fully,
    auth,
    fill_and_submit,
    issue,
    open_application,
)


@pytest.fixture(scope="module", autouse=True)
def _clean_module():
    _cleanup()
    yield
    _cleanup()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_outbox():
    """กล่องขาออกต้องว่างก่อนทุกเคส ไม่งั้นเคสหนึ่งจะเห็นเมลของอีกเคส"""
    shutil.rmtree(notify_svc.outbox_dir(), ignore_errors=True)
    yield
    shutil.rmtree(notify_svc.outbox_dir(), ignore_errors=True)


@pytest.fixture
def applicant(client) -> tuple[str, str]:
    """คืน (token, อีเมลที่ใช้สมัคร) — อีเมลนี้คือปลายทางที่ระบบต้องส่งไป (M1)"""
    return _register(client, "owner")


@pytest.fixture
def officer_a(client) -> str:
    return _make_officer(client, "PKT-CITY")


def sent_mails() -> list[str]:
    folder = notify_svc.outbox_dir()
    if not folder.exists():
        return []
    return [f.read_text(encoding="utf-8") for f in sorted(folder.iterdir())]


def last_notification_audit() -> AuditLog:
    with SessionLocal() as db:
        rows = db.scalars(
            select(AuditLog).where(AuditLog.action == "notification.email").order_by(AuditLog.id)
        ).all()
        assert rows, "ต้องมีรายการ audit ของการส่งอีเมล"
        return rows[-1]


def submitted_application(client, applicant, code: str = "PKT-CITY") -> str:
    token, _ = applicant
    no = open_application(client, token, code)
    fill_and_submit(client, token, no)
    return no


def request_revision(client, officer, no: str, reason: str):
    return client.post(
        f"/api/v1/officer/applications/{no}/decide",
        headers=auth(officer),
        json={"decision": "request_revision", "reason": reason},
    )


def test_revision_request_emails_the_applicant_with_the_reason(client, applicant, officer_a):
    """เคสสำคัญที่สุด — ถูกตีกลับแล้วต้องรู้ทางอีเมลว่าต้องแก้อะไร"""
    _, email = applicant
    no = submitted_application(client, applicant)

    request_revision(client, officer_a, no, "สำเนาทะเบียนบ้านเบลอ อ่านเลขที่บ้านไม่ออก")

    mails = sent_mails()
    assert len(mails) == 1, "ต้องส่งอีเมลหนึ่งฉบับต่อหนึ่งการตัดสิน"
    body = mails[0]
    assert f"To: {email}" in body, "ต้องส่งไปยังอีเมลที่ใช้สมัครสมาชิก (M1)"
    assert no in body
    assert "สำเนาทะเบียนบ้านเบลอ อ่านเลขที่บ้านไม่ออก" in body
    assert "/operator/applications/" in body, "ต้องมีลิงก์กลับเข้าระบบให้กดแก้ต่อได้ทันที"


def test_approval_and_issuing_each_send_their_own_email(client, applicant, officer_a):
    token, _ = applicant
    no = submitted_application(client, applicant)

    approve_fully(client, token, officer_a, no)
    assert len(sent_mails()) == 1
    assert "อนุมัติ" in sent_mails()[0]

    issue(client, officer_a, no)
    mails = sent_mails()
    assert len(mails) == 2, "ออกเอกสารเป็นคนละเหตุการณ์กับอนุมัติ จึงต้องแจ้งอีกฉบับ"
    assert "พร้อมให้พิมพ์" in mails[1]
    assert "/license" in mails[1], "ฉบับนี้ต้องพาไปหน้าพิมพ์เอกสารโดยตรง"


def test_rejection_tells_the_applicant_why(client, applicant, officer_a):
    no = submitted_application(client, applicant)

    client.post(
        f"/api/v1/officer/applications/{no}/decide",
        headers=auth(officer_a),
        json={"decision": "reject", "reason": "อาคารไม่ผ่านเกณฑ์ความปลอดภัย"},
    )

    assert "อาคารไม่ผ่านเกณฑ์ความปลอดภัย" in sent_mails()[0]


def test_every_email_is_written_to_the_audit_trail(client, applicant, officer_a):
    """M9: ต้องย้อนดูได้ว่าระบบแจ้งผู้ยื่นไปแล้วจริงเมื่อไร"""
    _, email = applicant
    no = submitted_application(client, applicant)

    request_revision(client, officer_a, no, "ขอเอกสารเพิ่ม")

    row = last_notification_audit()
    assert row.outcome == "success"
    assert row.to_status == "needs_revision"
    # กฎข้อมูลส่วนบุคคลของโปรเจกต์: ห้ามเขียนที่อยู่อีเมลเต็มลง log
    assert email not in (row.detail or "")


def test_account_without_email_does_not_break_the_decision(client, applicant, officer_a):
    """M1 สมัครด้วยเบอร์โทรอย่างเดียวได้ คนกลุ่มนี้ต้องไม่ทำให้การตัดสินพัง"""
    _, email = applicant
    no = submitted_application(client, applicant)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        user_id = user.id
        user.email = None
        db.commit()

    try:
        res = request_revision(client, officer_a, no, "ขอเอกสารเพิ่ม")

        assert res.status_code == 200, "ไม่มีอีเมลก็ต้องตัดสินได้ตามปกติ"
        assert sent_mails() == []
        assert last_notification_audit().outcome == "skipped"
    finally:
        # ต้องคืนอีเมลเสมอ ไม่งั้นตัวล้างข้อมูลท้ายไฟล์หาผู้ใช้รายนี้ไม่เจอ
        # (หาโดยอีเมลขึ้นต้นด้วย EMAIL_PREFIX) แล้วข้อมูลจะค้างจนเทสต์รอบหน้าล้ม
        with SessionLocal() as db:
            db.get(User, user_id).email = email
            db.commit()


def test_sending_failure_never_breaks_the_decision(client, applicant, officer_a, monkeypatch):
    """เซิร์ฟเวอร์เมลล่มต้องไม่ทำให้ผลการพิจารณาที่บันทึกแล้วหายไป"""
    no = submitted_application(client, applicant)

    def boom(_mail):
        raise RuntimeError("เชื่อมต่อเซิร์ฟเวอร์เมลไม่ได้")

    monkeypatch.setattr(notify_svc, "send", boom)

    res = request_revision(client, officer_a, no, "ขอเอกสารเพิ่ม")

    assert res.status_code == 200
    assert res.json()["status"] == "needs_revision", "สถานะต้องเปลี่ยนสำเร็จแม้ส่งเมลไม่ได้"
    assert last_notification_audit().outcome == "failed", "ส่งไม่สำเร็จก็ต้องมีร่องรอยไว้ตามหาได้"


def test_no_email_for_steps_the_applicant_did_themselves(client, applicant, officer_a):
    """ผู้ยื่นเพิ่งกดยื่นเอง ไม่ต้องส่งอีเมลบอกสิ่งที่เขารู้อยู่แล้ว"""
    submitted_application(client, applicant)

    assert sent_mails() == []


# ---------------------------------------------------------------- ช่องทาง smtp
#
# เคสข้างล่างไม่พึ่งฐานข้อมูลและไม่ต่อเน็ต แค่ตรวจว่า "ถ้าจะส่งจริง เราคุยกับ
# เซิร์ฟเวอร์เมลถูกขั้นตอนและจดหมายที่ยื่นให้มันหน้าตาถูกต้อง" เพราะของจริง
# ถูกเรียกใน background task ที่กลืน exception ทุกชนิด ถ้าพลาดจะเงียบสนิท


class FakeSMTP:
    """เซิร์ฟเวอร์เมลปลอมไว้บันทึกว่าถูกเรียกอะไรบ้าง"""

    last: "FakeSMTP | None" = None

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in_as = None
        self.message = None
        FakeSMTP.last = self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, user, _password):
        self.logged_in_as = user

    def send_message(self, message):
        self.message = message


@pytest.fixture
def smtp(monkeypatch) -> type[FakeSMTP]:
    """สลับไปช่องทาง smtp พร้อมเซิร์ฟเวอร์ปลอม (conftest บังคับ outbox ไว้)"""
    monkeypatch.setattr(notify_svc.settings, "EMAIL_BACKEND", "smtp")
    monkeypatch.setattr(notify_svc.settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(notify_svc.settings, "SMTP_PORT", 587)
    monkeypatch.setattr(notify_svc.settings, "SMTP_USER", "robot@example.com")
    monkeypatch.setattr(notify_svc.settings, "SMTP_STARTTLS", True)
    monkeypatch.setattr(notify_svc.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def test_smtp_channel_encrypts_and_signs_in_before_sending(smtp):
    notify_svc.send(notify_svc.Mail(to="owner@example.com", subject="หัวข้อ", body="เนื้อความ"))

    sent = smtp.last
    assert (sent.host, sent.port) == ("smtp.example.com", 587)
    assert sent.timeout == notify_svc.settings.SMTP_TIMEOUT, "ต้องมี timeout เสมอ ไม่งั้นค้างยาว"
    assert sent.started_tls, "ต้องเข้ารหัสก่อนส่งรหัสผ่านออกไป"
    assert sent.logged_in_as == "robot@example.com"


def test_thai_subject_and_body_survive_the_wire(smtp):
    """หัวข้อภาษาไทยต้องไม่กลายเป็นตัวประหลาดในกล่องจดหมายของผู้ยื่น"""
    from email import message_from_string, policy

    notify_svc.send(
        notify_svc.Mail(
            to="owner@example.com",
            subject="เจ้าหน้าที่ขอให้แก้ไขเอกสาร คำขอ PKT-2569-000001",
            body="เรียน คุณทดสอบ\nสำเนาทะเบียนบ้านเบลอ",
        )
    )

    # ผ่านการเข้ารหัสหัวจดหมายจริงแล้วอ่านกลับ เหมือนที่โปรแกรมเมลปลายทางทำ
    delivered = message_from_string(smtp.last.message.as_string(), policy=policy.default)

    assert delivered["Subject"] == "เจ้าหน้าที่ขอให้แก้ไขเอกสาร คำขอ PKT-2569-000001"
    assert "สำเนาทะเบียนบ้านเบลอ" in delivered.get_content()
    assert delivered["To"] == "owner@example.com"
    assert delivered["From"] == notify_svc.settings.EMAIL_FROM


def test_automated_mail_carries_the_headers_filters_expect(smtp):
    notify_svc.send(notify_svc.Mail(to="owner@example.com", subject="หัวข้อ", body="เนื้อความ"))

    message = smtp.last.message
    assert message["Date"], "ไม่มี Date ตัวกรองสแปมหักคะแนน"
    assert message["Message-ID"], "ไม่มี Message-ID ตัวกรองสแปมหักคะแนน"
    assert message["Auto-Submitted"] == "auto-generated", "บอกปลายทางว่าอย่าตอบกลับอัตโนมัติ"


def test_missing_smtp_host_says_what_to_fix(smtp, monkeypatch):
    """ลืมตั้งค่าแล้วต้องรู้ว่าลืมอะไร ไม่ใช่ error ดิบ ๆ (NFR Usability)"""
    monkeypatch.setattr(notify_svc.settings, "SMTP_HOST", "")

    with pytest.raises(RuntimeError, match="SMTP_HOST"):
        notify_svc.send(notify_svc.Mail(to="owner@example.com", subject="x", body="y"))


# ------------------------------------------------- โหมดทดสอบ เปลี่ยนปลายทางทุกฉบับ


@pytest.fixture
def redirect_to(monkeypatch):
    """เปิดโหมดทดสอบ (conftest ปิดไว้เป็นค่าตั้งต้นให้ทุกเคส)"""

    def enable(address: str) -> str:
        monkeypatch.setattr(notify_svc.settings, "EMAIL_REDIRECT_TO", address)
        return address

    return enable


def test_redirect_sends_every_mail_to_the_tester_inbox(client, applicant, officer_a, redirect_to):
    """บัญชีทดสอบใช้อีเมลจำลองที่เปิดอ่านไม่ได้ ต้องดึงมาเข้ากล่องจริงกล่องเดียว"""
    _, applicant_email = applicant
    tester = redirect_to("  tester@example.org  ")  # เผื่อคนกรอกเว้นวรรคติดมาใน .env
    no = submitted_application(client, applicant)

    request_revision(client, officer_a, no, "ขอเอกสารเพิ่ม")

    body = sent_mails()[0]
    assert f"To: {tester.strip()}" in body
    assert f"To: {applicant_email}" not in body, "ต้องไม่ส่งถึงผู้ยื่นตัวจริงตอนเปิดโหมดนี้"
    assert applicant_email in body, "ต้องบอกในจดหมายว่าฉบับนี้ของใคร ไม่งั้นทดสอบแล้วแยกไม่ออก"
    assert "[ทดสอบ]" in body, "หัวข้อต้องบอกให้รู้ว่าเป็นของทดสอบ ไม่ใช่จดหมายจริง"
    assert no in body, "เนื้อความเดิมต้องอยู่ครบ"


def test_redirect_is_recorded_so_the_log_does_not_lie(client, applicant, officer_a, redirect_to):
    """M9: log ต้องไม่อ้างว่าแจ้งผู้ยื่นแล้ว ทั้งที่จดหมายไปเข้ากล่องคนทดสอบ"""
    redirect_to("tester@example.org")
    no = submitted_application(client, applicant)

    request_revision(client, officer_a, no, "ขอเอกสารเพิ่ม")

    row = last_notification_audit()
    assert row.outcome == "success"
    assert "โหมดทดสอบ" in row.detail


def test_no_redirect_means_the_applicant_gets_it(client, applicant, officer_a):
    """ลบค่าออกจาก .env แล้วต้องกลับไปส่งถึงผู้ยื่นตามปกติทันที"""
    _, applicant_email = applicant
    no = submitted_application(client, applicant)

    request_revision(client, officer_a, no, "ขอเอกสารเพิ่ม")

    body = sent_mails()[0]
    assert f"To: {applicant_email}" in body
    assert "[ทดสอบ]" not in body
