/**
 * M8/M9 — เรียก API ของเจ้าหน้าที่ท้องถิ่น
 *
 * ชนิดข้อมูลต้องตรงกับ backend/app/schemas/officer.py
 * ทุกเส้นทางต้องแนบ token และถูกกรองด้วยเขตที่เจ้าหน้าที่สังกัดเสมอ (T-09)
 */
import { api, fileBlobUrl } from "@/lib/api";
import type { ApplicationProperty, LicenseDocument } from "@/lib/applications";
import { getToken } from "@/lib/auth";
import type { SystemForm } from "@/lib/systemForm";
import type { ClassifyResult } from "@/lib/wizard";

export type QueueItem = {
  application_no: string;
  status: string;
  days_waiting: number;
  property_name: string;
  property_type_name: string;
  local_authority_name: string;
  submitted_at: string | null;
};

export type OfficerApplication = {
  application_no: string;
  status: string;
  days_waiting: number;
  submitted_at: string | null;
  decided_at: string | null;
  decision_reason: string | null;
  property_type_name: string;
  requires_license: boolean;
  reason: string;
  fee: ClassifyResult["fee"];
  property: ApplicationProperty;
  documents: ClassifyResult["documents"];
  can_approve: boolean;
  /** M10: ออกเอกสารได้เมื่ออนุมัติแล้วและยังไม่เคยออก */
  can_issue_license: boolean;
  license_no: string | null;
  /** เอกสารบังคับที่ยังไม่ผ่านการตรวจ — ใช้บอกว่าทำไมยังกดอนุมัติไม่ได้ */
  pending_documents: string[];
};

/** ผลตรวจรายฉบับ — ต้องตรงกับ ReviewDecision ใน enums.py */
export type ReviewDecision = "pass" | "request_revision" | "fail";

/** ผลพิจารณาคำขอทั้งใบ */
export type Decision = "approve" | "reject" | "request_revision";

function authed() {
  const token = getToken();
  return token ? { token } : {};
}

/** กลุ่มคิวที่เลือกดูได้ — ต้องตรงกับ QUEUE_SCOPES ใน services/officer.py */
export type QueueScope = "open" | "revision" | "closed" | "all";

export function officerQueue(scope: QueueScope = "open") {
  return api<QueueItem[]>(`/officer/queue?scope=${scope}`, authed());
}

export function officerApplication(applicationNo: string) {
  return api<OfficerApplication>(
    `/officer/applications/${encodeURIComponent(applicationNo)}`,
    authed(),
  );
}

export function reviewDocument(
  applicationNo: string,
  fileId: number,
  decision: ReviewDecision,
  comment?: string,
) {
  return api<OfficerApplication>(
    `/officer/applications/${encodeURIComponent(applicationNo)}/documents/${fileId}/review`,
    { method: "POST", body: JSON.stringify({ decision, comment: comment ?? null }), ...authed() },
  );
}

export function decideApplication(applicationNo: string, decision: Decision, reason?: string) {
  return api<OfficerApplication>(
    `/officer/applications/${encodeURIComponent(applicationNo)}/decide`,
    { method: "POST", body: JSON.stringify({ decision, reason: reason ?? null }), ...authed() },
  );
}

/**
 * ออกใบอนุญาต/หนังสือรับรอง พร้อมลายมือชื่อผู้ลงนาม
 *
 * ลายมือชื่อบังคับ เพราะเอกสารที่ไม่มีใครลงนามคือเอกสารที่ใช้ไม่ได้
 * กติกาเดียวกับที่ผู้ยื่นต้องลงลายมือชื่อในแบบฟอร์มก่อนยื่น (M6)
 */
export function issueLicense(applicationNo: string, signature: Blob) {
  const form = new FormData();
  form.append("signature", new File([signature], "ลายมือชื่อผู้ลงนาม.png", { type: "image/png" }));

  return api<OfficerApplication>(
    `/officer/applications/${encodeURIComponent(applicationNo)}/issue-license`,
    { method: "POST", body: form, ...authed() },
  );
}

/**
 * แบบฟอร์มที่ระบบกรอกให้ ฉบับที่เจ้าหน้าที่เปิดดู — อ่านอย่างเดียว
 *
 * เจ้าหน้าที่ต้องเห็น "หนังสือที่ลงลายมือชื่อแล้ว" ฉบับเดียวกับที่ผู้ยื่นเห็น
 * ไม่ใช่เห็นแต่ไฟล์รูปลายเซ็นซึ่งบอกไม่ได้ว่าเซ็นกำกับข้อความอะไรไว้
 * ฝั่งเซิร์ฟเวอร์ใช้ presenter ตัวเดียวกับของผู้ยื่น ชนิดข้อมูลจึงเป็น SystemForm เดิม
 */
export function getSystemForm(applicationNo: string, code: string) {
  return api<SystemForm>(
    `/officer/applications/${encodeURIComponent(applicationNo)}/forms/${code}`,
    authed(),
  );
}

/**
 * โหลดไฟล์แนบมาเป็น URL ชั่วคราวสำหรับแสดงบนหน้า (เช่น รูปลายมือชื่อบนแบบฟอร์ม)
 *
 * ฝาแฝดฝั่งเจ้าหน้าที่ของ fetchDocumentFileUrl ใน lib/applications.ts
 * ใส่ URL ของ API ลงใน <img src> ตรง ๆ ไม่ได้ เพราะปลายทางต้องการ
 * Authorization header ผู้เรียกต้อง URL.revokeObjectURL คืนเมื่อเลิกใช้
 */
export async function fetchDocumentFileUrl(
  applicationNo: string,
  fileId: number,
): Promise<string> {
  return fileBlobUrl(`/officer/applications/${encodeURIComponent(applicationNo)}/documents/file/${fileId}`, getToken() ?? "");
}

/**
 * เอกสารที่ออกให้คำขอนี้ ฉบับที่เจ้าหน้าที่เปิดดู (M10)
 *
 * เจ้าหน้าที่เป็นคนลงนามออกเอกสาร จึงต้องเปิดดูใบที่ออกไปได้ ไม่ใช่เห็นแค่เลขที่
 * ฝั่งเซิร์ฟเวอร์ใช้ presenter ตัวเดียวกับของผู้ยื่น ชนิดข้อมูลจึงเป็นตัวเดิม
 */
export function getLicense(applicationNo: string) {
  return api<LicenseDocument>(
    `/officer/applications/${encodeURIComponent(applicationNo)}/license`,
    authed(),
  );
}

/** รูปลายมือชื่อผู้ลงนาม — ฝาแฝดฝั่งเจ้าหน้าที่ของ licenseSignatureUrl ใน lib/applications.ts */
export async function licenseSignatureUrl(applicationNo: string): Promise<string> {
  return fileBlobUrl(`/officer/applications/${encodeURIComponent(applicationNo)}/license/signature`, getToken() ?? "");
}

/**
 * เปิดไฟล์เอกสารในแท็บใหม่
 *
 * ใช้ fetch แทน <a href> เพราะปลายทางต้องการ Authorization header
 * ซึ่งแท็กลิงก์ธรรมดาแนบไปด้วยไม่ได้ จึงต้องโหลดเป็น blob แล้วค่อยเปิด
 */
export async function openDocumentFile(applicationNo: string, fileId: number): Promise<void> {
  const url = await fetchDocumentFileUrl(applicationNo, fileId);
  window.open(url, "_blank", "noopener");
  // ปล่อยหน่วยความจำคืนหลังเบราว์เซอร์เปิดไฟล์เสร็จ
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
