"""ทดสอบรายการเอกสารของเส้น "ไม่เข้าข่ายโรงแรม" (M3, M4)

อ่านจากฐานข้อมูลจริงที่ seed ไว้ ไม่ได้อ่านจากไฟล์ seed
เพื่อพิสูจน์ว่าโค้ดส่วนอื่นดึงข้อมูลจากตารางได้จริงตามกฎข้อ 1 ของทีม
"""

import pytest
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.authority import ContactPoint, LocalAuthority
from app.models.classification import PropertyType
from app.models.document import DocumentRequirement, DocumentType
from app.models.enums import DocumentCategory

NOT_HOTEL = "not_hotel"


@pytest.fixture(scope="module")
def db():
    with SessionLocal() as session:
        yield session


def requirements(db) -> list[DocumentRequirement]:
    ptype = db.scalar(select(PropertyType).where(PropertyType.code == NOT_HOTEL))
    assert ptype is not None, "ยังไม่ได้ seed ประเภทที่พัก — รัน uv run python -m app.seeds.run"
    return list(
        db.scalars(
            select(DocumentRequirement)
            .join(DocumentType)
            .where(DocumentRequirement.property_type_id == ptype.id)
            .order_by(DocumentType.display_order)
        ).all()
    )


def test_not_hotel_still_has_a_document_list(db):
    """ตารางข้อ 4: ไม่เข้าข่ายโรงแรม "ไม่ต้องขอใบอนุญาต แต่ต้องดำเนินการแจ้ง
    ตามแนวทางที่กำหนด ระบบต้องแสดงรายการเอกสารและหน่วยงานที่ต้องติดต่อ"

    เส้นนี้จึงต้องมีรายการเอกสาร ไม่ใช่จบแค่บอกว่าไม่เข้าข่าย
    """
    codes = [r.document_type.code for r in requirements(db)]
    assert codes == ["A01", "A02", "B01", "A03", "A04", "A05"]


def test_documents_are_split_into_two_categories(db):
    """M3: ต้องแบ่ง 2 หมวดชัดเจน — ทำเองได้ / ต้องขอจากหน่วยงานอื่น"""
    by_category = {DocumentCategory.SELF: [], DocumentCategory.EXTERNAL: []}
    for r in requirements(db):
        by_category[r.document_type.category].append(r.document_type.code)

    assert by_category[DocumentCategory.SELF] == ["A01", "A02", "A03", "A04", "A05"]
    assert by_category[DocumentCategory.EXTERNAL] == ["B01"]


def test_external_document_answers_all_four_questions_of_m4(db):
    """M4 บังคับ 4 อย่าง: หน่วยงานใด / ท้องถิ่นใด / ใช้เอกสารประกอบอะไร / ใช้เวลาเท่าใด"""
    doc = db.scalar(select(DocumentType).where(DocumentType.code == "B01"))

    assert doc.issuing_agency is not None, "หน่วยงานใด"
    assert doc.preparation_note, "ใช้เอกสารประกอบอะไร"
    assert doc.estimated_days and doc.estimated_days > 0, "ใช้เวลาเท่าใด"

    # "ท้องถิ่นใด" — ต้องมีจุดติดต่อครบทุก อปท. ไม่งั้นผู้ใช้บางเขตจะไม่เห็นข้อมูล
    authorities = db.scalars(select(LocalAuthority.id)).all()
    contacts = db.scalars(
        select(ContactPoint.local_authority_id).where(
            ContactPoint.issuing_agency_id == doc.issuing_agency_id
        )
    ).all()
    assert set(contacts) == set(authorities), "ต้องมีจุดติดต่อครบทั้ง 19 อปท."


def test_contact_point_is_specific_to_the_authority(db):
    """ผู้ใช้เขตกะรนต้องไม่เห็นที่อยู่ของเขตอื่น — เป็นปัญหาข้อ 3 ที่โจทย์ยกมา"""
    karon = db.scalar(select(LocalAuthority).where(LocalAuthority.code == "KRN-SUB"))
    contact = db.scalar(select(ContactPoint).where(ContactPoint.local_authority_id == karon.id))
    assert karon.name in contact.office_name


def test_self_service_form_is_marked_so_ui_does_not_ask_for_upload(db):
    """A01 กรอกในระบบ ไม่ใช่ไฟล์ที่ผู้ใช้ไปหามาจากที่อื่น"""
    form = db.scalar(select(DocumentType).where(DocumentType.code == "A01"))
    assert form.is_system_form is True
    assert form.issuing_agency_id is None, "เอกสารที่กรอกเองต้องไม่มีหน่วยงานที่ต้องไปติดต่อ"


def test_building_photos_allow_multiple_files(db):
    """A04 แนบได้หลายมุม ส่วนฉบับอื่นแนบได้ฉบับเดียว"""
    docs = {d.code: d for d in db.scalars(select(DocumentType)).all()}
    assert docs["A04"].allows_multiple is True
    assert [c for c, d in docs.items() if d.allows_multiple] == ["A04"]


@pytest.mark.parametrize(
    "code,expected",
    [
        ("B01", ["application/pdf"]),  # เอกสารที่หน่วยงานลงนามแล้ว
        ("A03", ["application/pdf"]),  # เอกสารสิทธิ์ที่ดิน
        ("A02", ["application/pdf", "image/jpeg", "image/png"]),  # ถ่ายรูปได้ (US-04)
        ("A04", ["image/jpeg", "image/png"]),  # ภาพถ่ายอาคาร
        ("A05", ["image/jpeg", "image/png"]),  # รูปถ่ายผู้แจ้ง
    ],
)
def test_accepted_file_types_come_from_the_database(db, code, expected):
    """M5 ตรวจชนิดไฟล์ — เงื่อนไขเก็บใน DB ให้ Super Admin แก้ได้ (US-09)"""
    doc = db.scalar(select(DocumentType).where(DocumentType.code == code))
    assert doc.accepted_mime_list == expected
