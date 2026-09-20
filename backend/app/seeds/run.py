"""รัน seed ข้อมูลตั้งต้นลงฐานข้อมูล

    cd backend && uv run python -m app.seeds.run

เขียนแบบ idempotent (upsert ตาม code) — รันซ้ำได้ไม่พัง และไม่สร้างข้อมูลซ้ำ
สำคัญตอนแข่ง เพราะจะได้รันซ้ำหลัง migrate ใหม่โดยไม่ต้อง drop ฐานข้อมูล
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.authority import ContactPoint, IssuingAgency, LocalAuthority
from app.models.classification import ClassificationRule, PropertyType
from app.models.document import DocumentRequirement, DocumentType
from app.models.license import FeeSchedule
from app.models.user import OfficerAssignment, User
from app.seeds.classification import (
    CLASSIFICATION_RULES,
    EFFECTIVE_FROM,
    FEE_SCHEDULES,
    PROPERTY_TYPES,
)
from app.seeds.documents import (
    CONTACT_POINT_DEFAULTS,
    DOCUMENT_REQUIREMENTS,
    DOCUMENT_TYPES,
    ISSUING_AGENCIES,
)
from app.seeds.local_authorities import LOCAL_AUTHORITIES
from app.seeds.users import DEMO_PASSWORD, DEMO_USERS


def seed_local_authorities(db: Session) -> int:
    for row in LOCAL_AUTHORITIES:
        obj = db.scalar(select(LocalAuthority).where(LocalAuthority.code == row["code"]))
        if obj is None:
            db.add(LocalAuthority(**row))
        else:
            for k, v in row.items():
                setattr(obj, k, v)
    db.flush()
    return len(LOCAL_AUTHORITIES)


def seed_property_types(db: Session) -> dict[str, PropertyType]:
    result: dict[str, PropertyType] = {}
    for row in PROPERTY_TYPES:
        obj = db.scalar(select(PropertyType).where(PropertyType.code == row["code"]))
        if obj is None:
            obj = PropertyType(**row)
            db.add(obj)
        else:
            for k, v in row.items():
                setattr(obj, k, v)
        result[row["code"]] = obj
    db.flush()
    return result


def seed_classification_rules(db: Session, types: dict[str, PropertyType]) -> int:
    for row in CLASSIFICATION_RULES:
        data = dict(row)
        ptype = types[data.pop("property_type")]
        obj = db.scalar(select(ClassificationRule).where(ClassificationRule.code == data["code"]))
        if obj is None:
            obj = ClassificationRule(
                **data, property_type_id=ptype.id, effective_from=EFFECTIVE_FROM
            )
            db.add(obj)
        else:
            for k, v in data.items():
                setattr(obj, k, v)
            obj.property_type_id = ptype.id
            obj.effective_from = EFFECTIVE_FROM
    db.flush()
    return len(CLASSIFICATION_RULES)


def seed_fee_schedules(db: Session, types: dict[str, PropertyType]) -> int:
    for row in FEE_SCHEDULES:
        data = dict(row)
        ptype = types[data.pop("property_type")]
        obj = db.scalar(
            select(FeeSchedule).where(
                FeeSchedule.property_type_id == ptype.id,
                FeeSchedule.effective_from == EFFECTIVE_FROM,
            )
        )
        if obj is None:
            db.add(FeeSchedule(**data, property_type_id=ptype.id, effective_from=EFFECTIVE_FROM))
        else:
            for k, v in data.items():
                setattr(obj, k, v)
    db.flush()
    return len(FEE_SCHEDULES)


def seed_issuing_agencies(db: Session) -> dict[str, IssuingAgency]:
    result: dict[str, IssuingAgency] = {}
    for row in ISSUING_AGENCIES:
        obj = db.scalar(select(IssuingAgency).where(IssuingAgency.code == row["code"]))
        if obj is None:
            obj = IssuingAgency(**row)
            db.add(obj)
        else:
            for k, v in row.items():
                setattr(obj, k, v)
        result[row["code"]] = obj
    db.flush()
    return result


def seed_document_types(db: Session, agencies: dict[str, IssuingAgency]) -> dict[str, DocumentType]:
    """สร้าง/อัปเดตชนิดเอกสาร แล้วผูก parent ทีหลัง

    ต้องแยกสองรอบ เพราะเอกสารย่อยอ้างถึงฉบับแม่ซึ่งอาจยังไม่มี id ตอนวนรอบแรก
    """
    result: dict[str, DocumentType] = {}
    parents: dict[str, str] = {}

    for row in DOCUMENT_TYPES:
        data = dict(row)
        agency_code = data.pop("issuing_agency", None)
        parent_code = data.pop("parent", None)
        if parent_code:
            parents[data["code"]] = parent_code
        agency_id = agencies[agency_code].id if agency_code else None

        obj = db.scalar(select(DocumentType).where(DocumentType.code == data["code"]))
        if obj is None:
            obj = DocumentType(**data, issuing_agency_id=agency_id)
            db.add(obj)
        else:
            for k, v in data.items():
                setattr(obj, k, v)
            obj.issuing_agency_id = agency_id
        result[data["code"]] = obj
    db.flush()

    for code, parent_code in parents.items():
        result[code].parent_id = result[parent_code].id
    db.flush()
    return result


def seed_document_requirements(
    db: Session, types: dict[str, PropertyType], docs: dict[str, DocumentType]
) -> int:
    for row in DOCUMENT_REQUIREMENTS:
        ptype = types[row["property_type"]]
        dtype = docs[row["document_type"]]
        obj = db.scalar(
            select(DocumentRequirement).where(
                DocumentRequirement.property_type_id == ptype.id,
                DocumentRequirement.document_type_id == dtype.id,
            )
        )
        if obj is None:
            db.add(
                DocumentRequirement(
                    property_type_id=ptype.id,
                    document_type_id=dtype.id,
                    is_mandatory=row["is_mandatory"],
                    display_order=row["display_order"],
                    note=row.get("note"),
                )
            )
        else:
            obj.is_mandatory = row["is_mandatory"]
            obj.display_order = row["display_order"]
            obj.note = row.get("note")
    db.flush()
    return len(DOCUMENT_REQUIREMENTS)


def seed_contact_points(db: Session, agencies: dict[str, IssuingAgency]) -> int:
    """จุดติดต่อของกองช่างครบทั้ง 19 อปท. — ตอบ M4 ว่า "ที่ท้องถิ่นใด"

    สร้างจากรายชื่อ อปท. ในฐานข้อมูล ไม่ใช่รายการที่เขียนซ้ำไว้ในไฟล์ seed
    เพิ่ม อปท. ใหม่แล้วรัน seed ซ้ำ จุดติดต่อจะตามมาเองโดยไม่ต้องแก้อะไร
    """
    cfg = CONTACT_POINT_DEFAULTS
    agency = agencies[cfg["issuing_agency"]]
    count = 0

    for authority in db.scalars(select(LocalAuthority)).all():
        obj = db.scalar(
            select(ContactPoint).where(
                ContactPoint.issuing_agency_id == agency.id,
                ContactPoint.local_authority_id == authority.id,
            )
        )
        values = {
            "office_name": cfg["office_name_template"].format(authority_name=authority.name),
            "address": authority.address,
            "phone": authority.phone,
            # กองช่างอยู่ในสำนักงานของ อปท. จึงใช้หมุดเดียวกันเป็นค่าตั้งต้น
            "map_url": authority.map_url,
            "office_hours": cfg["office_hours"],
            "estimated_days": cfg["estimated_days"],
            "notes": cfg["notes"],
        }
        if obj is None:
            db.add(
                ContactPoint(
                    issuing_agency_id=agency.id,
                    local_authority_id=authority.id,
                    **values,
                )
            )
        else:
            for k, v in values.items():
                setattr(obj, k, v)
        count += 1

    db.flush()
    return count


def seed_demo_users(db: Session) -> int:
    """บัญชีสาธิต 4 บทบาท — hash รหัสผ่านใหม่เฉพาะตอนสร้างครั้งแรก
    เพื่อไม่ให้รันซ้ำแล้ว bcrypt ทำงานใหม่ทุกครั้งโดยไม่จำเป็น
    """
    authorities = {a.code: a for a in db.scalars(select(LocalAuthority)).all()}

    for row in DEMO_USERS:
        data = dict(row)
        auth_code = data.pop("authority_code", None)
        user = db.scalar(select(User).where(User.email == data["email"]))
        if user is None:
            user = User(**data, password_hash=hash_password(DEMO_PASSWORD))
            db.add(user)
            db.flush()
        else:
            for k, v in data.items():
                setattr(user, k, v)

        if auth_code:
            exists = db.scalar(
                select(OfficerAssignment).where(
                    OfficerAssignment.officer_id == user.id,
                    OfficerAssignment.local_authority_id == authorities[auth_code].id,
                )
            )
            if exists is None:
                db.add(
                    OfficerAssignment(
                        officer_id=user.id, local_authority_id=authorities[auth_code].id
                    )
                )
    db.flush()
    return len(DEMO_USERS)


def main() -> None:
    with SessionLocal() as db:
        n_auth = seed_local_authorities(db)
        types = seed_property_types(db)
        n_rules = seed_classification_rules(db, types)
        n_fees = seed_fee_schedules(db, types)
        agencies = seed_issuing_agencies(db)
        docs = seed_document_types(db, agencies)
        n_reqs = seed_document_requirements(db, types, docs)
        n_contacts = seed_contact_points(db, agencies)
        n_users = seed_demo_users(db)
        db.commit()

    print(f"  อปท.              {n_auth} แห่ง")
    print(f"  ประเภทที่พัก       {len(types)} ประเภท")
    print(f"  กฎจำแนกประเภท     {n_rules} กฎ")
    print(f"  อัตราค่าธรรมเนียม  {n_fees} รายการ")
    print(f"  หน่วยงานออกเอกสาร  {len(agencies)} แห่ง")
    print(f"  ชนิดเอกสาร         {len(docs)} รายการ")
    print(f"  ข้อกำหนดเอกสาร     {n_reqs} รายการ")
    print(f"  จุดติดต่อ           {n_contacts} จุด")
    print(f"  บัญชีสาธิต         {n_users} บัญชี (รหัสผ่าน {DEMO_PASSWORD})")


if __name__ == "__main__":
    main()
