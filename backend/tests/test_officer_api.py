"""ทดสอบหน้าทำงานเจ้าหน้าที่ (M8, M9, T-08, T-09)

เคสสำคัญที่สุดคือ T-09: เจ้าหน้าที่เขตหนึ่งเปิดคำขอของอีกเขตต้องถูกปฏิเสธ
**และความพยายามนั้นต้องถูกบันทึกไว้** โจทย์เขียนข้อหลังไว้ชัด คนมักทำแต่ข้อแรก
"""

import shutil
from random import randint
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.db import SessionLocal
from app.main import app
from app.models.application import Application, ApplicationStatusHistory
from app.models.audit import AuditLog
from app.models.authority import LocalAuthority
from app.models.classification import ApplicationClassification
from app.models.document import DocumentFile, DocumentReview
from app.models.license import License
from app.models.property import Operator, Property
from app.models.user import OfficerAssignment, User
from app.services import document as doc_svc
from tests.test_thai_id import make_valid

# ผู้ใช้ของแต่ละเคสต้องไม่ปนกัน เพราะเคสหนึ่งเปลี่ยนบทบาทและสังกัดของผู้ใช้
# ถ้าใช้อีเมลชุดเดียวกันทุกเคสแล้วลบทิ้งระหว่างทาง จะมีจังหวะที่ token ของเคสหนึ่ง
# ชี้ไปยังผู้ใช้ที่อีกเคสลบไปแล้ว ทำให้เทสต์ล้มแบบสุ่ม
EMAIL_PREFIX = "pytest-officer-"

PDF = b"%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "3df80000000c4944415408d763f8cfc000000301010018dd8db00000000049454e44ae426082"
)


def _test_users(db) -> list[int]:
    return list(db.scalars(select(User.id).where(User.email.like(f"{EMAIL_PREFIX}%"))).all())


def _cleanup() -> None:
    """ล้างผู้ใช้ทดสอบทั้งหมดของไฟล์นี้ พร้อมข้อมูลที่ผูกอยู่

    ลบจากปลายทางย้อนขึ้นต้นทาง ไม่งั้นติด foreign key
    """
    with SessionLocal() as db:
        user_ids = _test_users(db)
        if not user_ids:
            return

        operator_ids = list(
            db.scalars(select(Operator.id).where(Operator.user_id.in_(user_ids))).all()
        )
        apps = (
            list(
                db.scalars(
                    select(Application).where(Application.operator_id.in_(operator_ids))
                ).all()
            )
            if operator_ids
            else []
        )
        app_ids = [a.id for a in apps]
        for row in apps:
            shutil.rmtree(doc_svc.storage_root() / row.application_no, ignore_errors=True)

        if app_ids:
            db.execute(delete(License).where(License.application_id.in_(app_ids)))
            file_ids = list(
                db.scalars(
                    select(DocumentFile.id).where(DocumentFile.application_id.in_(app_ids))
                ).all()
            )
            if file_ids:
                db.execute(
                    delete(DocumentReview).where(DocumentReview.document_file_id.in_(file_ids))
                )
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

        db.execute(delete(OfficerAssignment).where(OfficerAssignment.officer_id.in_(user_ids)))
        db.execute(delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))
        db.execute(delete(User).where(User.id.in_(user_ids)))
        db.commit()


def _register(client: TestClient, role_tag: str) -> tuple[str, str]:
    """สมัครผู้ใช้ใหม่ที่ไม่ซ้ำกับใคร คืน (token, email)"""
    tag = uuid4().hex[:8]
    email = f"{EMAIL_PREFIX}{role_tag}-{tag}@example.com"
    # เลขบัตรและเบอร์ต้องไม่ซ้ำเช่นกัน สร้างจากตัวเลขสุ่มแล้วเติมหลักตรวจสอบ
    national_id = make_valid(f"{randint(10**11, 10**12 - 1)}")
    phone = f"09{randint(10**7, 10**8 - 1)}"

    res = client.post(
        "/api/v1/auth/register",
        json={
            "first_name": "ทดสอบ",
            "last_name": role_tag,
            "national_id": national_id,
            "phone": phone,
            "email": email,
            "password": "demo1234",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["access_token"], email


def _make_officer(client: TestClient, code: str) -> str:
    """สมัครแล้วเลื่อนเป็นเจ้าหน้าที่ของ อปท. ที่กำหนด

    ปกติ Super Admin เป็นคนตั้งบทบาทและสังกัด (US-09) ที่นี่เซ็ตตรงในฐานข้อมูล
    เพราะหน้าจัดการผู้ใช้ยังไม่ถูกสร้าง
    """
    _, email = _register(client, "officer")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        authority = db.scalar(select(LocalAuthority).where(LocalAuthority.code == code))
        user.role = "officer"
        db.add(OfficerAssignment(officer_id=user.id, local_authority_id=authority.id))
        db.commit()

    # role เปลี่ยนหลังออก token เดิม ต้องล็อกอินใหม่ให้ token มี role ที่ถูกต้อง
    return client.post(
        "/api/v1/auth/login", json={"identifier": email, "password": "demo1234"}
    ).json()["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module", autouse=True)
def _clean_module():
    """ล้างครั้งเดียวก่อนและหลังทั้งไฟล์

    ไม่ล้างระหว่างเคส เพราะผู้ใช้ของแต่ละเคสไม่ซ้ำกันอยู่แล้ว
    และการลบระหว่างทางคือต้นเหตุที่ทำให้เทสต์ล้มแบบสุ่ม
    """
    _cleanup()
    yield
    _cleanup()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def owner(client) -> str:
    token, _ = _register(client, "owner")
    return token


@pytest.fixture
def officer_a(client) -> str:
    """เจ้าหน้าที่เทศบาลนครภูเก็ต"""
    return _make_officer(client, "PKT-CITY")


@pytest.fixture
def officer_b(client) -> str:
    """เจ้าหน้าที่เทศบาลตำบลกะรน"""
    return _make_officer(client, "KRN-SUB")


def authority_id(client, code: str) -> int:
    return next(
        a["id"] for a in client.get("/api/v1/wizard/local-authorities").json() if a["code"] == code
    )


def open_application(client, owner_token, code: str, rooms: int = 6, guests: int = 24) -> str:
    res = client.post(
        "/api/v1/applications",
        headers=auth(owner_token),
        json={
            "rooms": rooms,
            "guests": guests,
            "has_restaurant": False,
            "local_authority_id": authority_id(client, code),
            "property_name": f"ที่พักเขต {code}",
            "address": {
                "address_no": "1",
                "sub_district": "ตำบลทดสอบ",
                "district": "เมืองภูเก็ต",
                "postal_code": "83000",
            },
            "accommodation_kind": "detached_house",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["application_no"]


def fill_and_submit(client, owner_token, no: str) -> None:
    """แนบเอกสารบังคับให้ครบตามที่ API บอก แล้วยื่น

    อ่านรายการจากคำขอจริงแทนการเขียนรหัสเอกสารตายตัวไว้ในเทสต์
    เพราะแต่ละประเภทที่พักใช้รายการคนละชุด และรายการแก้ได้จากหน้า Super Admin
    ถ้าเขียนตายตัว เทสต์จะล้มทุกครั้งที่ทีมเพิ่มเอกสารใหม่ทั้งที่ระบบยังถูกต้อง
    """
    detail = client.get(f"/api/v1/applications/{no}", headers=auth(owner_token)).json()
    documents = detail["documents"]["self_service"] + detail["documents"]["external"]

    for doc in documents:
        # ฉบับที่ไม่บังคับไม่ต้องแนบ ส่วนแบบฟอร์มในระบบต้องแนบ "รูปลายมือชื่อ"
        # ซึ่งเข้าเงื่อนไขเดียวกับเอกสารที่รับเฉพาะรูปภาพ จึงไม่ต้องแยกเคส
        if not doc["is_mandatory"]:
            continue
        is_pdf_only = doc["accepted_mime"] == ["application/pdf"]
        payload = (
            ("doc.pdf", PDF, "application/pdf") if is_pdf_only else ("p.png", PNG, "image/png")
        )
        res = client.post(
            f"/api/v1/applications/{no}/documents/{doc['code']}",
            headers=auth(owner_token),
            files={"file": payload},
        )
        assert res.status_code == 201, f"{doc['code']}: {res.text}"

    submitted = client.post(f"/api/v1/applications/{no}/submit", headers=auth(owner_token))
    assert submitted.status_code == 200, submitted.text


def file_ids(client, officer_token, no: str) -> dict[str, int]:
    body = client.get(f"/api/v1/officer/applications/{no}", headers=auth(officer_token)).json()
    docs = body["documents"]["self_service"] + body["documents"]["external"]
    return {d["code"]: d["files"][0]["id"] for d in docs if d["files"]}


def test_queue_shows_only_applications_in_my_authority(client, owner, officer_a):
    """T-09 ฝั่งคิวงาน: คำขอของเขตอื่นต้องไม่โผล่มาให้เห็นตั้งแต่แรก"""
    mine = open_application(client, owner, "PKT-CITY")
    other = open_application(client, owner, "KRN-SUB")
    fill_and_submit(client, owner, mine)
    fill_and_submit(client, owner, other)

    rows = client.get("/api/v1/officer/queue", headers=auth(officer_a)).json()
    numbers = [r["application_no"] for r in rows]

    assert mine in numbers
    assert other not in numbers


def test_approved_application_stays_in_the_queue_until_the_document_is_issued(
    client, owner, officer_a
):
    """บั๊กที่เคยเจอ: พออนุมัติแล้วคำขอหายจากคิวทันที

    ผลคือเจ้าหน้าที่กดปุ่ม "ออกใบอนุญาต" ไม่ได้อีกเลย เพราะไม่มีทางกลับไปที่
    คำขอนั้นผ่านหน้าจอ ทำให้ M10 เข้าไม่ถึง
    คำขอที่อนุมัติแล้วยังค้างงานอยู่หนึ่งขั้น จึงต้องอยู่ในคิวต่อ
    """
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)

    def in_queue(scope: str) -> str | None:
        rows = client.get(f"/api/v1/officer/queue?scope={scope}", headers=auth(officer_a)).json()
        return next((r["status"] for r in rows if r["application_no"] == no), None)

    assert in_queue("open") == "submitted"

    approve_fully(client, owner, officer_a, no)
    assert in_queue("open") == "approved", "อนุมัติแล้วต้องยังอยู่ในคิว รอออกเอกสาร"
    assert in_queue("closed") is None

    issue(client, officer_a, no)
    assert in_queue("open") is None, "ออกเอกสารแล้วถึงจะออกจากคิว"
    assert in_queue("closed") == "license_issued"
    assert in_queue("all") == "license_issued"


def test_queue_separates_work_by_whose_turn_it_is(client, owner, officer_a):
    """แท็บ "รอฉันดำเนินการ" กับ "รอผู้ยื่นแก้ไข" ต้องแยกกัน

    คำขอที่ส่งกลับให้แก้ไขไม่ใช่งานของเจ้าหน้าที่แล้ว จนกว่าผู้ยื่นจะส่งกลับมา
    ถ้าปนกันอยู่คิวเดียว เจ้าหน้าที่จะแยกไม่ออกว่าอันไหนต้องลงมือเอง
    """
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)

    def scope_of(scope: str) -> bool:
        rows = client.get(f"/api/v1/officer/queue?scope={scope}", headers=auth(officer_a)).json()
        return any(r["application_no"] == no for r in rows)

    assert scope_of("open") and not scope_of("revision")

    client.post(
        f"/api/v1/officer/applications/{no}/decide",
        headers=auth(officer_a),
        json={"decision": "request_revision", "reason": "ขอเอกสารเพิ่ม"},
    )
    assert scope_of("revision"), "ส่งกลับแก้ไขแล้วต้องไปอยู่แท็บรอผู้ยื่น"
    assert not scope_of("open"), "และต้องไม่ค้างอยู่ในคิวงานของเจ้าหน้าที่"
    assert scope_of("all")

    # ผู้ยื่นส่งกลับมาแล้วต้องเด้งกลับเข้าคิวเจ้าหน้าที่
    client.post(f"/api/v1/applications/{no}/submit", headers=auth(owner))
    assert scope_of("open") and not scope_of("revision")


def test_revision_reason_reaches_the_person_who_has_to_fix_it(client, owner, officer_a):
    """M8/M9: เหตุผลที่ตีกลับต้องไปถึงผู้ยื่น ไม่ใช่เห็นแต่ฝั่งเจ้าหน้าที่"""
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)

    client.post(
        f"/api/v1/officer/applications/{no}/decide",
        headers=auth(officer_a),
        json={"decision": "request_revision", "reason": "สำเนาทะเบียนบ้านเบลอ อ่านเลขที่บ้านไม่ออก"},
    )

    body = client.get(f"/api/v1/applications/{no}", headers=auth(owner)).json()
    assert body["decision_reason"] == "สำเนาทะเบียนบ้านเบลอ อ่านเลขที่บ้านไม่ออก"


def test_queue_rejects_an_unknown_scope(client, officer_a):
    res = client.get("/api/v1/officer/queue?scope=mystery", headers=auth(officer_a))
    assert res.status_code == 422


def test_queue_never_shows_drafts(client, owner, officer_a):
    """ร่างคือคำขอที่ผู้ยื่นยังไม่ได้ส่งมา เจ้าหน้าที่ไม่ควรเห็นไม่ว่ากลุ่มไหน"""
    draft = open_application(client, owner, "PKT-CITY")

    for scope in ("open", "closed", "all"):
        rows = client.get(f"/api/v1/officer/queue?scope={scope}", headers=auth(officer_a)).json()
        assert draft not in [r["application_no"] for r in rows], scope


def test_t09_opening_another_authoritys_application_is_denied_and_logged(client, owner, officer_a):
    """T-09 เต็มรูปแบบ: ปฏิเสธ **และบันทึกความพยายามนั้นไว้**"""
    other = open_application(client, owner, "KRN-SUB")
    fill_and_submit(client, owner, other)

    res = client.get(f"/api/v1/officer/applications/{other}", headers=auth(officer_a))
    assert res.status_code == 403
    assert "นอกเขต" in res.json()["detail"]

    with SessionLocal() as db:
        logged = db.scalar(
            select(AuditLog)
            .where(
                AuditLog.actor_id.in_(_test_users(db)),
                AuditLog.action == "officer.cross_authority_denied",
            )
            .order_by(AuditLog.id.desc())
        )
    assert logged is not None, "ต้องบันทึกความพยายามเปิดคำขอข้ามเขต"
    assert logged.outcome == "denied"
    assert other in logged.detail


def test_cross_authority_block_applies_to_every_action(client, owner, officer_a, officer_b):
    """กันข้ามเขตต้องครอบทุกปุ่ม ไม่ใช่แค่หน้ารายละเอียด"""
    other = open_application(client, owner, "KRN-SUB")
    fill_and_submit(client, owner, other)
    ids = file_ids(client, officer_b, other)

    review = client.post(
        f"/api/v1/officer/applications/{other}/documents/{ids['A02']}/review",
        headers=auth(officer_a),
        json={"decision": "pass"},
    )
    decide = client.post(
        f"/api/v1/officer/applications/{other}/decide",
        headers=auth(officer_a),
        json={"decision": "approve"},
    )
    assert review.status_code == 403
    assert decide.status_code == 403


def test_officer_can_open_documents_in_scope_but_not_across_authorities(client, owner, officer_a):
    """เจ้าหน้าที่ต้องเปิดไฟล์ได้จริง ไม่งั้นตรวจเอกสารไม่ได้ — แต่ต้องไม่ข้ามเขต"""
    mine = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, mine)
    ids = file_ids(client, officer_a, mine)

    # ใช้ B01 เพราะรับเฉพาะ PDF จึงรู้แน่ว่าไฟล์ที่แนบไว้คือไฟล์ไหน
    opened = client.get(
        f"/api/v1/officer/applications/{mine}/documents/file/{ids['B01']}",
        headers=auth(officer_a),
    )
    assert opened.status_code == 200
    assert opened.content == PDF

    other = open_application(client, owner, "KRN-SUB")
    fill_and_submit(client, owner, other)
    assert (
        client.get(
            f"/api/v1/officer/applications/{other}/documents/file/1",
            headers=auth(officer_a),
        ).status_code
        == 403
    )


def test_operator_cannot_use_officer_endpoints(client, owner):
    assert client.get("/api/v1/officer/queue", headers=auth(owner)).status_code == 403


def test_reviewing_first_document_claims_the_application(client, owner, officer_a):
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)
    ids = file_ids(client, officer_a, no)

    body = client.post(
        f"/api/v1/officer/applications/{no}/documents/{ids['A02']}/review",
        headers=auth(officer_a),
        json={"decision": "pass"},
    ).json()

    assert body["status"] == "under_review"
    assert "A02" not in " ".join(body["pending_documents"])


def test_revision_requires_a_reason(client, owner, officer_a):
    """ผู้ยื่นต้องรู้ว่าต้องแก้อะไร การขอแก้ไขโดยไม่บอกเหตุผลจึงต้องถูกกัน"""
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)
    ids = file_ids(client, officer_a, no)

    res = client.post(
        f"/api/v1/officer/applications/{no}/documents/{ids['A02']}/review",
        headers=auth(officer_a),
        json={"decision": "request_revision"},
    )
    assert res.status_code == 422
    assert "เหตุผล" in res.json()["detail"]


def test_cannot_approve_before_every_mandatory_document_passes(client, owner, officer_a):
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)

    res = client.post(
        f"/api/v1/officer/applications/{no}/decide",
        headers=auth(officer_a),
        json={"decision": "approve"},
    )
    assert res.status_code == 422
    assert "ยังไม่ผ่านการตรวจ" in res.json()["detail"]


def test_t08_request_revision_reopens_uploads_for_the_operator(client, owner, officer_a):
    """T-08: ขอเอกสารเพิ่ม -> สถานะเปลี่ยนเป็นรอผู้ยื่นแก้ไข และแก้ไขได้จริง"""
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)

    decided = client.post(
        f"/api/v1/officer/applications/{no}/decide",
        headers=auth(officer_a),
        json={"decision": "request_revision", "reason": "สำเนาทะเบียนบ้านอ่านไม่ชัด"},
    ).json()
    assert decided["status"] == "needs_revision"
    assert decided["decision_reason"] == "สำเนาทะเบียนบ้านอ่านไม่ชัด"

    # ยื่นแล้วเคยถูกล็อก ตอนนี้ต้องส่งใหม่ได้
    again = client.post(
        f"/api/v1/applications/{no}/documents/A02",
        headers=auth(owner),
        files={"file": ("fixed.pdf", PDF, "application/pdf")},
    )
    assert again.status_code == 201
    assert again.json()["version_no"] == 2, "ส่งใหม่ต้องเป็นรุ่นใหม่ ไม่ทับของเดิม"

    assert (
        client.post(f"/api/v1/applications/{no}/submit", headers=auth(owner)).json()["status"]
        == "submitted"
    )


def test_full_review_to_approval_writes_the_whole_trail(client, owner, officer_a):
    """M9: ทุกการเปลี่ยนสถานะต้องรู้ว่าใครทำ เมื่อใด จากสถานะใดเป็นสถานะใด"""
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)

    for file_id in file_ids(client, officer_a, no).values():
        client.post(
            f"/api/v1/officer/applications/{no}/documents/{file_id}/review",
            headers=auth(officer_a),
            json={"decision": "pass"},
        )

    body = client.post(
        f"/api/v1/officer/applications/{no}/decide",
        headers=auth(officer_a),
        json={"decision": "approve"},
    ).json()

    assert body["status"] == "approved"
    assert body["decided_at"] is not None
    assert body["can_approve"] is False

    with SessionLocal() as db:
        application = db.scalar(select(Application).where(Application.application_no == no))
        history = [
            h.to_status
            for h in db.scalars(
                select(ApplicationStatusHistory)
                .where(ApplicationStatusHistory.application_id == application.id)
                .order_by(ApplicationStatusHistory.id)
            ).all()
        ]
        assert history == ["draft", "submitted", "under_review", "approved"]

        reviews = list(
            db.scalars(
                select(DocumentReview).where(
                    DocumentReview.reviewer_id == application.assigned_officer_id
                )
            ).all()
        )
        # 5 ฉบับบังคับ + ลายมือชื่อในแบบหนังสือแจ้งฯ ซึ่งก็ต้องถูกตรวจเหมือนกัน
        assert len(reviews) == 6, "ต้องมีผลตรวจรายฉบับครบทุกฉบับ"
        assert all(r.reviewed_at is not None for r in reviews)


def test_decided_application_cannot_be_changed_again(client, owner, officer_a):
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)
    ids = file_ids(client, officer_a, no)
    for file_id in ids.values():
        client.post(
            f"/api/v1/officer/applications/{no}/documents/{file_id}/review",
            headers=auth(officer_a),
            json={"decision": "pass"},
        )
    client.post(
        f"/api/v1/officer/applications/{no}/decide",
        headers=auth(officer_a),
        json={"decision": "approve"},
    )

    again = client.post(
        f"/api/v1/officer/applications/{no}/decide",
        headers=auth(officer_a),
        json={"decision": "reject", "reason": "เปลี่ยนใจ"},
    )
    review = client.post(
        f"/api/v1/officer/applications/{no}/documents/{ids['A02']}/review",
        headers=auth(officer_a),
        json={"decision": "pass"},
    )
    assert again.status_code == 422
    assert review.status_code == 422


def test_rejecting_requires_a_reason(client, owner, officer_a):
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)

    res = client.post(
        f"/api/v1/officer/applications/{no}/decide",
        headers=auth(officer_a),
        json={"decision": "reject"},
    )
    assert res.status_code == 422


# ---------------------------------------------------------------- M10 ใบอนุญาต


def issue(client, officer, no: str, *, signature=PNG, mime="image/png"):
    """ออกเอกสารต้องแนบลายมือชื่อผู้ลงนามเสมอ (M10)"""
    files = {"signature": ("sign.png", signature, mime)} if signature is not None else None
    return client.post(
        f"/api/v1/officer/applications/{no}/issue-license", headers=auth(officer), files=files
    )


def approve_fully(client, owner, officer, no: str) -> None:
    for file_id in file_ids(client, officer, no).values():
        client.post(
            f"/api/v1/officer/applications/{no}/documents/{file_id}/review",
            headers=auth(officer),
            json={"decision": "pass"},
        )
    client.post(
        f"/api/v1/officer/applications/{no}/decide",
        headers=auth(officer),
        json={"decision": "approve"},
    )


def test_issuing_requires_the_signature_of_the_person_who_signs(client, owner, officer_a):
    """เอกสารที่ไม่มีใครลงนามคือเอกสารที่ใช้ไม่ได้ — กติกาเดียวกับฝั่งผู้ยื่น"""
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)
    approve_fully(client, owner, officer_a, no)

    blank = issue(client, officer_a, no, signature=b"")
    assert blank.status_code == 422
    assert "ลงลายมือชื่อ" in blank.json()["detail"]

    wrong_type = issue(client, officer_a, no, signature=PDF, mime="application/pdf")
    assert wrong_type.status_code == 422

    body = client.get(f"/api/v1/officer/applications/{no}", headers=auth(officer_a)).json()
    assert body["license_no"] is None, "ยังไม่ควรมีเอกสารออกไปจนกว่าจะลงนาม"


def test_issued_document_keeps_the_signature_for_the_printed_page(client, owner, officer_a):
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)
    approve_fully(client, owner, officer_a, no)
    assert issue(client, officer_a, no).status_code == 200

    body = client.get(f"/api/v1/applications/{no}/license", headers=auth(owner)).json()
    assert body["has_issuer_signature"] is True

    # ผู้ยื่นต้องโหลดรูปมาแสดงบนหน้าพิมพ์ของตัวเองได้
    img = client.get(f"/api/v1/applications/{no}/license/signature", headers=auth(owner))
    assert img.status_code == 200
    assert img.headers["content-type"] == "image/png"


def test_m10_notice_receipt_for_properties_that_need_no_licence(client, owner, officer_a):
    """ที่พักที่ไม่เข้าข่ายโรงแรมก็ต้องได้เอกสารที่พิมพ์ได้พร้อมเลขอ้างอิง

    ตารางข้อ 5 เขียนว่าผู้ประกอบการต้อง "พิมพ์ใบอนุญาตหรือเอกสารอ้างอิง"
    กรณีนี้ไม่มีค่าธรรมเนียมและไม่มีวันหมดอายุตามตารางข้อ 4
    """
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)
    approve_fully(client, owner, officer_a, no)

    issued = issue(client, officer_a, no)
    assert issued.status_code == 200, issued.text
    assert issued.json()["status"] == "license_issued"

    doc = client.get(f"/api/v1/applications/{no}/license", headers=auth(owner)).json()
    assert doc["kind"] == "notice_receipt"
    assert doc["license_no"].startswith("NR-")
    assert doc["fee_amount"] is None
    assert doc["valid_until"] is None, "หนังสือรับรองการแจ้งไม่มีวันหมดอายุ"
    assert doc["is_expired"] is False


def test_m10_licence_snapshots_the_fee_that_applied_at_issue_time(client, owner, officer_a):
    """ข้อควรคิดข้อ 1 ของโจทย์ข้อ 8: ใบอนุญาตต้องคงอัตราเดิมไว้เสมอ"""
    no = open_application(client, owner, "PKT-CITY", rooms=20, guests=60)
    fill_and_submit(client, owner, no)
    approve_fully(client, owner, officer_a, no)
    issue(client, officer_a, no)

    doc = client.get(f"/api/v1/applications/{no}/license", headers=auth(owner)).json()
    assert doc["kind"] == "license"
    assert doc["license_no"].startswith("HL-")
    assert doc["fee_amount"] == 10000.0
    assert doc["valid_until"] is not None

    with SessionLocal() as db:
        application = db.scalar(select(Application).where(Application.application_no == no))
        row = db.scalar(select(License).where(License.application_id == application.id))
        # ต้องเก็บทั้งตัวเลขและตัวชี้กลับไปยังอัตราที่ใช้
        assert row.fee_schedule_id is not None
        assert float(row.fee_amount) == 10000.0


def test_cannot_issue_before_approval_or_twice(client, owner, officer_a):
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)

    too_early = issue(client, officer_a, no)
    assert too_early.status_code == 422
    assert "อนุมัติ" in too_early.json()["detail"]

    approve_fully(client, owner, officer_a, no)
    issue(client, officer_a, no)

    again = issue(client, officer_a, no)
    assert again.status_code == 422
    assert "ออกเอกสารไปแล้ว" in again.json()["detail"]


def test_license_is_only_visible_to_its_owner(client, owner, officer_a):
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)
    approve_fully(client, owner, officer_a, no)
    issue(client, officer_a, no)

    stranger, _ = _register(client, "stranger")
    assert (
        client.get(f"/api/v1/applications/{no}/license", headers=auth(stranger)).status_code == 404
    )


def test_license_endpoint_reports_clearly_when_nothing_issued_yet(client, owner):
    no = open_application(client, owner, "PKT-CITY")
    res = client.get(f"/api/v1/applications/{no}/license", headers=auth(owner))
    assert res.status_code == 404
    assert "ยังไม่ได้ออกเอกสาร" in res.json()["detail"]


# ---------------------------------------------------------------- M11 ภาพรวม


def test_m11_overview_counts_by_type_authority_and_stuck_step(client, owner, officer_a):
    """M11: "จำนวนคำขอแยกตามประเภทและตามท้องถิ่น และคำขอค้างอยู่ที่ขั้นตอนใดบ้าง" """
    waiting = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, waiting)

    revising = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, revising)
    client.post(
        f"/api/v1/officer/applications/{revising}/decide",
        headers=auth(officer_a),
        json={"decision": "request_revision", "reason": "ขอเอกสารเพิ่ม"},
    )

    central = client.post(
        "/api/v1/auth/login",
        json={"identifier": "central@example.com", "password": "demo1234"},
    ).json()["access_token"]

    body = client.get("/api/v1/reports/overview", headers=auth(central)).json()

    assert body["waiting_on_officer"] >= 1
    assert body["waiting_on_applicant"] >= 1

    # แยกตามประเภท: ต้องมีครบทุกประเภทแม้ประเภทที่ยังไม่มีคำขอ
    codes = [b["key"] for b in body["by_property_type"]]
    assert {"not_hotel", "type_1", "type_2", "out_of_scope"} <= set(codes)

    # ค้างที่ขั้นตอนใด: ต้องครบทุกสถานะ เพื่อให้เห็นว่าขั้นไหนเป็นศูนย์ด้วย
    statuses = [b["key"] for b in body["by_status"]]
    assert "submitted" in statuses and "needs_revision" in statuses

    # แยกตามท้องถิ่น: ต้องครบ 19 แห่ง รวมแห่งที่ยังไม่มีคำขอ
    assert len(body["by_authority"]) == 19
    names = [r["name"] for r in body["by_authority"]]
    assert "เทศบาลนครภูเก็ต" in names


def test_m11_is_read_only_summary_without_personal_data(client, owner, officer_a):
    """ส่วนกลาง "ดูภาพรวมโดยไม่ก้าวก่ายการพิจารณารายคำขอ" (ตารางข้อ 5)

    รายงานจึงต้องไม่มีเลขที่คำขอ ชื่อผู้ยื่น หรือชื่อเจ้าหน้าที่หลุดออกไป
    """
    no = open_application(client, owner, "PKT-CITY")
    fill_and_submit(client, owner, no)

    central = client.post(
        "/api/v1/auth/login",
        json={"identifier": "central@example.com", "password": "demo1234"},
    ).json()["access_token"]

    raw = client.get("/api/v1/reports/overview", headers=auth(central)).text
    assert no not in raw, "เลขที่คำขอต้องไม่หลุดไปในรายงานภาพรวม"
    assert "ที่พักเขต" not in raw, "ชื่อสถานที่ต้องไม่หลุดไปในรายงานภาพรวม"


def test_m11_is_restricted_to_central_and_admin(client, owner, officer_a):
    assert client.get("/api/v1/reports/overview", headers=auth(owner)).status_code == 403
    assert client.get("/api/v1/reports/overview", headers=auth(officer_a)).status_code == 403
    assert client.get("/api/v1/reports/overview").status_code == 401
