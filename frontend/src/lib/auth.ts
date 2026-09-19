import { api } from "@/lib/api";
import type { UserRole } from "@/types/enums";

export type AuthUser = {
  id: number;
  full_name: string;
  email: string | null;
  phone: string | null;
  role: UserRole;
  is_verified: boolean;
};

type TokenResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

const TOKEN_KEY = "hotline.token";
const USER_KEY = "hotline.user";

/** M1: เข้าสู่ระบบด้วยอีเมลหรือเบอร์โทร */
export async function login(
  identifier: string,
  password: string,
  remember: boolean,
): Promise<AuthUser> {
  const res = await api<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ identifier, password }),
  });
  saveSession(res, remember);
  return res.user;
}

/**
 * "จดจำการเข้าสู่ระบบ" = localStorage (อยู่ข้ามการปิดเบราว์เซอร์)
 * ไม่จดจำ = sessionStorage (หายเมื่อปิดแท็บ)
 *
 * หมายเหตุด้านความปลอดภัย: การเก็บ JWT ใน storage เปิดช่องให้ XSS อ่านได้
 * ระบบจริงควรใช้ httpOnly cookie — ที่เลือกแบบนี้เพราะเป็นต้นแบบสำหรับสาธิต
 * และ backend ยังไม่มี refresh token flow
 */
function saveSession(res: TokenResponse, remember: boolean) {
  const store = remember ? window.localStorage : window.sessionStorage;
  store.setItem(TOKEN_KEY, res.access_token);
  store.setItem(USER_KEY, JSON.stringify(res.user));
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY) ?? window.sessionStorage.getItem(TOKEN_KEY);
}

export function getUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY) ?? window.sessionStorage.getItem(USER_KEY);
  return raw ? (JSON.parse(raw) as AuthUser) : null;
}

export function logout() {
  for (const store of [window.localStorage, window.sessionStorage]) {
    store.removeItem(TOKEN_KEY);
    store.removeItem(USER_KEY);
  }
}

/** ปลายทางหลังล็อกอิน แยกตามบทบาท (ข้อ 5 ของโจทย์) */
export function homeFor(role: UserRole): string {
  switch (role) {
    case "officer":
      return "/officer/queue";
    case "central":
      return "/central/overview";
    case "super_admin":
      return "/admin/settings";
    default:
      return "/operator/applications";
  }
}
