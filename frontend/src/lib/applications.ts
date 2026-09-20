/**
 * M6/M7 — เรียก API ของคำขอ
 *
 * ชนิดข้อมูลต้องตรงกับ backend/app/schemas/application.py
 * เส้นทางกลุ่มนี้ต้องแนบ token เสมอ ต่างจาก /wizard ที่เปิดให้ลองได้เลย
 */
import { ApiError, BASE, api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { ClassifyResult, RequiredDocument } from "@/lib/wizard";

/** ลักษณะที่พักในแบบหนังสือแจ้งฯ — ต้องตรงกับ AccommodationKind ใน enums.py */
export const ACCOMMODATION_KINDS = [
  { value: "detached_house", label: "บ้านเดี่ยว" },
  { value: "semi_detached", label: "บ้านแฝด" },
  { value: "row_house", label: "ห้องแถว / ตึกแถว" },
  { value: "other", label: "อื่น ๆ" },
] as const;

export type AccommodationKind = (typeof ACCOMMODATION_KINDS)[number]["value"];

export function labelForKind(value: string | null): string {
  return ACCOMMODATION_KINDS.find((k) => k.value === value)?.label ?? "-";
}

/** ที่อยู่แยกช่องตามแบบหนังสือแจ้งฯ — ต้องตรงกับ AddressIn ใน schemas/application.py */
export type AddressInput = {
  address_no: string;
  moo?: string | null;
  soi?: string | null;
  road?: string | null;
  sub_district: string;
  district: string;
  postal_code: string;
};

export type Address = AddressInput & {
  /** จังหวัดเซิร์ฟเวอร์เติมให้ ผู้ใช้เลือกไม่ได้ (ระบบรับเฉพาะภูเก็ต) */
  province: string;
  /** ประกอบจากช่องย่อยฝั่งเซิร์ฟเวอร์ ไม่ได้เก็บซ้ำในฐานข้อมูล */
  full_address: string;
};

export type StartApplicationInput = {
  rooms: number;
  guests: number;
  has_restaurant: boolean;
  local_authority_id: number;
  property_name: string;
  address: AddressInput;
  accommodation_kind: AccommodationKind;
  accommodation_kind_other?: string | null;
  latitude?: number | null;
  longitude?: number | null;
};

export type ApplicationProperty = {
  name: string;
  address: Address;
  /** ชื่อ อปท. ที่ที่พักตั้งอยู่ — มาจาก local_authority_id ของคำขอ */
  local_authority_name: string;
  room_count: number;
  max_guests: number;
  has_restaurant: boolean;
  accommodation_kind: string | null;
  accommodation_kind_other: string | null;
};

export type Application = {
  application_no: string;
  status: string;
  /** M7: อยู่ในสถานะนี้มากี่วันแล้ว */
  days_waiting: number;
  created_at: string;
  submitted_at: string | null;
  property_type_code: string;
  property_type_name: string;
  requires_license: boolean;
  reason: string;
  matched_rule_code: string | null;
  fee: ClassifyResult["fee"];
  property: ApplicationProperty;
  documents: ClassifyResult["documents"];
  /** M8/M9: เหตุผลที่เจ้าหน้าที่ตีกลับหรือไม่อนุมัติ — ผู้ยื่นต้องรู้ว่าต้องแก้อะไร */
  decision_reason: string | null;
  /** M10: มีค่าเมื่อเจ้าหน้าที่ออกเอกสารแล้ว */
  license_no: string | null;
  /** M6: หน้าจอใช้สองค่านี้ตัดสินว่าจะเปิดปุ่ม "ยื่นคำขอ" หรือไม่ */
  can_submit: boolean;
  missing_documents: MissingDocument[];
};

/** T-06: ต้องบอกให้ครบว่าขาดฉบับใด ไม่ใช่แค่ทำปุ่มเป็นสีเทา */
export type MissingDocument = {
  code: string;
  name_th: string;
  /** true = แบบฟอร์มที่ระบบกรอกให้ สิ่งที่ยังขาดคือลายมือชื่อ ไม่ใช่ไฟล์เอกสาร */
  needs_signature: boolean;
};

export type ApplicationSummary = {
  application_no: string;
  status: string;
  days_waiting: number;
  property_name: string;
  property_type_name: string;
  created_at: string;
};

function authed() {
  const token = getToken();
  return token ? { token } : {};
}

export function startApplication(input: StartApplicationInput) {
  return api<Application>("/applications", {
    method: "POST",
    body: JSON.stringify(input),
    ...authed(),
  });
}

export function myApplications() {
  return api<ApplicationSummary[]>("/applications", authed());
}

export function getApplication(applicationNo: string) {
  return api<Application>(`/applications/${encodeURIComponent(applicationNo)}`, authed());
}

export type UploadedFile = {
  id: number;
  slot_no: number;
  version_no: number;
  original_name: string;
  size_bytes: number;
  mime_type: string;
  uploaded_at: string;
};

/**
 * อัปโหลดเอกสารหนึ่งฉบับ
 *
 * ไม่ส่ง slotNo = แนบไฟล์ใหม่ (เอกสารที่แนบได้ไฟล์เดียวจะกลายเป็นรุ่นใหม่ของไฟล์เดิม)
 * ส่ง slotNo = ตั้งใจแทนที่ไฟล์เดิมของ slot นั้น
 */
export function uploadDocument(
  applicationNo: string,
  code: string,
  file: File,
  slotNo?: number,
) {
  const form = new FormData();
  form.append("file", file);
  if (slotNo !== undefined) form.append("slot_no", String(slotNo));

  return api<UploadedFile>(
    `/applications/${encodeURIComponent(applicationNo)}/documents/${code}`,
    { method: "POST", body: form, ...authed() },
  );
}

export function submitApplication(applicationNo: string) {
  return api<Application>(`/applications/${encodeURIComponent(applicationNo)}/submit`, {
    method: "POST",
    ...authed(),
  });
}

/**
 * โหลดไฟล์แนบมาเป็น URL ชั่วคราวสำหรับแสดงบนหน้า (เช่น รูปลายมือชื่อบนแบบฟอร์ม)
 *
 * ใส่ URL ของ API ลงใน <img src> ตรง ๆ ไม่ได้ เพราะปลายทางต้องการ
 * Authorization header ซึ่งแท็ก img แนบไปเองไม่ได้ จึงต้องโหลดเป็น blob ก่อน
 * ผู้เรียกต้อง URL.revokeObjectURL คืนเมื่อเลิกใช้ ไม่งั้นหน่วยความจำรั่ว
 */
export async function fetchDocumentFileUrl(
  applicationNo: string,
  fileId: number,
): Promise<string> {
  const url = `${BASE}/applications/${encodeURIComponent(applicationNo)}/documents/file/${fileId}`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${getToken() ?? ""}` } });
  if (!res.ok) throw new ApiError("เปิดไฟล์แนบไม่ได้ กรุณาลองใหม่อีกครั้ง", res.status);
  return URL.createObjectURL(await res.blob());
}

/**
 * เปิดไฟล์แนบในแท็บใหม่ — ฝาแฝดฝั่งผู้ยื่นของ openDocumentFile ใน lib/officer.ts
 *
 * เหตุผลที่ต้องโหลดเป็น blob ก่อนเหมือนกัน: ปลายทางต้องการ Authorization header
 */
export async function openDocumentFile(applicationNo: string, fileId: number): Promise<void> {
  const url = await fetchDocumentFileUrl(applicationNo, fileId);
  window.open(url, "_blank", "noopener");
  // ปล่อยหน่วยความจำคืนหลังเบราว์เซอร์เปิดไฟล์เสร็จ
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** ขนาดไฟล์แบบที่คนอ่านเข้าใจ — NFR Usability ห้ามโชว์จำนวนไบต์ดิบ */
export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} ไบต์`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** เอกสารสิทธิ์ที่ระบบออกให้ — ต้องตรงกับ LicenseOut ใน schemas/license.py */
export type LicenseDocument = {
  license_no: string;
  kind: "license" | "notice_receipt";
  title: string;
  application_no: string;
  property_type_name: string;
  holder_name: string;
  issued_at: string;
  valid_from: string;
  valid_until: string | null;
  is_expired: boolean;
  is_revoked: boolean;
  fee_amount: number | null;
  fee_currency: string | null;
  issued_by_name: string;
  /** โหลดรูปได้ด้วย licenseSignatureUrl() เมื่อเป็น true */
  has_issuer_signature: boolean;
  local_authority_name: string;
  property: ApplicationProperty;
};

export function getLicense(applicationNo: string) {
  return api<LicenseDocument>(
    `/applications/${encodeURIComponent(applicationNo)}/license`,
    authed(),
  );
}

/**
 * รูปลายมือชื่อเจ้าหน้าที่ผู้ลงนามบนเอกสารที่ออกให้ (M10)
 *
 * แยกจาก LicenseOut เป็นคนละคำขอ เพราะถ้าฝัง base64 มากับ JSON
 * ทุกครั้งที่เปิดหน้าใบอนุญาตจะต้องโหลดรูปไปด้วยเสมอแม้ยังไม่ได้ใช้
 */
export async function licenseSignatureUrl(applicationNo: string): Promise<string> {
  const url = `${BASE}/applications/${encodeURIComponent(applicationNo)}/license/signature`;
  const res = await fetch(url, { headers: { Authorization: `Bearer ${getToken() ?? ""}` } });
  if (!res.ok) throw new ApiError("โหลดลายมือชื่อผู้ลงนามไม่ได้", res.status);
  return URL.createObjectURL(await res.blob());
}

/** วันที่แบบไทย พ.ศ. — เอกสารราชการใช้ พ.ศ. ไม่ใช่ ค.ศ. */
export function thaiDate(iso: string): string {
  return new Date(iso).toLocaleDateString("th-TH", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** รวมเอกสารทั้งสองหมวดเป็นชุดเดียว เรียงตามที่ backend ส่งมา */
export function allDocuments(app: Application): RequiredDocument[] {
  return [...app.documents.self_service, ...app.documents.external];
}
