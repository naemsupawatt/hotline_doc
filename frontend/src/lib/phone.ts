/**
 * หมายเลขโทรศัพท์ไทย — ฝั่งหน้าเว็บ
 *
 * ตรรกะเดียวกับ backend/app/core/phone.py
 * ทำซ้ำฝั่งนี้เพื่อให้ผู้ใช้รู้ผลทันทีที่พิมพ์ครบ ไม่ต้องรอส่งฟอร์ม
 * แต่ backend ยังต้องตรวจซ้ำเสมอ เพราะการตรวจฝั่งหน้าเว็บถูกข้ามได้
 *
 * ถ้าแก้สูตรที่ไฟล์ใดไฟล์หนึ่ง ต้องแก้อีกไฟล์ด้วย
 */

/** ความยาวสูงสุดที่ยอมรับ — ใช้ตัดค่าที่ช่องกรอกด้วย ไม่งั้นผู้ใช้พิมพ์เกิน
    แล้วเห็นบนจอ 10 หลักถูกต้อง แต่ค่าในฟอร์มมี 11 หลักและถูกตีว่าผิด */
export const PHONE_MAX_DIGITS = 10;

const MOBILE_LENGTH = PHONE_MAX_DIGITS; // 08x-xxx-xxxx
const LANDLINE_LENGTH = 9; // 076-xxx-xxx

/** เหลือเฉพาะตัวเลข และแปลงรูปแบบสากล (+66 81 234 5678) ให้เป็น 0812345678 */
export function normalizePhone(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.startsWith("66") && (digits.length === MOBILE_LENGTH + 1 || digits.length === LANDLINE_LENGTH + 1)) {
    return `0${digits.slice(2)}`;
  }
  return digits;
}

/** เบอร์มือถือ 10 หลัก หรือเบอร์บ้าน 9 หลัก และต้องขึ้นต้นด้วย 0 */
export function isValidPhone(value: string): boolean {
  const d = normalizePhone(value);
  return (d.length === MOBILE_LENGTH || d.length === LANDLINE_LENGTH) && d.startsWith("0");
}

/** จัดรูปแบบระหว่างพิมพ์ -> 081-234-5678 */
export function formatPhone(value: string): string {
  const d = normalizePhone(value).slice(0, MOBILE_LENGTH);
  return [d.slice(0, 3), d.slice(3, 6), d.slice(6)].filter(Boolean).join("-");
}
