/**
 * เลขประจำตัวประชาชนไทย — ฝั่งหน้าเว็บ
 *
 * ตรรกะเดียวกับ backend/app/core/thai_id.py
 * ทำซ้ำฝั่งนี้เพื่อให้ผู้ใช้รู้ผลทันทีที่พิมพ์ครบ ไม่ต้องรอส่งฟอร์ม
 * แต่ backend ยังต้องตรวจซ้ำเสมอ เพราะการตรวจฝั่งหน้าเว็บถูกข้ามได้
 *
 * ถ้าแก้สูตรที่ไฟล์ใดไฟล์หนึ่ง ต้องแก้อีกไฟล์ด้วย
 */

/** ความยาวของเลขบัตร — ใช้ตัดค่าที่ช่องกรอกด้วย ไม่งั้นผู้ใช้พิมพ์เกิน
    แล้วเห็นบนจอครบ 13 หลักถูกต้อง แต่ค่าจริงในฟอร์มมี 14 หลักและถูกตีว่าผิด */
export const THAI_ID_DIGITS = 13;

export function normalizeThaiId(value: string): string {
  return value.replace(/\D/g, "");
}

export function isValidThaiId(value: string): boolean {
  const d = normalizeThaiId(value);
  if (d.length !== THAI_ID_DIGITS) return false;

  let total = 0;
  for (let i = 0; i < 12; i++) total += Number(d[i]) * (13 - i);
  return ((11 - (total % 11)) % 10) === Number(d[12]);
}

/** จัดรูปแบบระหว่างพิมพ์ -> 1-2345-67890-12-3 */
export function formatThaiId(value: string): string {
  const d = normalizeThaiId(value).slice(0, THAI_ID_DIGITS);
  const parts = [d.slice(0, 1), d.slice(1, 5), d.slice(5, 10), d.slice(10, 12), d.slice(12, 13)];
  return parts.filter(Boolean).join("-");
}
