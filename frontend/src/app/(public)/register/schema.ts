import { z } from "zod";

import { isValidPhone, normalizePhone } from "@/lib/phone";
import { isValidThaiId, normalizeThaiId } from "@/lib/thaiId";

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
    phone: z
      .string()
      .min(1, "กรุณากรอกหมายเลขโทรศัพท์")
      .refine(
        (v) => normalizePhone(v).length >= 9,
        "หมายเลขโทรศัพท์สั้นเกินไป กรุณากรอกให้ครบ",
      )
      .refine(
        isValidPhone,
        "หมายเลขโทรศัพท์ไม่ถูกต้อง กรุณากรอกเบอร์มือถือ 10 หลัก เช่น 0812345678",
      ),
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
