"""แบบฟอร์มที่ระบบกรอกให้ (A01 หนังสือแจ้งฯ / A06 ร.ร.1) — หน้าพิมพ์ + ลายมือชื่อ

ผู้ใช้ของไฟล์นี้แยกจากไฟล์เทสต์อื่น เพราะเคสที่ใช้อีเมลชุดเดียวกันแล้วลบ
ระหว่างเคสเคยทำให้ชุดเทสต์ล้มแบบสุ่มมาแล้ว
"""

import shutil

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.db import SessionLocal
from app.main import app
from app.models.application import Application, ApplicationStatusHistory
from app.models.audit import AuditLog
from app.models.classification import ApplicationClassification
from app.models.document import DocumentFile
from app.models.property import Operator, Property
from app.models.user import User
from app.services import document as doc_svc
from tests.test_document_upload import PDF, PNG
from tests.test_thai_id import make_valid

EMAIL = "pytest-notice-form@example.com"
PHONE = "0899960041"
NATIONAL_ID = make_valid("392220004411")


def _cleanup() -> None:
    with SessionLocal() as db:
        user_ids = list(db.scalars(select(User.id).where(User.email == EMAIL)).all())
        if not user_ids:
            return
        operator_ids = list(
            db.scalars(select(Operator.id).where(Operator.user_id.in_(user_ids))).all()
        )
        app_rows = (
            list(
                db.scalars(
                    select(Application).where(Application.operator_id.in_(operator_ids))
                ).all()
            )
            if operator_ids
            else []
        )
        app_ids = [a.id for a in app_rows]

        for row in app_rows:
            shutil.rmtree(doc_svc.storage_root() / row.application_no, ignore_errors=True)

        if app_ids:
            db.execute(delete(DocumentFile).where(DocumentFile.application_id.in_(app_ids)))
            db.execute(
                delete(ApplicationClassification).where(
                    ApplicationClassification.application_id.in_(app_ids)
                )
            )
            db.execute(
                delete(ApplicationStatusHistory).where(
                    ApplicationStatusHistory.application_id.in_(app_ids)
                )
            )
            db.execute(delete(Application).where(Application.id.in_(app_ids)))
        if operator_ids:
            db.execute(delete(Property).where(Property.operator_id.in_(operator_ids)))
            db.execute(delete(Operator).where(Operator.id.in_(operator_ids)))
        db.execute(delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))
        db.execute(delete(User).where(User.id.in_(user_ids)))
        db.commit()


@pytest.fixture
def client():
    _cleanup()
    with TestClient(app) as c:
        yield c
    _cleanup()


@pytest.fixture
def token(client) -> str:
    res = client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "สมหญิง",
            "last_name": "ใจดี",
            "national_id": NATIONAL_ID,
            "phone": PHONE,
            "email": EMAIL,
            "password": "demo1234",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def start(client, token, *, rooms: int, guests: int) -> str:
    karon = next(
        a["id"]
        for a in client.get("/api/v1/wizard/local-authorities").json()
        if a["code"] == "KRN-SUB"
    )
    res = client.post(
        "/api/v1/applications",
        headers=auth(token),
        json={
            "rooms": rooms,
            "guests": guests,
            "has_restaurant": False,
            "local_authority_id": karon,
            "property_name": "บ้านพักทดสอบแบบแจ้ง",
            "address": {
                "address_no": "99/9",
                "moo": "1",
                "sub_district": "กะรน",
                "district": "เมืองภูเก็ต",
                "postal_code": "83100",
            },
            "accommodation_kind": "detached_house",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["application_no"]


@pytest.fixture
def application_no(client, token) -> str:
    """6 ห้อง 24 คน = ไม่เข้าข่ายโรงแรม จึงใช้แบบหนังสือแจ้งฯ"""
    return start(client, token, rooms=6, guests=24)


def form_of(client, token, no, code="A01"):
    return client.get(f"/api/v1/applications/{no}/forms/{code}", headers=auth(token))


def sign(client, token, no, *, data=PNG, name="signature.png", mime="image/png"):
    return client.post(
        f"/api/v1/applications/{no}/documents/A01",
        headers=auth(token),
        files={"file": (name, data, mime)},
    )


def test_form_is_prefilled_from_the_application(client, token, application_no):
    """ระบบกรอกให้ครบ ผู้แจ้งไม่ต้องพิมพ์ซ้ำ — เหลือแค่ลงลายมือชื่อ"""
    body = form_of(client, token, application_no).json()

    assert body["form_code"] == "A01"
    # ชื่อแบบฟอร์มต้องมาจากตารางเอกสาร ไม่ใช่ค่าคงที่ในโค้ด (US-09)
    assert body["title"] == "แบบหนังสือแจ้งสถานที่พักที่ไม่เป็นโรงแรม"
    assert body["applicant"]["display_name"] == "สมหญิง ใจดี"
    assert body["property"]["name"] == "บ้านพักทดสอบแบบแจ้ง"
    assert body["property"]["room_count"] == 6
    assert body["property"]["address"]["moo"] == "1"
    assert body["local_authority_name"]
    assert body["filed_on"] is None, "ยังไม่ได้ยื่น วันที่แจ้งต้องยังว่าง"
    assert body["signature"] is None
    assert body["can_sign"] is True


def test_form_never_exposes_the_raw_national_id(client, token, application_no):
    """กฎของโปรเจกต์: เลขบัตรเต็มห้ามออกทาง API ไม่ว่าจากเส้นทางไหน"""
    res = form_of(client, token, application_no)

    assert NATIONAL_ID not in res.text
    assert res.json()["applicant"]["national_id_masked"].endswith(NATIONAL_ID[-1])


def test_signature_appears_in_the_form_after_signing(client, token, application_no):
    # ชื่อไฟล์ภาษาไทยเพราะหน้าเว็บตั้งชื่อไฟล์ว่า "ลายมือชื่อ.png" ตอนส่งขึ้นมา
    res = sign(client, token, application_no, name="ลายมือชื่อ.png")
    assert res.status_code == 201, res.text
    assert res.json()["original_name"] == "ลายมือชื่อ.png"

    body = form_of(client, token, application_no).json()
    assert body["signature"]["version_no"] == 1
    assert body["signature"]["status"] == "uploaded"

    # หน้าพิมพ์ต้องโหลดรูปลายมือชื่อมาแสดงได้จริงด้วย id ที่ส่งมา
    file_id = body["signature"]["file_id"]
    res = client.get(
        f"/api/v1/applications/{application_no}/documents/file/{file_id}", headers=auth(token)
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"


def test_signing_again_replaces_the_signature_shown_on_the_form(client, token, application_no):
    sign(client, token, application_no)
    sign(client, token, application_no)

    body = form_of(client, token, application_no).json()
    assert body["signature"]["version_no"] == 2, "หน้าพิมพ์ต้องใช้ลายมือชื่อรุ่นล่าสุด"


def test_signature_slot_refuses_a_scanned_pdf(client, token, application_no):
    res = sign(client, token, application_no, data=PDF, name="scan.pdf", mime="application/pdf")

    assert res.status_code == 422
    assert "ลายมือชื่อ" in res.json()["detail"]


def test_form_locks_after_the_application_is_filed(client, token, application_no):
    """ยื่นแล้วแก้ลายมือชื่อไม่ได้ และหน้าพิมพ์ต้องมีวันที่แจ้ง"""
    sign(client, token, application_no)
    for code in ["A02", "A03", "B01"]:
        client.post(
            f"/api/v1/applications/{application_no}/documents/{code}",
            headers=auth(token),
            files={"file": ("doc.pdf", PDF, "application/pdf")},
        )
    for code in ["A04", "A05"]:  # สองฉบับนี้รับเฉพาะรูปภาพ
        client.post(
            f"/api/v1/applications/{application_no}/documents/{code}",
            headers=auth(token),
            files={"file": ("photo.png", PNG, "image/png")},
        )
    res = client.post(f"/api/v1/applications/{application_no}/submit", headers=auth(token))
    assert res.status_code == 200, res.text

    body = form_of(client, token, application_no).json()
    assert body["filed_on"] is not None
    assert body["can_sign"] is False


def test_each_property_type_gets_only_its_own_form(client, token, application_no):
    """ไม่เข้าข่ายโรงแรมใช้ A01 ส่วนประเภทที่ 1/2 ใช้แบบ ร.ร.1 (A06) สลับกันไม่ได้"""
    hotel = start(client, token, rooms=20, guests=60)

    for no, wrong_code in [(application_no, "A06"), (hotel, "A01")]:
        res = form_of(client, token, no, wrong_code)
        assert res.status_code == 404
        # ข้อความต้องบอกว่าเป็นเพราะประเภทที่พัก ไม่ใช่ "ไม่พบ" ลอย ๆ (NFR Usability)
        assert "ประเภท" in res.json()["detail"]


def test_hotel_form_carries_what_the_rr1_paper_needs(client, token):
    """แบบ ร.ร.1 ต้องมีประเภทโรงแรม ค่าธรรมเนียม และช่องแนบ A07–A09 ในตัวมันเอง"""
    no = start(client, token, rooms=20, guests=60)

    body = form_of(client, token, no, "A06").json()

    assert body["form_code"] == "A06"
    assert body["title"] == "แบบ ร.ร.1"
    assert body["requires_license"] is True
    assert "ประเภทที่ 1" in body["property_type_name"]
    assert body["fee"]["amount"] > 0, "ประเภทที่มีใบอนุญาตต้องมีค่าธรรมเนียมให้พิมพ์ลงแบบฟอร์ม"

    attachments = {a["code"]: a for a in body["attachments"]}
    assert set(attachments) == {"A07", "A08", "A09"}
    assert all(a["is_attached"] is False for a in attachments.values())
    # ช่องแนบในแบบ ร.ร.1 ไม่บังคับ เพราะบางฉบับไม่มีจริงตามรูปแบบกิจการ
    assert all(a["is_mandatory"] is False for a in attachments.values())


def test_hotel_form_ticks_the_attachment_once_it_is_uploaded(client, token):
    no = start(client, token, rooms=20, guests=60)
    res = client.post(
        f"/api/v1/applications/{no}/documents/A07",
        headers=auth(token),
        files={"file": ("doc.pdf", PDF, "application/pdf")},
    )
    assert res.status_code == 201, res.text

    attachments = {a["code"]: a for a in form_of(client, token, no, "A06").json()["attachments"]}
    assert attachments["A07"]["is_attached"] is True
    assert attachments["A08"]["is_attached"] is False


def test_notice_form_has_no_attachment_boxes(client, token, application_no):
    """หนังสือแจ้งฯ ไม่มีช่องแนบอยู่ในตัวแบบฟอร์ม ต่างจาก ร.ร.1"""
    assert form_of(client, token, application_no).json()["attachments"] == []


def test_hotel_form_can_be_signed_like_the_notice_form(client, token):
    """แบบ ร.ร.1 ใช้กลไกลายมือชื่อชุดเดียวกับ A01 ไม่ได้เขียนกลไกใหม่"""
    no = start(client, token, rooms=20, guests=60)
    res = client.post(
        f"/api/v1/applications/{no}/documents/A06",
        headers=auth(token),
        files={"file": ("ลายมือชื่อ.png", PNG, "image/png")},
    )
    assert res.status_code == 201, res.text
    assert form_of(client, token, no, "A06").json()["signature"]["version_no"] == 1


# ---------------------------------------------------------------- ชื่อผู้ยื่นบนแบบฟอร์ม


def test_applicant_name_starts_from_the_account_and_can_be_changed(client, token, application_no):
    """แบบ ร.ร.1 มีช่องบุคคลธรรมดา/นิติบุคคล ผู้ยื่นจึงต้องแก้ชื่อบนแบบฟอร์มได้เอง"""
    assert form_of(client, token, application_no).json()["applicant"]["is_juristic"] is False

    res = client.patch(
        f"/api/v1/applications/{application_no}/applicant",
        headers=auth(token),
        json={
            "display_name": "บริษัท ภูเก็ตสเตย์ จำกัด",
            "is_juristic": True,
            "juristic_reg_no": "0-8355-48000-12-3",
        },
    )
    assert res.status_code == 200, res.text
    # เก็บเป็นตัวเลขล้วนเหมือนเบอร์โทร เลขเดียวกันที่พิมพ์คนละแบบต้องไม่กลายเป็นคนละเลข
    assert res.json()["juristic_reg_no"] == "0835548000123"

    applicant = form_of(client, token, application_no).json()["applicant"]
    assert applicant["display_name"] == "บริษัท ภูเก็ตสเตย์ จำกัด"
    assert applicant["is_juristic"] is True


def test_juristic_applicant_must_give_a_registration_number(client, token, application_no):
    res = client.patch(
        f"/api/v1/applications/{application_no}/applicant",
        headers=auth(token),
        json={"display_name": "บริษัท ไม่ใส่เลข จำกัด", "is_juristic": True},
    )
    assert res.status_code == 422
    assert "13 หลัก" in res.json()["detail"]


def test_switching_back_to_a_person_clears_the_registration_number(client, token, application_no):
    client.patch(
        f"/api/v1/applications/{application_no}/applicant",
        headers=auth(token),
        json={
            "display_name": "บริษัท ภูเก็ตสเตย์ จำกัด",
            "is_juristic": True,
            "juristic_reg_no": "0835548000123",
        },
    )
    res = client.patch(
        f"/api/v1/applications/{application_no}/applicant",
        headers=auth(token),
        json={"display_name": "สมหญิง ใจดี", "is_juristic": False},
    )

    assert res.status_code == 200, res.text
    assert res.json()["juristic_reg_no"] is None, "กลับเป็นบุคคลธรรมดาแล้วต้องไม่เหลือเลขค้างไว้"


def test_other_peoples_forms_are_not_reachable(client, token, application_no):
    """ฝาแฝดของ T-09 ฝั่งผู้ยื่น — เส้นทางใหม่ต้องถูกกันด้วยกติกาเดียวกัน"""
    other = client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "คนอื่น",
            "last_name": "ทดสอบ",
            "national_id": make_valid("392220004422"),
            "phone": "0899960042",
            "email": "pytest-notice-form-other@example.com",
            "password": "demo1234",
        },
    )
    assert other.status_code == 201, other.text
    try:
        res = form_of(client, other.json()["access_token"], application_no)
        assert res.status_code == 404
    finally:
        with SessionLocal() as db:
            ids = list(
                db.scalars(
                    select(User.id).where(User.email == "pytest-notice-form-other@example.com")
                ).all()
            )
            db.execute(delete(AuditLog).where(AuditLog.actor_id.in_(ids)))
            db.execute(delete(Operator).where(Operator.user_id.in_(ids)))
            db.execute(delete(User).where(User.id.in_(ids)))
            db.commit()
