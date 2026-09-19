"""รัน seed ข้อมูลตั้งต้นลงฐานข้อมูล

    cd backend && uv run python -m app.seeds.run

เขียนแบบ idempotent (upsert ตาม code) — รันซ้ำได้ไม่พัง และไม่สร้างข้อมูลซ้ำ
สำคัญตอนแข่ง เพราะจะได้รันซ้ำหลัง migrate ใหม่โดยไม่ต้อง drop ฐานข้อมูล
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.authority import LocalAuthority
from app.models.classification import ClassificationRule, PropertyType
from app.models.license import FeeSchedule
from app.seeds.classification import (
    CLASSIFICATION_RULES,
    EFFECTIVE_FROM,
    FEE_SCHEDULES,
    PROPERTY_TYPES,
)
from app.seeds.local_authorities import LOCAL_AUTHORITIES


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


def main() -> None:
    with SessionLocal() as db:
        n_auth = seed_local_authorities(db)
        types = seed_property_types(db)
        n_rules = seed_classification_rules(db, types)
        n_fees = seed_fee_schedules(db, types)
        db.commit()

    print(f"  อปท.              {n_auth} แห่ง")
    print(f"  ประเภทที่พัก       {len(types)} ประเภท")
    print(f"  กฎจำแนกประเภท     {n_rules} กฎ")
    print(f"  อัตราค่าธรรมเนียม  {n_fees} รายการ")


if __name__ == "__main__":
    main()
