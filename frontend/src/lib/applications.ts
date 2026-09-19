/**
 * M6/M7 — เรียก API ของคำขอ
 *
 * ชนิดข้อมูลต้องตรงกับ backend/app/schemas/application.py
 * เส้นทางกลุ่มนี้ต้องแนบ token เสมอ ต่างจาก /wizard ที่เปิดให้ลองได้เลย
 */
import { api } from "@/lib/api";
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
  room_count: number;
  max_guests: number;
  has_restaurant: boolean;
  accommodation_kind: string | null;
  accommodation_kind_other: string | null;
  local_authority_name: string;
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

/** รวมเอกสารทั้งสองหมวดเป็นชุดเดียว เรียงตามที่ backend ส่งมา */
export function allDocuments(app: Application): RequiredDocument[] {
  return [...app.documents.self_service, ...app.documents.external];
}
