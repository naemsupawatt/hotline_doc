/**
 * M2/M3/M4 — เรียก API ของระบบนำทาง
 *
 * ชนิดข้อมูลในไฟล์นี้ต้องตรงกับ backend/app/schemas/wizard.py
 * ถ้าแก้ฝั่งใดฝั่งหนึ่งต้องแก้อีกฝั่งด้วย
 *
 * endpoint กลุ่มนี้ไม่ต้องล็อกอิน ตั้งใจให้ลองประเมินได้ทันทีตาม US-01
 */
import { api } from "@/lib/api";

export type LocalAuthority = {
  id: number;
  code: string;
  name: string;
  kind: string;
  district: string;
};

export type ContactPoint = {
  agency_name: string;
  local_authority_name: string | null;
  office_name: string;
  address: string | null;
  phone: string | null;
  office_hours: string | null;
  estimated_days: number | null;
  notes: string | null;
};

export type RequiredDocument = {
  code: string;
  name_th: string;
  description: string | null;
  is_mandatory: boolean;
  /** true = กรอกในระบบ ไม่ต้องอัปโหลดไฟล์ (เช่น A01 แบบหนังสือแจ้งฯ) */
  is_system_form: boolean;
  allows_multiple: boolean;
  accepted_mime: string[];
  preparation_note: string | null;
  estimated_days: number | null;
  contact_point: ContactPoint | null;
};

export type ClassifyResult = {
  property_type_code: string;
  property_type_name: string;
  requires_license: boolean;
  is_out_of_scope: boolean;
  /** M2 บังคับ: เหตุผลว่าทำไมจึงได้ผลนั้น */
  reason: string;
  outcome_message: string;
  /** กฎใน DB ที่ใช้ตัดสิน — ใช้สาธิต US-09 */
  matched_rule_code: string | null;
  fee: { amount: number; currency: string; validity_years: number } | null;
  documents: {
    self_service: RequiredDocument[];
    external: RequiredDocument[];
    needs_local_authority: boolean;
  };
};

export type WizardAnswers = {
  rooms: number;
  guests: number;
  has_restaurant: boolean;
  local_authority_id: number | null;
};

export function listLocalAuthorities() {
  return api<LocalAuthority[]>("/wizard/local-authorities");
}

export function classify(answers: WizardAnswers) {
  return api<ClassifyResult>("/wizard/classify", {
    method: "POST",
    body: JSON.stringify(answers),
  });
}

/** แปลง mime เป็นคำที่ผู้ใช้ทั่วไปเข้าใจ — NFR Usability ห้ามโชว์ "application/pdf" ดิบ */
export function describeAccepted(mimes: string[]): string {
  const hasPdf = mimes.includes("application/pdf");
  const hasImage = mimes.some((m) => m.startsWith("image/"));

  if (hasPdf && hasImage) return "ไฟล์ PDF หรือรูปถ่าย";
  if (hasPdf) return "ไฟล์ PDF เท่านั้น";
  if (hasImage) return "รูปถ่าย (JPG หรือ PNG)";
  return mimes.join(", ");
}
