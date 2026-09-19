/**
 * M11 — เรียก API รายงานภาพรวมส่วนกลาง
 *
 * ชนิดข้อมูลต้องตรงกับ backend/app/schemas/reports.py
 * ทุกช่องเป็นตัวเลขรวม ไม่มีข้อมูลที่ระบุตัวผู้ยื่นหรือเจ้าหน้าที่รายคน
 */
import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";

export type Bucket = { key: string; label: string; count: number };

export type AuthorityRow = {
  name: string;
  total: number;
  waiting_on_officer: number;
  waiting_on_applicant: number;
  finished: number;
  longest_wait_days: number;
};

export type Overview = {
  total: number;
  draft: number;
  waiting_on_officer: number;
  waiting_on_applicant: number;
  finished: number;
  rejected: number;
  by_property_type: Bucket[];
  by_status: Bucket[];
  by_authority: AuthorityRow[];
};

export function getOverview() {
  const token = getToken();
  return api<Overview>("/reports/overview", token ? { token } : {});
}
