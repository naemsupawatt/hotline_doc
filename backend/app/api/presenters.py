"""แปลงผลจาก service เป็น schema สำหรับส่งออก

มีไฟล์นี้เพราะทั้ง /wizard/classify และ /applications/{no} ต้องส่ง
"รายการเอกสาร 2 หมวด" หน้าตาเดียวกัน ถ้าปล่อยให้แต่ละ endpoint ประกอบเอง
สองที่นี้จะค่อย ๆ เพี้ยนจากกัน แล้วหน้าจอที่ใช้ทั้งสองจะพังแบบหาสาเหตุยาก
"""

from app.models.document import DocumentFile
from app.models.enums import DocumentCategory, DocumentStatus
from app.schemas.wizard import (
    ContactPointOut,
    DocumentChecklistOut,
    DocumentOut,
    UploadedFileOut,
)
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


def to_file_out(row: DocumentFile) -> UploadedFileOut:
    return UploadedFileOut(
        id=row.id,
        slot_no=row.slot_no,
        version_no=row.version_no,
        original_name=row.original_name,
        size_bytes=row.size_bytes,
        mime_type=row.mime_type,
        uploaded_at=row.created_at,
    )


def _status_of(doc, files: list[DocumentFile]) -> str:
    """สถานะรายฉบับที่หน้าจอเอาไปแปลงเป็นสี

    แบบฟอร์มที่กรอกในระบบถือว่าพร้อมตั้งแต่เปิดคำขอ เพราะข้อมูลที่ใช้
    ถูกกรอกครบไปแล้ว ไม่มีไฟล์ให้แนบ จึงไม่ควรค้างเป็น "ยังไม่ได้อัปโหลด"
    """
    if doc.is_system_form:
        return DocumentStatus.UPLOADED
    if not files:
        return DocumentStatus.NOT_UPLOADED
    # ทุกไฟล์ของเอกสารฉบับเดียวกันใช้สถานะเดียวกัน ใช้ของไฟล์แรกเป็นตัวแทน
    return files[0].status


def to_document_out(
    item: svc.RequiredDocument, files: list[DocumentFile] | None = None
) -> DocumentOut:
    doc = item.document_type
    attached = files or []
    return DocumentOut(
        status=_status_of(doc, attached),
        files=[to_file_out(f) for f in attached],
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
    items: list[svc.RequiredDocument],
    *,
    local_authority_id: int | None,
    files: list[DocumentFile] | None = None,
) -> DocumentChecklistOut:
    """แยก 2 หมวดตาม M3 ให้เสร็จตั้งแต่ชั้น API

    หน้าจอจึงไม่ต้องรู้กติกาการแบ่ง แค่วาดสองกล่อง
    """
    self_service: list[DocumentOut] = []
    external: list[DocumentOut] = []

    by_type: dict[int, list[DocumentFile]] = {}
    for row in files or []:
        by_type.setdefault(row.document_type_id, []).append(row)

    for item in items:
        bucket = (
            external
            if DocumentCategory(item.document_type.category) is DocumentCategory.EXTERNAL
            else self_service
        )
        bucket.append(to_document_out(item, by_type.get(item.document_type.id)))

    return DocumentChecklistOut(
        self_service=self_service,
        external=external,
        # มีเอกสารที่ต้องไปขอ แต่ยังไม่รู้ว่าเขตไหน -> หน้าจอต้องให้เลือกก่อน
        needs_local_authority=bool(external) and local_authority_id is None,
    )


def to_property_out(prop, local_authority_name: str):
    """แปลง Property เป็น schema — ใช้ซ้ำทั้งฝั่งผู้ยื่น เจ้าหน้าที่ และหน้าพิมพ์"""
    from app.schemas.application import AddressOut, PropertyOut

    return PropertyOut(
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
        local_authority_name=local_authority_name,
    )


# ชื่อเอกสารบนหัวกระดาษ แยกตามชนิด
LICENSE_TITLE = {
    "license": "ใบอนุญาตประกอบธุรกิจโรงแรม",
    "notice_receipt": "หนังสือรับรองการแจ้งสถานที่พักที่ไม่เป็นโรงแรม",
}


def to_license_out(db, row, application, prop, authority, holder, issuer):
    """ประกอบข้อมูลทั้งหมดที่หน้าพิมพ์ต้องใช้ไว้ในก้อนเดียว"""
    from app.models.classification import PropertyType
    from app.schemas.license import LicenseOut
    from app.services import license as license_svc

    ptype = db.get(PropertyType, row.property_type_id)

    return LicenseOut(
        license_no=row.license_no,
        kind=row.kind,
        title=LICENSE_TITLE.get(row.kind, "เอกสารอ้างอิง"),
        application_no=application.application_no,
        property_type_name=ptype.name_th if ptype else "-",
        holder_name=holder.full_name if holder else "-",
        issued_at=row.issued_at,
        valid_from=row.valid_from,
        valid_until=row.valid_until,
        is_expired=license_svc.is_expired(row),
        is_revoked=row.is_revoked,
        fee_amount=float(row.fee_amount) if row.fee_amount is not None else None,
        fee_currency="THB" if row.fee_amount is not None else None,
        issued_by_name=issuer.full_name if issuer else "-",
        local_authority_name=authority.name if authority else "-",
        property=to_property_out(prop, authority.name if authority else "-"),
    )
