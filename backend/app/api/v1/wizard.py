"""M2 — ระบบนำทางแบบถามตอบทีละขั้น (Guided Wizard)

หัวใจของโจทย์: รับคำตอบ -> จำแนกประเภทตาม classification_rule ใน DB
-> ตอบกลับพร้อม "เหตุผลว่าทำไมจึงได้ผลนั้น" + รายการเอกสาร 2 หมวด

ข้อควรระวัง (กรณีทดสอบ T-02): เงื่อนไข "ไม่เข้าข่ายโรงแรม" คือ
ห้องพัก <= 8 ห้อง **และ** ผู้เข้าพัก <= 30 คน ต้องเป็น AND ทั้งสองเงื่อนไข
ที่พัก 8 ห้องแต่รับ 36 คน ต้องตอบว่า "เข้าข่ายต้องขอใบอนุญาต"

endpoint กลุ่มนี้ไม่บังคับให้เข้าสู่ระบบ ตั้งใจให้ผู้ประกอบการลองเช็ก
ได้ทันทีตาม US-01 ("ตอบคำถามไม่กี่ข้อแล้วรู้ว่าต้องขอใบอนุญาตหรือไม่")
และไม่เขียนอะไรลง DB จึงไม่มีขยะค้างจากคนที่แค่มาลอง

เจ้าของงานส่วนนี้: <ใส่ชื่อสมาชิก>
"""

from fastapi import APIRouter, HTTPException, status

from app.api import presenters
from app.api.deps import DbSession
from app.schemas.wizard import ClassifyResult, FeeOut, LocalAuthorityOut, WizardAnswers
from app.services import classification as svc

router = APIRouter()


@router.get(
    "/local-authorities",
    response_model=list[LocalAuthorityOut],
    summary="รายชื่อ อปท. ทั้งหมดสำหรับให้เลือกใน wizard",
)
def list_local_authorities(db: DbSession) -> list[LocalAuthorityOut]:
    return [LocalAuthorityOut.model_validate(a) for a in svc.local_authorities(db)]


@router.post(
    "/classify",
    response_model=ClassifyResult,
    summary="ประเมินว่าที่พักเข้าข่ายประเภทใด พร้อมเหตุผลและรายการเอกสาร",
    responses={
        422: {"description": "ไม่มีกฎใดในระบบรองรับกรณีนี้"},
    },
)
def classify(payload: WizardAnswers, db: DbSession) -> ClassifyResult:
    outcome = svc.classify(db, svc.Answers(payload.rooms, payload.guests, payload.has_restaurant))

    if outcome is None:
        # เกิดได้เมื่อ Super Admin แก้กฎจนมีช่องโหว่ — ต้องบอกให้ผู้ใช้เข้าใจ
        # ไม่ใช่ปล่อย 500 ออกไป (NFR Usability)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=("ระบบยังไม่มีเกณฑ์สำหรับที่พักลักษณะนี้ กรุณาติดต่อเจ้าหน้าที่เพื่อตรวจสอบเป็นรายกรณี"),
        )

    docs = svc.required_documents(
        db, outcome.property_type.id, local_authority_id=payload.local_authority_id
    )

    return ClassifyResult(
        property_type_code=outcome.property_type.code,
        property_type_name=outcome.property_type.name_th,
        requires_license=outcome.property_type.requires_license,
        is_out_of_scope=outcome.property_type.is_out_of_scope,
        reason=outcome.reason,
        outcome_message=outcome.outcome_message,
        matched_rule_code=outcome.matched_rule.code if outcome.matched_rule else None,
        fee=FeeOut(**vars(outcome.fee)) if outcome.fee else None,
        documents=presenters.to_checklist(docs, local_authority_id=payload.local_authority_id),
    )
