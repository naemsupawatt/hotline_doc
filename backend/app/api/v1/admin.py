"""US-09 — Super Admin แก้ไขเงื่อนไขและค่าธรรมเนียมได้โดยไม่ต้องแก้โค้ด

endpoint กลุ่มนี้คือสิ่งที่พิสูจน์ว่าระบบเป็น config-driven จริง
เป็นจุดที่กรรมการน่าจะขอให้สาธิต (เกณฑ์ข้อ 2, 25 คะแนน)

วิธีสาธิตที่เร็วที่สุด:
  1. เปิด /operator/wizard กรอก 8 ห้อง 36 คน -> ได้ "ที่พักแรม ประเภทที่ 1"
  2. มาที่หน้านี้ แก้ max_guests ของ RULE-NOT-HOTEL จาก 30 เป็น 40
  3. กรอกเดิมอีกครั้ง -> ได้ "ไม่เข้าข่ายโรงแรม" โดยไม่มีใครแตะโค้ดเลย

เจ้าของงานส่วนนี้: <ใส่ชื่อสมาชิก>
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import DbSession, require_role
from app.models.classification import PropertyType
from app.models.enums import UserRole
from app.models.license import FeeSchedule
from app.models.user import User
from app.schemas.admin import (
    FeeOut,
    FeeSupersede,
    PreviewRequest,
    PreviewResult,
    RuleOut,
    RuleUpdate,
)
from app.services import admin as admin_svc
from app.services import classification as classify_svc

router = APIRouter()

CurrentAdmin = Annotated[User, Depends(require_role(UserRole.SUPER_ADMIN))]


@router.get(
    "/classification-rules",
    response_model=list[RuleOut],
    summary="เงื่อนไขจำแนกประเภททั้งหมด เรียงตามลำดับการตัดสิน",
)
def list_rules(db: DbSession, current: CurrentAdmin) -> list[RuleOut]:
    return [_rule_out(db, rule) for rule in admin_svc.all_rules(db)]


@router.patch(
    "/classification-rules/{code}",
    response_model=RuleOut,
    summary="แก้เงื่อนไขจำแนกประเภท (US-09)",
    responses={
        404: {"description": "ไม่พบกฎรหัสนี้"},
        422: {"description": "ค่าที่ส่งมาทำให้กฎใช้ไม่ได้"},
    },
)
def update_rule(
    code: str,
    payload: RuleUpdate,
    db: DbSession,
    current: CurrentAdmin,
    request: Request,
) -> RuleOut:
    rule = admin_svc.rule_by_code(db, code)
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบกฎรหัสนี้")

    # ช่องที่ไม่ส่งมา = ไม่แก้  ส่วนช่องใน clear = ตั้งใจล้างให้เป็นค่าว่าง
    changes = {k: v for k, v in payload.model_dump(exclude={"clear"}).items() if v is not None}
    for field in payload.clear:
        changes[field] = None

    applied, error = admin_svc.update_rule(
        db,
        rule=rule,
        changes=changes,
        admin=current,
        ip=request.client.host if request.client else None,
    )
    if error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    db.commit()
    db.refresh(rule)
    return _rule_out(db, rule)


@router.post(
    "/classification-rules/preview",
    response_model=PreviewResult,
    summary="ลองจำแนกด้วยกฎปัจจุบัน โดยไม่บันทึกอะไร",
)
def preview_rules(payload: PreviewRequest, db: DbSession, current: CurrentAdmin) -> PreviewResult:
    """ให้ผู้ดูแลระบบเห็นผลทันทีหลังแก้กฎ ก่อนที่คำขอจริงจะเข้ามา"""
    return PreviewResult(
        **admin_svc.preview(db, payload.rooms, payload.guests, payload.has_restaurant)
    )


@router.get(
    "/fee-schedules",
    response_model=list[FeeOut],
    summary="อัตราค่าธรรมเนียมทั้งหมด รวมอัตราที่ปิดไปแล้ว",
)
def list_fees(db: DbSession, current: CurrentAdmin) -> list[FeeOut]:
    types = {t.id: t for t in db.scalars(select(PropertyType)).all()}
    current_ids = {
        row.id for type_id in types if (row := classify_svc.fee_row(db, type_id)) is not None
    }

    return [
        FeeOut(
            id=fee.id,
            property_type_code=types[fee.property_type_id].code,
            property_type_name=types[fee.property_type_id].name_th,
            amount=float(fee.amount),
            currency=fee.currency,
            validity_years=fee.validity_years,
            effective_from=fee.effective_from,
            effective_to=fee.effective_to,
            is_current=fee.id in current_ids,
            note=fee.note,
        )
        for fee in admin_svc.active_fees(db)
    ]


@router.post(
    "/fee-schedules/{fee_id}/supersede",
    response_model=list[FeeOut],
    status_code=status.HTTP_201_CREATED,
    summary="เปลี่ยนอัตราค่าธรรมเนียม (เพิ่มแถวใหม่ ไม่ทับของเดิม)",
    responses={
        404: {"description": "ไม่พบอัตรานี้"},
        422: {"description": "ค่าที่ส่งมาไม่ถูกต้อง"},
    },
)
def supersede_fee(
    fee_id: int,
    payload: FeeSupersede,
    db: DbSession,
    current: CurrentAdmin,
    request: Request,
) -> list[FeeOut]:
    """อัตราเดิมไม่ถูกลบ ใบอนุญาตที่ออกไปแล้วจึงยังชี้กลับมาหาได้เสมอ"""
    fee = db.get(FeeSchedule, fee_id)
    if fee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบอัตรานี้")

    created, error = admin_svc.supersede_fee(
        db,
        current=fee,
        amount=payload.amount,
        validity_years=payload.validity_years,
        effective_from=payload.effective_from,
        note=payload.note,
        admin=current,
        ip=request.client.host if request.client else None,
    )
    if created is None:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    db.commit()
    return list_fees(db, current)


def _rule_out(db: DbSession, rule) -> RuleOut:
    return RuleOut(
        code=rule.code,
        property_type_code=rule.property_type.code,
        property_type_name=rule.property_type.name_th,
        priority=rule.priority,
        min_rooms=rule.min_rooms,
        max_rooms=rule.max_rooms,
        min_guests=rule.min_guests,
        max_guests=rule.max_guests,
        requires_restaurant=rule.requires_restaurant,
        reason_template=rule.reason_template,
        outcome_message=rule.outcome_message,
        is_active=rule.is_active,
        effective_from=rule.effective_from,
        applications_classified=admin_svc.counts_using_rule(db, rule.property_type_id),
    )


# TODO US-09: GET/PUT /document-types     แก้รายการเอกสารและหมวด
# TODO US-09: GET/PUT /local-authorities  แก้จุดติดต่อของแต่ละท้องถิ่น
# TODO M1:    GET/PUT /users              จัดการบัญชีและสิทธิ์
