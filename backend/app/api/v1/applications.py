"""M6/M7 — เปิดคำขอ ดูรายการคำขอของตัวเอง และติดตามสถานะ

เส้นทางนี้ต้องเข้าสู่ระบบ ต่างจาก /wizard ที่เปิดให้ลองประเมินได้เลย
เพราะคำขอต้องผูกกับผู้ยื่นที่ระบุตัวตนได้ (NFR Audit Trail)

การเข้าถึง: ผู้ยื่นเห็นได้เฉพาะคำขอของตัวเอง — เป็นฝาแฝดของ T-09
ที่ห้ามเจ้าหน้าที่เปิดคำขอข้ามเขต ทั้งสองกรณีต้องบันทึกความพยายามลง AuditLog

เจ้าของงานส่วนนี้: <ใส่ชื่อสมาชิก>
"""

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api import presenters
from app.api.deps import CurrentOperator, DbSession
from app.models.application import Application
from app.models.audit import AuditLog
from app.models.authority import LocalAuthority
from app.models.classification import ApplicationClassification
from app.models.property import Operator, Property
from app.models.user import User
from app.schemas.application import (
    AddressOut,
    ApplicationOut,
    ApplicationSummaryOut,
    MissingDocumentOut,
    PropertyOut,
    StartApplicationRequest,
)
from app.schemas.license import LicenseOut
from app.schemas.wizard import FeeOut
from app.services import application as app_svc
from app.services import classification as classify_svc
from app.services import document as doc_svc
from app.services import license as license_svc

router = APIRouter()


@router.post(
    "",
    response_model=ApplicationOut,
    status_code=status.HTTP_201_CREATED,
    summary="เปิดคำขอใหม่จากผลประเมินในระบบนำทาง",
    responses={
        403: {"description": "บัญชีนี้ไม่ใช่ผู้ประกอบการ"},
        422: {"description": "ข้อมูลไม่ครบ หรือกรณีนี้อยู่นอกขอบเขตของระบบ"},
    },
)
def start_application(
    payload: StartApplicationRequest,
    db: DbSession,
    current: CurrentOperator,
    request: Request,
) -> ApplicationOut:
    authority = db.get(LocalAuthority, payload.local_authority_id)
    if authority is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ไม่พบองค์กรปกครองส่วนท้องถิ่นที่เลือก กรุณาเลือกใหม่อีกครั้ง",
        )

    created, error = app_svc.start(
        db,
        user=current,
        answers=classify_svc.Answers(payload.rooms, payload.guests, payload.has_restaurant),
        local_authority_id=payload.local_authority_id,
        details=app_svc.PropertyDetails(
            name=payload.property_name,
            address=app_svc.Address(
                address_no=payload.address.address_no,
                moo=payload.address.moo,
                soi=payload.address.soi,
                road=payload.address.road,
                sub_district=payload.address.sub_district,
                district=payload.address.district,
                postal_code=payload.address.postal_code,
            ),
            accommodation_kind=payload.accommodation_kind,
            accommodation_kind_other=payload.accommodation_kind_other,
            latitude=payload.latitude,
            longitude=payload.longitude,
        ),
        ip=request.client.host if request.client else None,
    )

    if created is None:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    db.commit()
    db.refresh(created.application)
    return _detail(db, created.application)


@router.get(
    "",
    response_model=list[ApplicationSummaryOut],
    summary="รายการคำขอของผู้ยื่นที่เข้าสู่ระบบอยู่",
)
def my_applications(db: DbSession, current: CurrentOperator) -> list[ApplicationSummaryOut]:
    rows: list[ApplicationSummaryOut] = []
    for application in app_svc.owned_by(db, current):
        prop = db.get(Property, application.property_id)
        snapshot = _classification(db, application)
        rows.append(
            ApplicationSummaryOut(
                application_no=application.application_no,
                status=application.status,
                days_waiting=app_svc.days_waiting(application),
                property_name=prop.name if prop else "-",
                property_type_name=(snapshot.property_type.name_th if snapshot else "ยังไม่ได้จำแนก"),
                created_at=application.created_at,
            )
        )
    return rows


@router.get(
    "/{application_no}",
    response_model=ApplicationOut,
    summary="รายละเอียดคำขอ พร้อมรายการเอกสารที่ต้องใช้",
    responses={404: {"description": "ไม่พบคำขอ หรือคำขอนี้ไม่ใช่ของผู้ใช้รายนี้"}},
)
def application_detail(
    application_no: str, db: DbSession, current: CurrentOperator, request: Request
) -> ApplicationOut:
    return _detail(db, _load_owned(db, application_no, current, request))


@router.post(
    "/{application_no}/submit",
    response_model=ApplicationOut,
    summary="ยื่นคำขอเข้าสู่การพิจารณา",
    responses={
        404: {"description": "ไม่พบคำขอ หรือคำขอนี้ไม่ใช่ของผู้ใช้รายนี้"},
        422: {"description": "เอกสารบังคับยังไม่ครบ — ระบุรายการที่ขาดใน detail"},
    },
)
def submit_application(
    application_no: str, db: DbSession, current: CurrentOperator, request: Request
) -> ApplicationOut:
    application = _load_owned(db, application_no, current, request)

    ok, error, missing = app_svc.submit(
        db,
        application=application,
        user=current,
        ip=request.client.host if request.client else None,
    )

    if not ok:
        db.rollback()
        # T-06: ต้องบอกให้ชัดว่าขาดฉบับใดบ้าง ไม่ใช่แค่ "เอกสารไม่ครบ"
        listed = ", ".join(f"{m.code} {m.name_th}" for m in missing)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{error} ขาด {len(missing)} ฉบับ: {listed}" if missing else error,
        )

    db.commit()
    db.refresh(application)
    return _detail(db, application)


@router.get(
    "/{application_no}/license",
    response_model=LicenseOut,
    summary="ข้อมูลใบอนุญาตหรือหนังสือรับรอง สำหรับพิมพ์ (M10)",
    responses={404: {"description": "ยังไม่ได้ออกเอกสารสำหรับคำขอนี้"}},
)
def application_license(
    application_no: str, db: DbSession, current: CurrentOperator, request: Request
) -> LicenseOut:
    application = _load_owned(db, application_no, current, request)

    row = license_svc.existing(db, application.id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="คำขอนี้ยังไม่ได้ออกเอกสาร กรุณารอเจ้าหน้าที่ดำเนินการ",
        )

    prop = db.get(Property, application.property_id)
    authority = db.get(LocalAuthority, application.local_authority_id)
    holder = db.scalar(
        select(User)
        .join(Operator, Operator.user_id == User.id)
        .where(Operator.id == application.operator_id)
    )
    issuer = db.get(User, row.issued_by_id)

    return presenters.to_license_out(db, row, application, prop, authority, holder, issuer)


# ---------------------------------------------------------------- ตัวช่วยภายใน


def _load_owned(db: DbSession, application_no: str, current, request: Request) -> Application:
    """คำขอของผู้ใช้รายนี้เท่านั้น

    ตอบ 404 ไม่ใช่ 403 เพราะ 403 เท่ากับยืนยันว่าเลขที่คำขอนี้มีอยู่จริง
    และบันทึกความพยายามลง AuditLog — ฝาแฝดของ T-09 ฝั่งผู้ยื่น
    """
    application = app_svc.by_number(db, application_no)

    if application is not None and not app_svc.is_owner(db, application, current):
        db.add(
            AuditLog(
                actor_id=current.id,
                action="application.access_denied",
                entity_type="application",
                entity_id=application.id,
                outcome="denied",
                detail=f"พยายามเปิดคำขอ {application_no} ซึ่งไม่ใช่ของตน",
                ip_address=request.client.host if request.client else None,
            )
        )
        db.commit()
        application = None

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบคำขอหมายเลขนี้ในบัญชีของคุณ กรุณาตรวจสอบเลขที่คำขออีกครั้ง",
        )
    return application


def _classification(db: DbSession, application: Application) -> ApplicationClassification | None:
    """ผลจำแนกที่บันทึกไว้ตอนเปิดคำขอ (หนึ่งคำขอมีได้ใบเดียว)"""
    return db.scalar(
        select(ApplicationClassification).where(
            ApplicationClassification.application_id == application.id
        )
    )


def _detail(db: DbSession, application: Application) -> ApplicationOut:
    snapshot = _classification(db, application)
    if snapshot is None:  # pragma: no cover - ทุกคำขอถูกสร้างพร้อม snapshot เสมอ
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ข้อมูลคำขอไม่สมบูรณ์ กรุณาติดต่อเจ้าหน้าที่",
        )

    ptype = snapshot.property_type
    prop = db.get(Property, application.property_id)
    authority = db.get(LocalAuthority, application.local_authority_id)

    docs = classify_svc.required_documents(
        db, ptype.id, local_authority_id=application.local_authority_id
    )
    fee = classify_svc.current_fee(db, ptype.id) if ptype.requires_license else None

    files = doc_svc.current_files(db, application.id)
    missing = doc_svc.missing_mandatory(db, application, ptype.id)

    return ApplicationOut(
        application_no=application.application_no,
        status=application.status,
        days_waiting=app_svc.days_waiting(application),
        created_at=application.created_at,
        submitted_at=application.submitted_at,
        property_type_code=ptype.code,
        property_type_name=ptype.name_th,
        requires_license=ptype.requires_license,
        # เหตุผลมาจาก snapshot ตอนจำแนก ไม่คำนวณใหม่
        # ถ้ากฎถูกแก้ทีหลัง คำขอใบนี้ต้องยังอธิบายได้ว่าตอนนั้นตัดสินด้วยอะไร
        reason=snapshot.reason_text,
        matched_rule_code=snapshot.matched_rule.code if snapshot.matched_rule else None,
        fee=FeeOut(**vars(fee)) if fee else None,
        property=PropertyOut(
            name=prop.name,
            address=AddressOut(
                address_no=prop.address_no,
                moo=prop.moo,
                soi=prop.soi,
                road=prop.road,
                sub_district=prop.sub_district,
                district=prop.district,
                postal_code=prop.postal_code,
                province=prop.province,
                full_address=prop.full_address,
            ),
            room_count=prop.room_count,
            max_guests=prop.max_guests,
            has_restaurant=prop.has_restaurant,
            accommodation_kind=prop.accommodation_kind,
            accommodation_kind_other=prop.accommodation_kind_other,
            local_authority_name=authority.name if authority else "-",
        ),
        documents=presenters.to_checklist(
            docs, local_authority_id=application.local_authority_id, files=files
        ),
        license_no=(
            issued.license_no if (issued := license_svc.existing(db, application.id)) else None
        ),
        can_submit=not missing and app_svc.is_editable(application),
        missing_documents=[MissingDocumentOut(code=m.code, name_th=m.name_th) for m in missing],
    )
