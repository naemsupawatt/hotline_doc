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

/**
 * เอกสารหนึ่งฉบับ กับจำนวนคำขอที่ติดค้างอยู่ที่ฉบับนั้น
 *
 * นิยาม "ยังไม่ได้ตรวจ" เป็นชุดเดียวกับสัญลักษณ์แจ้งเตือนในคิวเจ้าหน้าที่
 * (REVIEWED_DOCUMENT_STATUSES ใน backend/app/services/officer.py)
 * หน้าจอไม่ได้ไล่นับสถานะเอง รับตัวเลขจาก API มาตรง ๆ
 */
export type DocumentBottleneck = {
  code: string;
  name_th: string;
  /** จำนวนคำขอที่เอกสารฉบับนี้ยังไม่ได้ตรวจ */
  count: number;
  /** ฉบับที่ค้างรอตรวจนานที่สุดกี่วัน */
  oldest_days: number;
  /** กระจายตัวตามท้องถิ่น เฉพาะเขตที่มีของค้างจริง เรียงจากมากไปน้อย */
  by_authority: Bucket[];
};

export function getDocumentBottlenecks() {
  const token = getToken();
  return api<DocumentBottleneck[]>("/reports/document-bottlenecks", token ? { token } : {});
}

/**
 * เอกสารหนึ่งฉบับ กับจำนวนคำขอที่ผู้ยื่นยังไม่ได้แนบเข้ามา
 *
 * คู่แฝดของ DocumentBottleneck แต่มองอีกฝั่งของกระบวนการ:
 * อันนั้นคือของที่ส่งมาแล้วค้างที่เจ้าหน้าที่ อันนี้คือของที่ยังไม่ถูกส่งมา
 */
export type MissingUpload = {
  code: string;
  name_th: string;
  /** จำนวนคำขอที่ยังไม่ได้แนบเอกสารฉบับนี้ */
  count: number;
  /** ในจำนวนนั้น เป็นคำขอที่เอกสารฉบับนี้บังคับกี่ใบ — ฉบับไม่บังคับบางชนิดตั้งใจให้ขาดได้ */
  mandatory_count: number;
  by_authority: Bucket[];
};

export function getMissingUploads() {
  const token = getToken();
  return api<MissingUpload[]>("/reports/missing-uploads", token ? { token } : {});
}
