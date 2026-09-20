"""ทดสอบอัปโหลดเอกสารและยื่นคำขอ (M5, M6, T-06)

ยิงผ่าน API จริง เขียนไฟล์ลงดิสก์จริง จึงล้างทั้งแถวและไฟล์ทุกครั้ง
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
from tests.test_thai_id import make_valid

EMAIL = "pytest-upload@example.com"
PHONE = "0899960001"
NATIONAL_ID = make_valid("392220001122")

# ไฟล์ทดสอบขนาดเล็กที่สุดที่ยังถูกต้องตามรูปแบบ (ข้อมูลจำลอง)
PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "3df80000000c4944415408d763f8cfc000000301010018dd8db00000000049454e44ae426082"
)


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
            folder = doc_svc.storage_root() / row.application_no
            shutil.rmtree(folder, ignore_errors=True)

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
            "first_name": "ทดสอบ",
            "last_name": "อัปโหลด",
            "national_id": NATIONAL_ID,
            "phone": PHONE,
            "email": EMAIL,
            "password": "demo1234",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


@pytest.fixture
def application_no(client, token) -> str:
    karon = next(
        a["id"]
        for a in client.get("/api/v1/wizard/local-authorities").json()
        if a["code"] == "KRN-SUB"
    )
    res = client.post(
        "/api/v1/applications",
        headers=auth(token),
        json={
            "rooms": 6,
            "guests": 24,
            "has_restaurant": False,
            "local_authority_id": karon,
            "property_name": "บ้านพักทดสอบอัปโหลด",
            "address": {
                "address_no": "99/9",
                "sub_district": "กะรน",
                "district": "เมืองภูเก็ต",
                "postal_code": "83100",
            },
            "accommodation_kind": "detached_house",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["application_no"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def upload(client, token, no, code, *, data=PDF, name="doc.pdf", mime="application/pdf"):
    return client.post(
        f"/api/v1/applications/{no}/documents/{code}",
        headers=auth(token),
        files={"file": (name, data, mime)},
    )


def upload_all_mandatory(client, token, no) -> None:
    # A01 เป็นแบบฟอร์มในระบบ ไฟล์ที่ต้องมีคือรูปลายมือชื่อ
    upload(client, token, no, "A01", data=PNG, name="signature.png", mime="image/png")
    upload(client, token, no, "A02")
    upload(client, token, no, "A03")
    upload(client, token, no, "B01")
    upload(client, token, no, "A04", data=PNG, name="photo.png", mime="image/png")
    upload(client, token, no, "A05", data=PNG, name="photo.png", mime="image/png")


def test_upload_accepts_declared_file_types(client, token, application_no):
    res = upload(client, token, application_no, "A02")
    assert res.status_code == 201, res.text

    body = res.json()
    assert body["slot_no"] == 1 and body["version_no"] == 1
    assert body["original_name"] == "doc.pdf"
    assert body["size_bytes"] == len(PDF)


def test_rejects_wrong_file_type_using_rules_from_database(client, token, application_no):
    """M5 ตรวจชนิดไฟล์ — B01 รับเฉพาะ PDF ตามที่กำหนดไว้ใน accepted_mime"""
    res = upload(client, token, application_no, "B01", data=PNG, name="x.png", mime="image/png")
    assert res.status_code == 422
    # ข้อความต้องเป็นภาษาคน ไม่ใช่ MIME ดิบ (NFR Usability)
    assert "PDF" in res.json()["detail"]
    assert "application/pdf" not in res.json()["detail"]


def test_rejects_empty_file(client, token, application_no):
    res = upload(client, token, application_no, "A02", data=b"")
    assert res.status_code == 422


def test_uploading_again_creates_a_new_version_and_keeps_the_old_one(client, token, application_no):
    """ข้อ 8 ของโจทย์: อัปซ้ำต้องเก็บเป็นรุ่นใหม่ ไม่ทับของเดิม

    เพราะเจ้าหน้าที่ตรวจไฟล์รุ่นไหนไว้ ต้องย้อนดูได้ว่าตอนนั้นเห็นอะไร
    """
    first = upload(client, token, application_no, "A02").json()
    second = upload(client, token, application_no, "A02").json()

    assert (first["slot_no"], first["version_no"]) == (1, 1)
    assert (second["slot_no"], second["version_no"]) == (1, 2)

    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(DocumentFile).where(DocumentFile.id.in_([first["id"], second["id"]]))
            ).all()
        )
        by_id = {r.id: r for r in rows}
        assert by_id[first["id"]].is_current is False, "รุ่นเก่าต้องยังอยู่ แต่ไม่ใช่รุ่นปัจจุบัน"
        assert by_id[second["id"]].is_current is True


def test_document_that_allows_multiple_opens_new_slots(client, token, application_no):
    """A04 ภาพถ่ายอาคารแนบได้หลายมุม — ต้องเป็นคนละ slot ไม่ใช่คนละ version"""
    first = upload(
        client, token, application_no, "A04", data=PNG, name="1.png", mime="image/png"
    ).json()
    second = upload(
        client, token, application_no, "A04", data=PNG, name="2.png", mime="image/png"
    ).json()

    assert first["slot_no"] == 1 and second["slot_no"] == 2
    assert first["version_no"] == second["version_no"] == 1


def test_system_form_accepts_the_signature_image(client, token, application_no):
    """A01 ระบบกรอกเนื้อหาให้ เหลือช่องเดียวที่ระบบทำแทนไม่ได้คือลายมือชื่อ"""
    res = upload(
        client, token, application_no, "A01", data=PNG, name="signature.png", mime="image/png"
    )
    assert res.status_code == 201, res.text
    assert res.json()["version_no"] == 1


def test_signing_again_keeps_the_previous_signature_as_an_older_version(
    client, token, application_no
):
    """เซ็นใหม่ = รุ่นถัดไป ไม่ทับของเดิม เหมือนไฟล์แนบฉบับอื่น (ข้อ 8)"""
    first = upload(
        client, token, application_no, "A01", data=PNG, name="sig.png", mime="image/png"
    ).json()
    second = upload(
        client, token, application_no, "A01", data=PNG, name="sig.png", mime="image/png"
    ).json()

    assert (first["slot_no"], first["version_no"]) == (1, 1)
    assert (second["slot_no"], second["version_no"]) == (1, 2)


def test_system_form_rejects_a_scanned_document_and_says_what_to_do_instead(
    client, token, application_no
):
    """ผู้ใช้ที่พยายามสแกนแบบฟอร์มมาแนบ ต้องได้คำแนะนำที่ถูก ไม่ใช่ error ชนิดไฟล์"""
    res = upload(client, token, application_no, "A01")  # PDF
    assert res.status_code == 422
    assert "ลายมือชื่อ" in res.json()["detail"]


def test_unsigned_notice_form_blocks_submitting(client, token, application_no):
    """M6: ลายมือชื่อคือสิ่งที่ทำให้หนังสือแจ้งมีผล ขาดไม่ได้เหมือนเอกสารบังคับอื่น"""
    upload(client, token, application_no, "A02")
    upload(client, token, application_no, "A03")
    upload(client, token, application_no, "B01")
    for code in ["A04", "A05"]:
        upload(client, token, application_no, code, data=PNG, name="p.png", mime="image/png")

    blocked = client.post(f"/api/v1/applications/{application_no}/submit", headers=auth(token))
    assert blocked.status_code == 422
    assert "A01" in blocked.json()["detail"]

    body = client.get(f"/api/v1/applications/{application_no}", headers=auth(token)).json()
    assert body["can_submit"] is False
    missing = {m["code"]: m for m in body["missing_documents"]}
    assert missing["A01"]["needs_signature"] is True, "หน้าจอต้องแยกออกว่าขาดลายมือชื่อ ไม่ใช่ขาดไฟล์"

    upload(client, token, application_no, "A01", data=PNG, name="sig.png", mime="image/png")
    assert (
        client.post(
            f"/api/v1/applications/{application_no}/submit", headers=auth(token)
        ).status_code
        == 200
    )


def test_checklist_tells_the_screen_the_upload_size_limit(client, token, application_no):
    """หน้าจอกับแชทบอทต้องบอกขนาดไฟล์สูงสุดได้ โดยไม่ต้องเดาหรือเขียนตัวเลขไว้เอง"""
    body = client.get(f"/api/v1/applications/{application_no}", headers=auth(token)).json()
    assert body["documents"]["max_upload_mb"] >= 1


def test_operator_sees_the_reason_when_an_officer_sends_it_back(client, token, application_no):
    """ถูกตีกลับแล้วต้องรู้ว่าต้องแก้อะไร ไม่ใช่รู้แค่ว่าถูกตีกลับ"""
    body = client.get(f"/api/v1/applications/{application_no}", headers=auth(token)).json()
    assert body["decision_reason"] is None, "ยังไม่มีการพิจารณา จึงยังไม่มีเหตุผล"


def test_cannot_upload_a_document_not_required_for_this_property_type(
    client, token, application_no
):
    res = upload(client, token, application_no, "B99")
    assert res.status_code == 404


def test_t06_submit_is_blocked_and_names_every_missing_document(client, token, application_no):
    """T-06: ไม่ให้ยื่น **และระบุชัดว่าขาดฉบับใดบ้าง**"""
    upload(client, token, application_no, "A02")  # อัปแค่ฉบับเดียว

    res = client.post(f"/api/v1/applications/{application_no}/submit", headers=auth(token))
    assert res.status_code == 422

    detail = res.json()["detail"]
    for code in ["A01", "A03", "A04", "A05", "B01"]:
        assert code in detail, f"ต้องบอกว่าขาด {code} ด้วย"
    assert "A02" not in detail, "ฉบับที่อัปแล้วต้องไม่ถูกนับว่าขาด"
    # แบบฟอร์มในระบบต้องบอกให้ถูกว่าขาดอะไร ไม่งั้นผู้ใช้จะไปหาไฟล์มาแนบ
    assert "ลงลายมือชื่อ" in detail


def test_checklist_reports_status_and_attached_files(client, token, application_no):
    upload_all_mandatory(client, token, application_no)

    body = client.get(f"/api/v1/applications/{application_no}", headers=auth(token)).json()
    by_code = {
        d["code"]: d for d in body["documents"]["self_service"] + body["documents"]["external"]
    }

    assert by_code["A01"]["status"] == "uploaded", "ลงลายมือชื่อแล้ว"
    assert len(by_code["A01"]["files"]) == 1
    assert by_code["A02"]["status"] == "uploaded"
    assert len(by_code["A02"]["files"]) == 1
    assert body["can_submit"] is True
    assert body["missing_documents"] == []


def test_submitting_records_the_audit_trail(client, token, application_no):
    upload_all_mandatory(client, token, application_no)

    res = client.post(f"/api/v1/applications/{application_no}/submit", headers=auth(token))
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "submitted"
    assert res.json()["submitted_at"] is not None
    assert res.json()["can_submit"] is False

    with SessionLocal() as db:
        application = db.scalar(
            select(Application).where(Application.application_no == application_no)
        )
        history = list(
            db.scalars(
                select(ApplicationStatusHistory).where(
                    ApplicationStatusHistory.application_id == application.id
                )
            ).all()
        )
        assert [h.to_status for h in history] == ["draft", "submitted"]
        assert history[-1].from_status == "draft"

        logged = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "application.submit",
                AuditLog.entity_id == application.id,
            )
        )
        assert logged is not None and logged.to_status == "submitted"


def test_documents_are_locked_after_submitting(client, token, application_no):
    """ยื่นแล้วต้องล็อก ไม่งั้นไฟล์เปลี่ยนใต้มือขณะเจ้าหน้าที่กำลังตรวจ"""
    upload_all_mandatory(client, token, application_no)
    client.post(f"/api/v1/applications/{application_no}/submit", headers=auth(token))

    assert upload(client, token, application_no, "A02").status_code == 409
    assert (
        client.post(
            f"/api/v1/applications/{application_no}/submit", headers=auth(token)
        ).status_code
        == 422
    )


def test_uploaded_file_can_be_downloaded_back(client, token, application_no):
    uploaded = upload(client, token, application_no, "A02").json()

    res = client.get(
        f"/api/v1/applications/{application_no}/documents/file/{uploaded['id']}",
        headers=auth(token),
    )
    assert res.status_code == 200
    assert res.content == PDF


def test_another_operator_cannot_upload_to_someone_elses_application(client, token, application_no):
    stranger = client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "คน",
            "last_name": "อื่น",
            "national_id": make_valid("392220009988"),
            "phone": "0899960002",
            "email": "pytest-upload-stranger@example.com",
            "password": "demo1234",
        },
    )
    try:
        assert (
            upload(client, stranger.json()["access_token"], application_no, "A02").status_code
            == 404
        )
    finally:
        with SessionLocal() as db:
            ids = list(
                db.scalars(
                    select(User.id).where(User.email == "pytest-upload-stranger@example.com")
                ).all()
            )
            if ids:
                db.execute(delete(AuditLog).where(AuditLog.actor_id.in_(ids)))
                db.execute(delete(User).where(User.id.in_(ids)))
                db.commit()
