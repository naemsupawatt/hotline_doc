/**
 * ค่าสถานะ — ต้องตรงกับ backend/app/models/enums.py เสมอ
 *
 * ขั้นต่อไปเมื่อ API เริ่มนิ่ง ให้ generate ไฟล์นี้อัตโนมัติจาก OpenAPI แทนการพิมพ์เอง:
 *   npx openapi-typescript http://localhost:8000/openapi.json -o src/types/api.d.ts
 */

export type UserRole = "operator" | "officer" | "central" | "super_admin";

export type ClassificationResult = "not_hotel" | "type_1" | "type_2" | "out_of_scope";

export type ApplicationStatus =
  | "draft"
  | "submitted"
  | "under_review"
  | "needs_revision"
  | "approved"
  | "rejected"
  | "license_issued";

/** 7 สถานะตาม legend ในแบบหน้าจอ */
export type DocumentStatus =
  | "not_uploaded"
  | "uploaded"
  | "system_flagged"
  | "officer_reviewing"
  | "revision_requested"
  | "approved"
  | "not_required";

export type DocumentCategory = "self" | "external";

export type ReviewDecision = "pass" | "request_revision" | "fail";
