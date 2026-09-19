"""แปลงผลจาก service เป็น schema สำหรับส่งออก

มีไฟล์นี้เพราะทั้ง /wizard/classify และ /applications/{no} ต้องส่ง
"รายการเอกสาร 2 หมวด" หน้าตาเดียวกัน ถ้าปล่อยให้แต่ละ endpoint ประกอบเอง
สองที่นี้จะค่อย ๆ เพี้ยนจากกัน แล้วหน้าจอที่ใช้ทั้งสองจะพังแบบหาสาเหตุยาก
"""

from app.models.enums import DocumentCategory
from app.schemas.wizard import ContactPointOut, DocumentChecklistOut, DocumentOut
from app.services import classification as svc


def to_contact_out(item: svc.RequiredDocument) -> ContactPointOut | None:
    cp = item.contact_point
    agency = item.document_type.issuing_agency
    if cp is None or agency is None:
        return None
    return ContactPointOut(
        agency_name=agency.name,
        local_authority_name=cp.local_authority.name if cp.local_authority else None,
        office_name=cp.office_name,
        address=cp.address,
        phone=cp.phone,
        office_hours=cp.office_hours,
        estimated_days=cp.estimated_days,
        notes=cp.notes,
    )


def to_document_out(item: svc.RequiredDocument) -> DocumentOut:
    doc = item.document_type
    return DocumentOut(
        code=doc.code,
        name_th=doc.name_th,
        description=doc.description,
        is_mandatory=item.requirement.is_mandatory,
        is_system_form=doc.is_system_form,
        allows_multiple=doc.allows_multiple,
        accepted_mime=doc.accepted_mime_list,
        preparation_note=doc.preparation_note,
        estimated_days=doc.estimated_days,
        contact_point=to_contact_out(item),
    )


def to_checklist(
    items: list[svc.RequiredDocument], *, local_authority_id: int | None
) -> DocumentChecklistOut:
    """แยก 2 หมวดตาม M3 ให้เสร็จตั้งแต่ชั้น API

    หน้าจอจึงไม่ต้องรู้กติกาการแบ่ง แค่วาดสองกล่อง
    """
    self_service: list[DocumentOut] = []
    external: list[DocumentOut] = []

    for item in items:
        bucket = (
            external
            if DocumentCategory(item.document_type.category) is DocumentCategory.EXTERNAL
            else self_service
        )
        bucket.append(to_document_out(item))

    return DocumentChecklistOut(
        self_service=self_service,
        external=external,
        # มีเอกสารที่ต้องไปขอ แต่ยังไม่รู้ว่าเขตไหน -> หน้าจอต้องให้เลือกก่อน
        needs_local_authority=bool(external) and local_authority_id is None,
    )
