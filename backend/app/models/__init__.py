"""SQLAlchemy models

โครงตารางที่ต้องสร้าง (อ้างอิงข้อ 8 ของโจทย์ — ทีมปรับได้แต่ต้องอธิบายเหตุผลได้):

  user.py          User, Role, OfficerAssignment (ผูกเจ้าหน้าที่กับ อปท.)
  property.py      Operator, Property (จำนวนห้อง, มีห้องอาหารไหม, พิกัด)
  application.py   Application, ApplicationStatusHistory
  classification.py PropertyType, ClassificationRule, ClassificationResult
  document.py      DocumentType, DocumentFile (มี version), DocumentReview
  authority.py     LocalAuthority, IssuingAgency, ContactPoint
  license.py       License, FeeSchedule (มีผลตามช่วงเวลา)
  audit.py         AuditLog, Notification, ApplicationThread

ทุกไฟล์ที่เพิ่มต้อง import เข้ามาที่นี่ ไม่งั้น Alembic autogenerate จะมองไม่เห็น
"""

from app.core.db import Base  # noqa: F401
from app.models.base import TimestampMixin  # noqa: F401
from app.models.enums import (  # noqa: F401
    ApplicationStatus,
    ClassificationResult,
    DocumentCategory,
    DocumentStatus,
    ReviewDecision,
    UserRole,
)
