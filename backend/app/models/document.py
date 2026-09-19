"""เอกสาร: ชนิด → ข้อกำหนดรายประเภทที่พัก → ไฟล์ที่อัปโหลด (มีรุ่น) → ผลตรวจ"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.authority import IssuingAgency
from app.models.base import TimestampMixin
from app.models.enums import DocumentStatus


class DocumentType(Base, TimestampMixin):
    """ชนิดเอกสาร — รหัส A01–A08 (ทำเองได้) / B01–B07 (ขอจากหน่วยงานอื่น)

    category คือหัวใจของ M3 "แบ่งออกเป็น 2 หมวดชัดเจน"
    issuing_agency_id ใช้ตอบ M4 ว่าต้องไปติดต่อหน่วยงานใด
    """

    __tablename__ = "document_type"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    name_th: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    category: Mapped[str] = mapped_column(String(10), nullable=False)  # DocumentCategory

    # หมวด B เท่านั้นที่มีค่า — หมวด A ผู้ประกอบการทำเองได้
    issuing_agency_id: Mapped[int | None] = mapped_column(ForeignKey("issuing_agency.id"))
    preparation_note: Mapped[str | None] = mapped_column(Text())  # M4: ใช้เอกสารประกอบอะไร
    estimated_days: Mapped[int | None] = mapped_column(Integer)  # M4: ใช้เวลาประมาณเท่าใด

    # บางฉบับผู้ใช้ "กรอกในระบบ" แทนการอัปโหลด เช่น แบบหนังสือแจ้งสถานที่พักฯ
    # ระบบสร้างเอกสารให้จากข้อมูลที่กรอก + ลายเซ็น แล้วพิมพ์ออกมาได้
    is_system_form: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # เอกสารบางฉบับแนบได้หลายไฟล์ เช่น ภาพถ่ายอาคารหลายมุม
    allows_multiple: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

    # ชนิดไฟล์ที่ยอมรับ คั่นด้วยจุลภาค (M5: ต้องตรวจชนิดไฟล์)
    # เก็บใน DB ไม่ใช่ hard-code เพราะเป็นส่วนหนึ่งของ "รายการเอกสาร" ที่ US-09 ให้แก้ได้
    accepted_mime: Mapped[str] = mapped_column(
        String(200), server_default="application/pdf,image/jpeg,image/png", nullable=False
    )

    display_order: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    issuing_agency: Mapped[IssuingAgency | None] = relationship()

    @property
    def accepted_mime_list(self) -> list[str]:
        return [m.strip() for m in self.accepted_mime.split(",") if m.strip()]


class DocumentRequirement(Base, TimestampMixin):
    """เอกสารชนิดใดบังคับสำหรับที่พักประเภทใด (M3 + US-09)

    แยกตารางแทนที่จะใส่ is_required ไว้ใน DocumentType เพราะเอกสารฉบับเดียวกัน
    อาจบังคับกับประเภท 2 แต่ไม่บังคับกับประเภท 1 (3NF: ขึ้นกับคู่ type+doc)
    Super Admin เพิ่ม/ลดรายการเอกสารได้จากตารางนี้โดยไม่ต้องแก้โค้ด
    """

    __tablename__ = "document_requirement"
    __table_args__ = (
        UniqueConstraint("property_type_id", "document_type_id", name="uq_requirement_type_doc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    property_type_id: Mapped[int] = mapped_column(ForeignKey("property_type.id"), nullable=False)
    document_type_id: Mapped[int] = mapped_column(ForeignKey("document_type.id"), nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    note: Mapped[str | None] = mapped_column(Text())

    document_type: Mapped[DocumentType] = relationship()


class DocumentFile(Base, TimestampMixin):
    """ไฟล์ที่อัปโหลด — อัปซ้ำ = สร้างรุ่นใหม่ ไม่ทับของเดิม

    เหตุผล (ตอบ "ข้อควรคิด" ข้อ 2 ของโจทย์ข้อ 8):
    เจ้าหน้าที่ตรวจไฟล์รุ่นไหนไว้ ต้องย้อนดูได้ว่าตอนนั้นเห็นอะไร
    ถ้าทับไฟล์เดิม ผลตรวจใน DocumentReview จะชี้ไปยังไฟล์ที่ไม่มีอยู่จริงแล้ว
    → เก็บทุกรุ่น แล้วใช้ is_current ชี้รุ่นล่าสุดที่ใช้ตัดสินตอนนี้
    """

    __tablename__ = "document_file"
    __table_args__ = (
        UniqueConstraint(
            "application_id",
            "document_type_id",
            "slot_no",
            "version_no",
            name="uq_docfile_version",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("application.id"), nullable=False)
    document_type_id: Mapped[int] = mapped_column(ForeignKey("document_type.id"), nullable=False)

    # ลำดับไฟล์ภายในเอกสารชนิดเดียวกัน — เอกสารทั่วไปมี slot เดียว (1)
    # ส่วนภาพถ่ายอาคารที่แนบได้หลายมุม จะเป็น slot 1, 2, 3, ...
    #
    # ต้องแยกจาก version_no ให้ชัด: slot = "คนละไฟล์", version = "ไฟล์เดิมที่ส่งใหม่"
    # ถ้าใช้ version_no แทนการแนบหลายไฟล์ ภาพมุมที่สองจะกลายเป็นการ
    # "แก้ไข" ภาพมุมแรก ซึ่งทำให้ย้อนดูสิ่งที่เจ้าหน้าที่เคยตรวจไม่ได้ (กฎข้อ 5 ของทีม)
    slot_no: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)

    version_no: Mapped[int] = mapped_column(Integer, server_default="1", nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    stored_path: Mapped[str] = mapped_column(String(300), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)  # M5: ตรวจชนิดไฟล์
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)  # M5: ตรวจขนาดไฟล์

    status: Mapped[str] = mapped_column(
        String(24), server_default=DocumentStatus.UPLOADED, nullable=False
    )
    # S1/T-07: ผลตรวจเบื้องต้นด้วย AI (เบลอ/อ่านไม่ออก) — เตือนก่อนยื่น
    system_check_note: Mapped[str | None] = mapped_column(Text())

    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)

    document_type: Mapped[DocumentType] = relationship()
    reviews: Mapped[list[DocumentReview]] = relationship(back_populates="document_file")


class DocumentReview(Base, TimestampMixin):
    """ผลตรวจรายฉบับของเจ้าหน้าที่ (M8) — ผูกกับ "รุ่นไฟล์" ไม่ใช่ชนิดเอกสาร

    ผูกกับ document_file_id ทำให้ย้อนได้ว่าเจ้าหน้าที่ตรวจไฟล์รุ่นใด
    """

    __tablename__ = "document_review"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_file_id: Mapped[int] = mapped_column(ForeignKey("document_file.id"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)  # ReviewDecision
    comment: Mapped[str | None] = mapped_column(Text())  # บังคับเมื่อ decision = fail
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    document_file: Mapped[DocumentFile] = relationship(back_populates="reviews")
