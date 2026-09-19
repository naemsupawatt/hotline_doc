import { z } from "zod";

import { isValidThaiId, normalizeThaiId } from "@/lib/thaiId";

const MAX_AGE_YEARS = 120;

/**
 * เงื่อนไขต้องตรงกับ backend/app/schemas/auth.py
 * ตรวจฝั่งนี้เพื่อให้ผู้ใช้รู้ผลทันที ไม่ใช่เพื่อแทนการตรวจฝั่งเซิร์ฟเวอร์
 *
 * ข้อความทุกบรรทัดเขียนให้ผู้ใช้ทั่วไปเข้าใจ ไม่ใช่ศัพท์เทคนิค (NFR Usability)
 */
export const registerSchema = z
  .object({
    first_name: z
      .string()
      .trim()
      .min(1, "กรุณากรอกชื่อ")
      .max(80, "ชื่อยาวเกินไป")
      .refine((v) => !/\d/.test(v), "ชื่อต้องไม่มีตัวเลข"),
    last_name: z
      .string()
      .trim()
      .min(1, "กรุณากรอกนามสกุล")
      .max(80, "นามสกุลยาวเกินไป")
      .refine((v) => !/\d/.test(v), "นามสกุลต้องไม่มีตัวเลข"),
    national_id: z
      .string()
      .min(1, "กรุณากรอกเลขประจำตัวประชาชน")
      .refine((v) => normalizeThaiId(v).length === 13, "เลขประจำตัวประชาชนต้องมี 13 หลัก")
      .refine(isValidThaiId, "เลขประจำตัวประชาชนไม่ถูกต้อง กรุณาตรวจสอบตัวเลขอีกครั้ง"),
    birth_date: z
      .string()
      .min(1, "กรุณาเลือกวันเดือนปีเกิด")
      .refine((v) => new Date(v) < new Date(), "วันเดือนปีเกิดต้องเป็นวันที่ผ่านมาแล้ว")
      .refine((v) => {
        const years = (Date.now() - new Date(v).getTime()) / (365.25 * 86_400_000);
        return years <= MAX_AGE_YEARS;
      }, "วันเดือนปีเกิดไม่ถูกต้อง กรุณาตรวจสอบปีเกิดอีกครั้ง"),
    email: z
      .string()
      .trim()
      .min(1, "กรุณากรอกอีเมล")
      .regex(/^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$/, "รูปแบบอีเมลไม่ถูกต้อง เช่น name@example.com"),
    password: z.string().min(8, "รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร").max(128, "รหัสผ่านยาวเกินไป"),
    confirm_password: z.string().min(1, "กรุณากรอกรหัสผ่านอีกครั้ง"),
  })
  .refine((d) => d.password === d.confirm_password, {
    message: "รหัสผ่านทั้งสองช่องไม่ตรงกัน",
    path: ["confirm_password"],
  });

export type RegisterForm = z.infer<typeof registerSchema>;
