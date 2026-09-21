"""M6/M7 — เปิดคำขอ ดูรายการคำขอของตัวเอง และติดตามสถานะ

เส้นทางนี้ต้องเข้าสู่ระบบ ต่างจาก /wizard ที่เปิดให้ลองประเมินได้เลย
เพราะคำขอต้องผูกกับผู้ยื่นที่ระบุตัวตนได้ (NFR Audit Trail)

การเข้าถึง: ผู้ยื่นเห็นได้เฉพาะคำขอของตัวเอง — เป็นฝาแฝดของ T-09
ที่ห้ามเจ้าหน้าที่เปิดคำขอข้ามเขต ทั้งสองกรณีต้องบันทึกความพยายามลง AuditLog

เจ้าของงานส่วนนี้: <ใส่ชื่อสมาชิก>
"""

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import Response
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
from app.schemas.system_form import (
    ApplicantIn,
    ApplicantOut,
    SystemFormOut,
)
from app.schemas.wizard import FeeOut
from app.services import application as app_svc
from app.services import classification as classify_svc
from app.services import document as doc_svc
from app.services import license as license_svc
from app.services import storage
from app.services import system_form as form_svc

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
        listed = ", ".join(
            f"{m.code} {m.name_th}" + (" (ยังไม่ได้ลงลายมือชื่อ)" if m.needs_signature else "")
            for m in missing
        )
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

    return presenters.to_license_out_for(db, application, row)


@router.get(
    "/{application_no}/license/signature",
    summary="รูปลายมือชื่อผู้ลงนามบนเอกสารที่ออกให้ สำหรับแสดงบนหน้าพิมพ์ (M10)",
    responses={404: {"description": "ยังไม่ได้ออกเอกสาร หรือเอกสารใบนี้ไม่มีลายมือชื่อเก็บไว้"}},
)
def license_signature(
    application_no: str, db: DbSession, current: CurrentOperator, request: Request,
    download_url: bool = False,
) -> Response:
    """แยกเป็น endpoint ต่างหากแทนการฝัง base64 มากับ LicenseOut

    ถ้าฝังมาด้วย ทุกครั้งที่เปิดหน้าใบอนุญาตจะต้องโหลดรูปไปด้วยเสมอแม้ยังไม่ได้ใช้
    และ payload ของ JSON จะบวมขึ้นหลายเท่าโดยไม่จำเป็น
    """
    application = _load_owned(db, application_no, current, request)

    row = license_svc.existing(db, application.id)
    if row is None or not row.issuer_signature_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="เอกสารใบนี้ไม่มีลายมือชื่อผู้ลงนามเก็บไว้ในระบบ",
        )

    return storage.file_response(
        row.issuer_signature_path, "image/png", f"{row.license_no}.png",
        download_url=download_url,
    )


@router.get(
    "/{application_no}/forms/{code}",
    response_model=SystemFormOut,
    summary="แบบฟอร์มที่ระบบกรอกให้ (A01 หนังสือแจ้งฯ / A06 ร.ร.1) สำหรับพิมพ์และลงลายมือชื่อ",
    responses={
        404: {"description": "ไม่พบคำขอ หรือที่พักประเภทนี้ไม่ได้ใช้แบบฟอร์มรหัสนี้"},
    },
)
def application_form(
    application_no: str, code: str, db: DbSession, current: CurrentOperator, request: Request
) -> SystemFormOut:
    """เนื้อหาของแบบฟอร์มที่ระบบกรอกให้ พร้อมลายมือชื่อที่ผู้ยื่นลงไว้

    ตัวกระดาษถูกจัดหน้าและพิมพ์ที่ฝั่งหน้าเว็บ (เหตุผลอยู่ใน services/system_form.py)
    endpoint นี้จึงส่งเฉพาะ "ข้อความที่ต้องไปอยู่ในช่องไหน" ไม่ได้ส่งไฟล์ PDF
    """
    application = _load_owned(db, application_no, current, request)
    snapshot = _require_classification(db, application)

    form = form_svc.build(db, application, snapshot.property_type_id, code.upper())
    if form is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"คำขอนี้จำแนกเป็น{snapshot.property_type.name_th} "
                f"จึงไม่ได้ใช้แบบฟอร์มรหัส {code.upper()} "
                "ที่พักแต่ละประเภทใช้แบบฟอร์มคนละฉบับ"
            ),
        )

    return presenters.to_system_form_out(
        db, application, snapshot, form, can_sign=app_svc.is_editable(application)
    )


@router.patch(
    "/{application_no}/applicant",
    response_model=ApplicantOut,
    summary="แก้ชื่อผู้ยื่นที่จะปรากฏบนแบบฟอร์ม (บุคคลธรรมดา / นิติบุคคล)",
    responses={
        404: {"description": "ไม่พบคำขอ หรือคำขอนี้ไม่ใช่ของผู้ใช้รายนี้"},
        409: {"description": "คำขอถูกยื่นไปแล้ว แก้ไขไม่ได้"},
        422: {"description": "ข้อมูลไม่ครบ เช่น เลือกนิติบุคคลแต่ไม่ได้ใส่เลขทะเบียน"},
    },
)
def update_applicant(
    application_no: str,
    payload: ApplicantIn,
    db: DbSession,
    current: CurrentOperator,
    request: Request,
) -> ApplicantOut:
    """ชื่อบนแบบฟอร์มอาจไม่ใช่ชื่อเจ้าของบัญชี

    ตอนสมัคร ระบบตั้งชื่อผู้ประกอบการให้เท่ากับชื่อ-นามสกุลของผู้สมัครไปก่อน
    แต่แบบ ร.ร.1 มีช่องให้ระบุว่ายื่นในนามบุคคลธรรมดาหรือนิติบุคคล
    ผู้ยื่นจึงต้องแก้ตรงนี้ได้เอง ไม่ใช่ไปแก้ในฐานข้อมูลให้

    แก้ที่ตาราง operator ซึ่งใช้ร่วมกับคำขอใบอื่นของคนเดียวกัน ตั้งใจให้เป็นแบบนี้
    เพราะเป็น "ตัวตนของผู้ประกอบการ" ไม่ใช่ข้อมูลเฉพาะคำขอใบใดใบหนึ่ง
    """
    application = _load_owned(db, application_no, current, request)

    if not app_svc.is_editable(application):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="คำขอนี้ยื่นไปแล้ว จึงแก้ชื่อผู้ยื่นไม่ได้ หากต้องแก้ กรุณาติดต่อเจ้าหน้าที่",
        )

    reg_no = _clean_juristic_no(payload)

    operator = db.get(Operator, application.operator_id)
    operator.display_name = payload.display_name.strip()
    operator.is_juristic = payload.is_juristic
    operator.juristic_reg_no = reg_no

    db.add(
        AuditLog(
            actor_id=current.id,
            action="operator.update_profile",
            entity_type="operator",
            entity_id=operator.id,
            outcome="success",
            detail=f"แก้ชื่อผู้ยื่นบนแบบฟอร์มของคำขอ {application.application_no}",
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    db.refresh(operator)

    user = db.get(User, operator.user_id)
    return ApplicantOut(
        display_name=operator.display_name,
        is_juristic=operator.is_juristic,
        juristic_reg_no=operator.juristic_reg_no,
        national_id_masked=user.national_id_masked,
        phone=operator.contact_phone or user.phone,
        email=operator.contact_email or user.email,
    )


# ---------------------------------------------------------------- ตัวช่วยภายใน


def _require_classification(db: DbSession, application: Application) -> ApplicationClassification:
    snapshot = _classification(db, application)
    if snapshot is None:  # pragma: no cover - ทุกคำขอถูกสร้างพร้อม snapshot เสมอ
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ข้อมูลคำขอไม่สมบูรณ์ กรุณาติดต่อเจ้าหน้าที่",
        )
    return snapshot


def _clean_juristic_no(payload: ApplicantIn) -> str | None:
    """นิติบุคคลต้องมีเลขทะเบียน 13 หลัก — เก็บเป็นตัวเลขล้วนเหมือนเบอร์โทร

    เก็บตัวเลขล้วนด้วยเหตุผลเดียวกับ core/phone.py: ถ้าเก็บตามที่ผู้ใช้พิมพ์
    เลขเดียวกันที่พิมพ์คนละแบบจะกลายเป็นคนละเลขทันทีเมื่อต้องค้นหรือเทียบ
    """
    if not payload.is_juristic:
        return None

    digits = "".join(ch for ch in (payload.juristic_reg_no or "") if ch.isdigit())
    if len(digits) != 13:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="เลขทะเบียนนิติบุคคลต้องเป็นตัวเลข 13 หลัก",
        )
    return digits


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
    snapshot = _require_classification(db, application)

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
        decision_reason=application.decision_reason,
        license_no=(
            issued.license_no if (issued := license_svc.existing(db, application.id)) else None
        ),
        can_submit=not missing and app_svc.is_editable(application),
        missing_documents=[
            MissingDocumentOut(code=m.code, name_th=m.name_th, needs_signature=m.needs_signature)
            for m in missing
        ],
    )
