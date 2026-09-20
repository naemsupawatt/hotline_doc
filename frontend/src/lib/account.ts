/**
 * บัญชีของฉัน — ดูและแก้ข้อมูลของผู้ใช้ที่เข้าสู่ระบบอยู่
 *
 * ชนิดข้อมูลต้องตรงกับ ProfileOut ใน backend/app/schemas/auth.py
 *
 * ทุก endpoint ในไฟล์นี้ทำงานกับ "เจ้าของโทเคน" เสมอ ไม่มีที่ไหนรับ id ของผู้ใช้
 * เป็นพารามิเตอร์ จึงไม่มีทางแก้ข้อมูลของคนอื่นได้แม้จะแก้คำขอที่ยิงออกไป
 */
import { api } from "@/lib/api";
import { getToken, saveUser } from "@/lib/auth";
import type { UserRole } from "@/types/enums";

export type Profile = {
  id: number;
  full_name: string;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  role: UserRole;
  /** เลขบัตรแบบปิดบัง — ระบบไม่เคยส่งเลขเต็มออกมาให้หน้าจอ */
  national_id_masked: string | null;
  created_at: string;
  /** อปท. ที่เจ้าหน้าที่คนนี้รับผิดชอบ (T-09) บทบาทอื่นเป็นรายการว่าง */
  local_authorities: string[];
};

export type ProfileInput = {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
};

function authed() {
  const token = getToken();
  return token ? { token } : {};
}

export function getProfile() {
  return api<Profile>("/auth/me", authed());
}

/** แก้แล้วต้องอัปเดตผู้ใช้ที่เก็บไว้ด้วย ไม่งั้นชื่อบนแถบเมนูจะไม่ตรงกับที่เพิ่งบันทึก */
export async function updateProfile(input: ProfileInput): Promise<Profile> {
  const profile = await api<Profile>("/auth/me", {
    method: "PATCH",
    body: JSON.stringify(input),
    ...authed(),
  });

  saveUser({
    id: profile.id,
    full_name: profile.full_name,
    email: profile.email,
    phone: profile.phone,
    role: profile.role,
    national_id_masked: profile.national_id_masked,
  });

  return profile;
}

/** ต้องกรอกรหัสเดิมเสมอ — โทเคนที่ถูกขโมยไปจะได้ยึดบัญชีไม่ได้ */
export function changePassword(current_password: string, new_password: string) {
  return api<void>("/auth/me/password", {
    method: "POST",
    body: JSON.stringify({ current_password, new_password }),
    ...authed(),
  });
}
