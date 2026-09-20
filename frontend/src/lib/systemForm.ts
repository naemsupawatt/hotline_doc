/**
 * แบบฟอร์มที่ระบบกรอกให้ (A01 หนังสือแจ้งฯ / A06 ร.ร.1) — ข้อมูลหน้าพิมพ์ + ลายมือชื่อ
 *
 * ชนิดข้อมูลต้องตรงกับ backend/app/schemas/system_form.py
 *
 * ไม่มี endpoint ที่คืนไฟล์ PDF โดยตั้งใจ: หน้าเว็บจัดหน้ากระดาษแล้วใช้
 * การพิมพ์ของเบราว์เซอร์ ("บันทึกเป็น PDF") เหตุผลเดียวกับใบอนุญาต M10
 * คือเลี่ยงไลบรารี PDF ฝั่งเซิร์ฟเวอร์และปัญหาฟอนต์ไทย
 */
import { api } from "@/lib/api";
import { type ApplicationProperty, uploadDocument } from "@/lib/applications";
import { getToken } from "@/lib/auth";
import type { ClassifyResult } from "@/lib/wizard";

/** รหัสแบบฟอร์มที่มีหน้ากระดาษในระบบ — ตรงกับค่าคงที่ใน services/system_form.py */
export const NOTICE_FORM_CODE = "A01"; // หนังสือแจ้งสถานที่พักที่ไม่เป็นโรงแรม
export const HOTEL_FORM_CODE = "A06"; // แบบ ร.ร.1

export type Applicant = {
  display_name: string;
  is_juristic: boolean;
  juristic_reg_no: string | null;
  /** เลขบัตรแบบปิดบัง — ระบบไม่เคยส่งเลขเต็มออกมาให้หน้าจอ */
  national_id_masked: string | null;
  phone: string | null;
  email: string | null;
};

export type ApplicantInput = {
  display_name: string;
  is_juristic: boolean;
  juristic_reg_no?: string | null;
};

export type Signature = {
  file_id: number;
  version_no: number;
  status: string;
  signed_at: string;
};

/** ช่องแนบที่อยู่ในตัวแบบฟอร์ม เช่น A07–A09 ในแบบ ร.ร.1 */
export type FormAttachment = {
  code: string;
  name_th: string;
  is_mandatory: boolean;
  is_attached: boolean;
};

export type SystemForm = {
  form_code: string;
  title: string;
  application_no: string;
  status: string;
  local_authority_name: string;
  filed_on: string | null;
  property_type_name: string;
  requires_license: boolean;
  fee: ClassifyResult["fee"];
  applicant: Applicant;
  property: ApplicationProperty;
  attachments: FormAttachment[];
  signature: Signature | null;
  can_sign: boolean;
};

function authed() {
  const token = getToken();
  return token ? { token } : {};
}

export function getSystemForm(applicationNo: string, code: string) {
  return api<SystemForm>(
    `/applications/${encodeURIComponent(applicationNo)}/forms/${code}`,
    authed(),
  );
}

/**
 * บันทึกลายมือชื่อลงในแบบฟอร์มที่ระบบกรอกให้
 *
 * ใช้ช่องอัปโหลดของเอกสารฉบับนั้นตรง ๆ ไม่ได้ทำ endpoint ใหม่ ลายมือชื่อจึงได้
 * ระบบรุ่น (เซ็นใหม่ = รุ่นถัดไป ไม่ทับของเดิม) และการตรวจของเจ้าหน้าที่มาฟรี
 */
export function saveSignature(applicationNo: string, png: Blob, code: string) {
  const file = new File([png], "ลายมือชื่อ.png", { type: "image/png" });
  return uploadDocument(applicationNo, code, file);
}

/** ชื่อบนแบบฟอร์มอาจไม่ใช่ชื่อเจ้าของบัญชี เช่น ยื่นในนามนิติบุคคล */
export function updateApplicant(applicationNo: string, input: ApplicantInput) {
  return api<Applicant>(`/applications/${encodeURIComponent(applicationNo)}/applicant`, {
    method: "PATCH",
    body: JSON.stringify(input),
    ...authed(),
  });
}

/** เลขทะเบียนนิติบุคคลเก็บเป็นตัวเลขล้วน แต่แสดงแบบมีขีดให้อ่านง่าย */
export function formatJuristicNo(value: string | null): string {
  if (!value) return "-";
  const d = value.replace(/\D/g, "");
  if (d.length !== 13) return value;
  return `${d[0]}-${d.slice(1, 5)}-${d.slice(5, 10)}-${d.slice(10, 12)}-${d[12]}`;
}
