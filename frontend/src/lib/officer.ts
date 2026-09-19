/**
 * M8/M9 — เรียก API ของเจ้าหน้าที่ท้องถิ่น
 *
 * ชนิดข้อมูลต้องตรงกับ backend/app/schemas/officer.py
 * ทุกเส้นทางต้องแนบ token และถูกกรองด้วยเขตที่เจ้าหน้าที่สังกัดเสมอ (T-09)
 */
import { api } from "@/lib/api";
import type { ApplicationProperty } from "@/lib/applications";
import { getToken } from "@/lib/auth";
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

export function officerQueue() {
  return api<QueueItem[]>("/officer/queue", authed());
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

export function issueLicense(applicationNo: string) {
  return api<OfficerApplication>(
    `/officer/applications/${encodeURIComponent(applicationNo)}/issue-license`,
    { method: "POST", ...authed() },
  );
}

/**
 * เปิดไฟล์เอกสารในแท็บใหม่
 *
 * ใช้ fetch แทน <a href> เพราะปลายทางต้องการ Authorization header
 * ซึ่งแท็กลิงก์ธรรมดาแนบไปด้วยไม่ได้ จึงต้องโหลดเป็น blob แล้วค่อยเปิด
 */
export async function openDocumentFile(
  applicationNo: string,
  fileId: number,
): Promise<void> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const url = `${base}/officer/applications/${encodeURIComponent(applicationNo)}/documents/file/${fileId}`;

  const res = await fetch(url, { headers: { Authorization: `Bearer ${getToken() ?? ""}` } });
  if (!res.ok) throw new Error("เปิดไฟล์ไม่ได้");

  const objectUrl = URL.createObjectURL(await res.blob());
  window.open(objectUrl, "_blank", "noopener");
  // ปล่อยหน่วยความจำคืนหลังเบราว์เซอร์เปิดไฟล์เสร็จ
  setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
}
