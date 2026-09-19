/**
 * US-09 — เรียก API หน้าตั้งค่าของผู้ดูแลระบบ
 *
 * ชนิดข้อมูลต้องตรงกับ backend/app/schemas/admin.py
 */
import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";

export type Rule = {
  code: string;
  property_type_code: string;
  property_type_name: string;
  priority: number;
  min_rooms: number | null;
  max_rooms: number | null;
  min_guests: number | null;
  max_guests: number | null;
  requires_restaurant: boolean | null;
  reason_template: string;
  outcome_message: string;
  is_active: boolean;
  effective_from: string;
  /** กฎนี้เคยตัดสินคำขอไปแล้วกี่ใบ — ใช้เตือนก่อนแก้ */
  applications_classified: number;
};

export type Fee = {
  id: number;
  property_type_code: string;
  property_type_name: string;
  amount: number;
  currency: string;
  validity_years: number;
  effective_from: string;
  effective_to: string | null;
  is_current: boolean;
  note: string | null;
};

export type PreviewResult = {
  matched: boolean;
  property_type_name: string | null;
  reason: string | null;
  rule_code: string | null;
};

/** ช่องที่ส่งค่า null ได้ ต้องบอกผ่าน clear เพราะ null เฉย ๆ แปลว่า "ไม่แก้ช่องนี้" */
export type RuleUpdate = Partial<
  Pick<
    Rule,
    | "priority"
    | "min_rooms"
    | "max_rooms"
    | "min_guests"
    | "max_guests"
    | "requires_restaurant"
    | "reason_template"
    | "outcome_message"
    | "is_active"
  >
> & { clear?: string[] };

function authed() {
  const token = getToken();
  return token ? { token } : {};
}

export function listRules() {
  return api<Rule[]>("/admin/classification-rules", authed());
}

export function updateRule(code: string, changes: RuleUpdate) {
  return api<Rule>(`/admin/classification-rules/${encodeURIComponent(code)}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
    ...authed(),
  });
}

export function previewRules(rooms: number, guests: number, hasRestaurant: boolean) {
  return api<PreviewResult>("/admin/classification-rules/preview", {
    method: "POST",
    body: JSON.stringify({ rooms, guests, has_restaurant: hasRestaurant }),
    ...authed(),
  });
}

export function listFees() {
  return api<Fee[]>("/admin/fee-schedules", authed());
}

export function supersedeFee(
  feeId: number,
  body: { amount: number; validity_years: number; effective_from: string; note?: string },
) {
  return api<Fee[]>(`/admin/fee-schedules/${feeId}/supersede`, {
    method: "POST",
    body: JSON.stringify(body),
    ...authed(),
  });
}
