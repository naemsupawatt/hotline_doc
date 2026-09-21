"""M8, M9 — หน้าทำงานเจ้าหน้าที่ท้องถิ่น

ข้อบังคับด้านสิทธิ์ (T-09): เจ้าหน้าที่เห็นและเปิดได้เฉพาะคำขอใน อปท.
ที่ตนสังกัดเท่านั้น หากพยายามเปิดของท้องถิ่นอื่น ต้องปฏิเสธ
**และบันทึกความพยายามนั้นลง AuditLog ด้วย**

ที่นี่ตอบ 403 ไม่ใช่ 404 ต่างจากฝั่งผู้ยื่น เพราะเจ้าหน้าที่เป็นผู้ใช้ภายใน
ที่รู้อยู่แล้วว่าคำขอของเขตอื่นมีอยู่จริง การบอกว่า "ไม่มีสิทธิ์" จึงตรงกับ
ความจริงและช่วยให้เขารู้ว่าต้องส่งเรื่องให้เขตที่ถูกต้อง

เจ้าของงานส่วนนี้: <ใส่ชื่อสมาชิก>
"""

from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy import select

from app.api import presenters
from app.api.deps import DbSession, require_role
from app.models.application import Application
from app.models.authority import LocalAuthority
from app.models.document import DocumentFile
from app.models.enums import ApplicationStatus, UserRole
from app.models.property import Property
from app.models.user import User
from app.schemas.application import AddressOut, PropertyOut
from app.schemas.license import LicenseOut
from app.schemas.officer import (
    DecisionRequest,
    OfficerApplicationOut,
    QueueItemOut,
    ReviewDocumentRequest,
)
from app.schemas.system_form import SystemFormOut
from app.schemas.wizard import FeeOut
from app.services import application as app_svc
from app.services import classification as classify_svc
from app.services import document as doc_svc
from app.services import license as license_svc
from app.services import notification as notify_svc
from app.services import officer as officer_svc
from app.services import storage
from app.services import system_form as form_svc

router = APIRouter()

CurrentOfficer = Annotated[User, Depends(require_role(UserRole.OFFICER))]


@router.get(
    "/queue",
    response_model=list[QueueItemOut],
    summary="คิวคำขอในเขตของตน",
    responses={403: {"description": "บัญชีนี้ไม่ใช่เจ้าหน้าที่ท้องถิ่น"}},
)
def queue(
    db: DbSession,
    current: CurrentOfficer,
    scope: Literal["open", "revision", "closed", "all"] = "open",
) -> list[QueueItemOut]:
    """แบ่งคิวตามว่า "ลูกบอลอยู่ในมือใคร"

    open     คำขอที่รอเจ้าหน้าที่ลงมือ — **รวมที่อนุมัติแล้วแต่ยังไม่ออกเอกสาร**
             ถ้าไม่รวม คำขอจะหายจากคิวทันทีที่กดอนุมัติ แล้วกดออกเอกสารไม่ได้อีก
    revision รอผู้ยื่นส่งเอกสารกลับมา เจ้าหน้าที่ทำอะไรไม่ได้จนกว่าจะได้รับ
    closed   ออกเอกสารแล้วหรือไม่อนุมัติ
    all      ทั้งหมดยกเว้นร่างที่ผู้ยื่นยังไม่ได้ส่ง
    """
    rows = officer_svc.queue(db, current, scope)
    authorities = {a.id: a.name for a in db.scalars(select(LocalAuthority)).all()}

    return [
        QueueItemOut(
            application_no=row.application.application_no,
            status=row.application.status,
            days_waiting=row.days_waiting,
            property_name=row.property_obj.name if row.property_obj else "-",
            property_type_name=(
                row.classification.property_type.name_th if row.classification else "-"
            ),
            local_authority_name=authorities.get(row.application.local_authority_id, "-"),
            submitted_at=row.application.submitted_at,
        )
        for row in rows
    ]


@router.get(
    "/applications/{application_no}",
    response_model=OfficerApplicationOut,
    summary="รายละเอียดคำขอ พร้อมเอกสารทุกฉบับ",
    responses={403: {"description": "คำขอนี้อยู่นอกเขตที่รับผิดชอบ (T-09)"}},
)
def application_detail(
    application_no: str, db: DbSession, current: CurrentOfficer, request: Request
) -> OfficerApplicationOut:
    return _detail(db, _load_in_scope(db, application_no, current, request))


@router.post(
    "/applications/{application_no}/documents/{file_id}/review",
    response_model=OfficerApplicationOut,
    summary="บันทึกผลตรวจเอกสารหนึ่งฉบับ",
    responses={
        403: {"description": "คำขอนี้อยู่นอกเขตที่รับผิดชอบ (T-09)"},
        422: {"description": "ผลตรวจไม่ถูกต้อง หรือขาดเหตุผลที่บังคับ"},
    },
)
def review_document(
    application_no: str,
    file_id: int,
    payload: ReviewDocumentRequest,
    db: DbSession,
    current: CurrentOfficer,
    request: Request,
) -> OfficerApplicationOut:
    application = _load_in_scope(db, application_no, current, request)

    file = db.get(DocumentFile, file_id)
    if file is None or file.application_id != application.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบเอกสารฉบับนี้ในคำขอนี้")

    ok, error = officer_svc.review_document(
        db,
        application=application,
        file=file,
        officer=current,
        decision=payload.decision,
        comment=payload.comment,
        ip=request.client.host if request.client else None,
    )
    if not ok:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    db.commit()
    db.refresh(application)
    return _detail(db, application)


@router.post(
    "/applications/{application_no}/decide",
    response_model=OfficerApplicationOut,
    summary="สรุปผลคำขอ: อนุมัติ / ไม่อนุมัติ / ขอให้แก้ไข",
    responses={
        403: {"description": "คำขอนี้อยู่นอกเขตที่รับผิดชอบ (T-09)"},
        422: {"description": "ยังอนุมัติไม่ได้ หรือขาดเหตุผลที่บังคับ"},
    },
)
def decide(
    application_no: str,
    payload: DecisionRequest,
    db: DbSession,
    current: CurrentOfficer,
    request: Request,
    background: BackgroundTasks,
) -> OfficerApplicationOut:
    application = _load_in_scope(db, application_no, current, request)

    ok, error = officer_svc.decide(
        db,
        application=application,
        officer=current,
        decision=payload.decision,
        reason=payload.reason,
        ip=request.client.host if request.client else None,
    )
    if not ok:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    db.commit()
    db.refresh(application)

    # แจ้งผู้ยื่นหลัง commit และนอก request เสมอ เมลช้าหรือล่มต้องไม่ทำให้
    # ผลที่บันทึกไปแล้วล้มเหลวตาม (ดู services/notification.py)
    background.add_task(notify_svc.notify_status_change, application.id, current.id)

    return _detail(db, application)


@router.post(
    "/applications/{application_no}/issue-license",
    response_model=OfficerApplicationOut,
    summary="ออกใบอนุญาตหรือหนังสือรับรองการแจ้ง (M10)",
    responses={
        403: {"description": "คำขอนี้อยู่นอกเขตที่รับผิดชอบ (T-09)"},
        422: {"description": "คำขอยังไม่อนุมัติ ออกเอกสารไปแล้ว หรือไม่ได้แนบลายมือชื่อผู้ลงนาม"},
    },
)
async def issue_license(
    application_no: str,
    db: DbSession,
    current: CurrentOfficer,
    request: Request,
    signature: Annotated[UploadFile, File(description="รูปลายมือชื่อผู้ลงนาม (PNG) ที่เจ้าหน้าที่เซ็นบนหน้าจอ")],
    background: BackgroundTasks,
) -> OfficerApplicationOut:
    """แยกจากขั้นอนุมัติโดยตั้งใจ

    การอนุมัติกับการออกเอกสารเป็นคนละการกระทำในทางปฏิบัติ และแยกไว้ทำให้
    เส้นเวลาของคำขออ่านออกว่าอนุมัติเมื่อใด ออกเอกสารเมื่อใด

    ลายมือชื่อผู้ลงนามบังคับ เพราะเอกสารที่ไม่มีใครลงนามคือเอกสารที่ใช้ไม่ได้
    กติกาเดียวกับที่ผู้ยื่นต้องลงลายมือชื่อในแบบฟอร์มก่อนยื่น (M6)
    """
    application = _load_in_scope(db, application_no, current, request)
    snapshot = app_svc.classification_of(db, application)

    png = await signature.read()
    if signature.content_type != "image/png" or not png:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="กรุณาลงลายมือชื่อผู้ลงนามก่อนออกเอกสาร",
        )

    issued, error = license_svc.issue(
        db,
        application=application,
        officer=current,
        property_type=snapshot.property_type,
        signature_png=png,
        ip=request.client.host if request.client else None,
    )
    if issued is None:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error)

    db.commit()
    db.refresh(application)

    # แจ้งผู้ยื่นหลัง commit และนอก request เสมอ เมลช้าหรือล่มต้องไม่ทำให้
    # ผลที่บันทึกไปแล้วล้มเหลวตาม (ดู services/notification.py)
    background.add_task(notify_svc.notify_status_change, application.id, current.id)

    return _detail(db, application)


@router.get(
    "/applications/{application_no}/documents/file/{file_id}",
    summary="เปิดไฟล์เอกสารเพื่อตรวจ",
    responses={
        403: {"description": "คำขอนี้อยู่นอกเขตที่รับผิดชอบ (T-09)"},
        404: {"description": "ไม่พบไฟล์"},
    },
)
def open_document(
    application_no: str,
    file_id: int,
    db: DbSession,
    current: CurrentOfficer,
    request: Request,
    download_url: bool = False,
) -> Response:
    """เจ้าหน้าที่ต้องเปิดไฟล์ได้ ไม่งั้นตรวจเอกสารไม่ได้จริง

    ใช้ guard ตัวเดียวกับหน้าอื่น ไฟล์ของคำขอนอกเขตจึงเปิดไม่ได้เช่นกัน
    """
    application = _load_in_scope(db, application_no, current, request)

    row = db.get(DocumentFile, file_id)
    if row is None or row.application_id != application.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบไฟล์ที่ต้องการ")

    return storage.file_response(
        row.stored_path, row.mime_type, row.original_name, download_url=download_url
    )


@router.get(
    "/applications/{application_no}/forms/{code}",
    response_model=SystemFormOut,
    summary="เปิดดูแบบฟอร์มที่ระบบกรอกให้ พร้อมลายมือชื่อที่ผู้ยื่นลงไว้ (อ่านอย่างเดียว)",
    responses={
        403: {"description": "คำขอนี้อยู่นอกเขตที่รับผิดชอบ (T-09)"},
        404: {"description": "ไม่พบคำขอ หรือที่พักประเภทนี้ไม่ได้ใช้แบบฟอร์มรหัสนี้"},
    },
)
def application_form(
    application_no: str, code: str, db: DbSession, current: CurrentOfficer, request: Request
) -> SystemFormOut:
    """เจ้าหน้าที่ต้องเห็น "หนังสือที่ลงลายมือชื่อแล้ว" ไม่ใช่เห็นแต่ไฟล์รูปลายมือชื่อ

    ไฟล์แนบของแบบฟอร์มที่ระบบกรอกให้คือรูปลายเซ็นเพียงอย่างเดียว เปิดดูแล้ว
    บอกไม่ได้เลยว่าเซ็นกำกับข้อความอะไรไว้ ทั้งที่คนตรวจต้องตัดสินว่าผ่านหรือไม่ผ่าน
    endpoint นี้จึงคืนกระดาษฉบับเดียวกับที่ผู้ยื่นเห็น ผ่าน presenter ตัวเดียวกัน

    อ่านอย่างเดียวเสมอ (can_sign=False) ลายมือชื่อเป็นของผู้ยื่น เจ้าหน้าที่เซ็นแทนไม่ได้
    guard เป็นตัวเดียวกับหน้าอื่น คำขอนอกเขตจึงเปิดไม่ได้และถูกบันทึกไว้ (T-09)
    """
    application = _load_in_scope(db, application_no, current, request)
    snapshot = app_svc.classification_of(db, application)

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

    return presenters.to_system_form_out(db, application, snapshot, form, can_sign=False)


@router.get(
    "/applications/{application_no}/license",
    response_model=LicenseOut,
    summary="เอกสารที่ออกให้คำขอนี้ สำหรับเจ้าหน้าที่เปิดดูและพิมพ์ (M10)",
    responses={
        403: {"description": "คำขอนี้อยู่นอกเขตที่รับผิดชอบ (T-09)"},
        404: {"description": "ยังไม่ได้ออกเอกสารสำหรับคำขอนี้"},
    },
)
def application_license(
    application_no: str, db: DbSession, current: CurrentOfficer, request: Request
) -> LicenseOut:
    """เจ้าหน้าที่ต้องเปิดดูเอกสารที่ตัวเองลงนามออกไปได้

    เดิมเปิดได้เฉพาะเจ้าของคำขอ เจ้าหน้าที่จึงกดออกเอกสารแล้วเห็นแค่เลขที่ ทั้งที่
    เป็นคนลงนามเอง และเป็นคนที่ผู้ยื่นจะโทรมาถามเมื่อข้อความบนเอกสารผิด
    ใช้ presenter ตัวเดียวกับฝั่งผู้ยื่น สองฝั่งจึงเห็นเอกสารใบเดียวกันเสมอ
    """
    application = _load_in_scope(db, application_no, current, request)

    row = license_svc.existing(db, application.id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="คำขอนี้ยังไม่ได้ออกเอกสาร กรุณาอนุมัติและลงนามออกเอกสารก่อน",
        )

    return presenters.to_license_out_for(db, application, row)


@router.get(
    "/applications/{application_no}/license/signature",
    summary="รูปลายมือชื่อผู้ลงนามบนเอกสารที่ออกให้ สำหรับแสดงบนหน้าพิมพ์ (M10)",
    responses={
        403: {"description": "คำขอนี้อยู่นอกเขตที่รับผิดชอบ (T-09)"},
        404: {"description": "ยังไม่ได้ออกเอกสาร หรือเอกสารใบนี้ไม่มีลายมือชื่อเก็บไว้"},
    },
)
def license_signature(
    application_no: str, db: DbSession, current: CurrentOfficer, request: Request,
    download_url: bool = False,
) -> Response:
    """แยกจาก LicenseOut ด้วยเหตุผลเดียวกับฝั่งผู้ยื่น — ไม่ต้องแบกรูปมากับ JSON ทุกครั้ง"""
    application = _load_in_scope(db, application_no, current, request)

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


# ---------------------------------------------------------------- ตัวช่วยภายใน


def _load_in_scope(
    db: DbSession, application_no: str, officer: User, request: Request
) -> Application:
    """T-09 — ปฏิเสธคำขอข้ามเขต และบันทึกความพยายามนั้นไว้เสมอ"""
    application = app_svc.by_number(db, application_no)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบคำขอหมายเลขนี้")

    if not officer_svc.in_scope(db, officer, application):
        officer_svc.deny_cross_authority(
            db,
            officer=officer,
            application=application,
            ip=request.client.host if request.client else None,
            detail=(
                f"พยายามเปิดคำขอ {application_no} "
                f"ซึ่งอยู่นอกเขตที่รับผิดชอบ (อปท. #{application.local_authority_id})"
            ),
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "คำขอนี้อยู่นอกเขตที่คุณรับผิดชอบ จึงเปิดดูไม่ได้ หากต้องการดำเนินการ กรุณาประสานกับเจ้าหน้าที่ของท้องถิ่นนั้น"
            ),
        )
    return application


def _detail(db: DbSession, application: Application) -> OfficerApplicationOut:
    snapshot = app_svc.classification_of(db, application)
    ptype = snapshot.property_type
    prop = db.get(Property, application.property_id)
    authority = db.get(LocalAuthority, application.local_authority_id)

    docs = classify_svc.required_documents(
        db, ptype.id, local_authority_id=application.local_authority_id
    )
    files = doc_svc.current_files(db, application.id)
    pending = officer_svc.mandatory_not_approved(db, application)
    issued = license_svc.existing(db, application.id)
    fee = classify_svc.current_fee(db, ptype.id) if ptype.requires_license else None

    return OfficerApplicationOut(
        application_no=application.application_no,
        status=application.status,
        days_waiting=app_svc.days_waiting(application),
        submitted_at=application.submitted_at,
        decided_at=application.decided_at,
        decision_reason=application.decision_reason,
        property_type_name=ptype.name_th,
        requires_license=ptype.requires_license,
        reason=snapshot.reason_text,
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
        can_approve=not pending and application.status in officer_svc.OPEN_STATUSES,
        pending_documents=pending,
        can_issue_license=(application.status == ApplicationStatus.APPROVED and issued is None),
        license_no=issued.license_no if issued else None,
    )
