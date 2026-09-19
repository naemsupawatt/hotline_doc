"""M5 — อัปโหลดเอกสาร + ตรวจชนิด/ขนาดไฟล์ + เก็บเป็นรุ่น (version)

ข้อ 8 ของโจทย์ถามตรง ๆ ว่า "อัปโหลดฉบับเดิมซ้ำเพื่อแก้ไข ควรทับไฟล์เดิม
หรือเก็บเป็นรุ่นใหม่" -> ระบบนี้เลือกเก็บเป็นรุ่นใหม่ทุกครั้ง เพราะไฟล์ที่
เจ้าหน้าที่เคยตรวจต้องย้อนดูได้ และ DocumentReview ต้องชี้ไปยังไฟล์รุ่นที่ถูกตรวจจริง

เส้นทางของไฟล์นี้ซ้อนอยู่ใต้ /applications เพราะเอกสารไม่มีความหมาย
ถ้าไม่มีคำขอ  router จึงถูก include แบบไม่มี prefix (ดู api/v1/router.py)

เจ้าของงานส่วนนี้: <ใส่ชื่อสมาชิก>
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.api import presenters
from app.api.deps import CurrentOperator, DbSession
from app.models.audit import AuditLog
from app.models.document import DocumentFile
from app.schemas.wizard import UploadedFileOut
from app.services import application as app_svc
from app.services import document as doc_svc

router = APIRouter()

PREFIX = "/applications/{application_no}/documents"


def _load_owned(db: DbSession, application_no: str, current, request: Request):
    """คำขอของผู้ใช้รายนี้เท่านั้น — ตอบ 404 เหมือนกันทั้งกรณีไม่มีและไม่ใช่ของตน"""
    application = app_svc.by_number(db, application_no)

    if application is not None and not app_svc.is_owner(db, application, current):
        db.add(
            AuditLog(
                actor_id=current.id,
                action="application.access_denied",
                entity_type="application",
                entity_id=application.id,
                outcome="denied",
                detail=f"พยายามจัดการเอกสารของคำขอ {application_no} ซึ่งไม่ใช่ของตน",
                ip_address=request.client.host if request.client else None,
            )
        )
        db.commit()
        application = None

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบคำขอหมายเลขนี้ในบัญชีของคุณ",
        )
    return application


@router.post(
    PREFIX + "/{code}",
    response_model=UploadedFileOut,
    status_code=status.HTTP_201_CREATED,
    tags=["documents"],
    summary="อัปโหลดเอกสารหนึ่งฉบับ (อัปซ้ำ = สร้างรุ่นใหม่)",
    responses={
        404: {"description": "ไม่พบคำขอ หรือเอกสารรหัสนี้ไม่ได้ใช้กับที่พักประเภทนี้"},
        409: {"description": "คำขอถูกยื่นไปแล้ว แก้ไขเอกสารไม่ได้"},
        422: {"description": "ชนิดไฟล์หรือขนาดไฟล์ไม่ผ่านเกณฑ์"},
    },
)
async def upload_document(
    application_no: str,
    code: str,
    db: DbSession,
    current: CurrentOperator,
    request: Request,
    file: Annotated[UploadFile, File(description="ไฟล์เอกสาร")],
    slot_no: Annotated[
        int | None,
        Form(description="ระบุเมื่อต้องการแทนที่ไฟล์เดิมของ slot นั้น เว้นว่าง = แนบไฟล์ใหม่"),
    ] = None,
) -> UploadedFileOut:
    application = _load_owned(db, application_no, current, request)

    if not app_svc.is_editable(application):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("คำขอนี้ยื่นไปแล้ว จึงแก้ไขเอกสารไม่ได้ หากเจ้าหน้าที่ขอให้แก้ไข ระบบจะเปิดให้ส่งเอกสารใหม่เอง"),
        )

    snapshot = app_svc.classification_of(db, application)
    requirement = doc_svc.requirement_for(db, snapshot.property_type_id, code.upper())
    if requirement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบเอกสารรหัสนี้ในรายการเอกสารของคำขอนี้",
        )

    doc = requirement.document_type
    data = await file.read()

    problem = doc_svc.validate(doc, content_type=file.content_type or "", size=len(data))
    if problem:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=problem)

    if slot_no is None and not doc.allows_multiple:
        slot_no = 1  # เอกสารไฟล์เดียว: อัปซ้ำคือรุ่นใหม่ของ slot เดิมเสมอ

    saved = doc_svc.save_upload(
        db,
        application=application,
        doc=doc,
        user=current,
        original_name=file.filename or "ไฟล์แนบ",
        content_type=file.content_type or "",
        data=data,
        slot_no=slot_no,
    )

    db.add(
        AuditLog(
            actor_id=current.id,
            action="document.upload",
            entity_type="document_file",
            entity_id=saved.file.id,
            outcome="success",
            detail=(
                f"อัปโหลด {doc.code} ของคำขอ {application.application_no} "
                f"(ไฟล์ที่ {saved.file.slot_no} รุ่นที่ {saved.file.version_no})"
            ),
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
    db.refresh(saved.file)
    return presenters.to_file_out(saved.file)


@router.get(
    PREFIX + "/file/{file_id}",
    tags=["documents"],
    summary="เปิดไฟล์ที่แนบไว้",
    responses={404: {"description": "ไม่พบไฟล์"}},
)
def download_document(
    application_no: str,
    file_id: int,
    db: DbSession,
    current: CurrentOperator,
    request: Request,
) -> FileResponse:
    application = _load_owned(db, application_no, current, request)

    row = db.get(DocumentFile, file_id)
    if row is None or row.application_id != application.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบไฟล์ที่ต้องการ")

    path = doc_svc.storage_root() / row.stored_path
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไฟล์นี้หาไม่พบในระบบจัดเก็บ กรุณาอัปโหลดใหม่",
        )

    return FileResponse(path, media_type=row.mime_type, filename=row.original_name)
