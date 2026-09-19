import { api } from "@/lib/api";
import type { UserRole } from "@/types/enums";

export type AuthUser = {
  id: number;
  full_name: string;
  email: string | null;
  phone: string | null;
  role: UserRole;
  national_id_masked: string | null;
};

type TokenResponse = {
  access_token: string;
  token_type: string;
  user: AuthUser;
};

const TOKEN_KEY = "hotline.token";
const USER_KEY = "hotline.user";

export type RegisterInput = {
  first_name: string;
  last_name: string;
  national_id: string;
  phone: string;
  email: string;
  password: string;
};

/** M1: สมัครสมาชิก — สมัครเสร็จเข้าใช้งานได้ทันที */
export async function register(input: RegisterInput, remember = true): Promise<AuthUser> {
  const res = await api<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(input),
  });
  saveSession(res, remember);
  return res.user;
}

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
      return "/operator/wizard";
  }
}

/**
 * หน้าปลายทางของบทบาทนั้นถูกสร้างแล้วหรือยัง
 *
 * ระหว่างที่ยังทำไม่ครบทุกบทบาท ต้องเช็กก่อน redirect ไม่งั้นผู้ใช้จะเจอ 404
 * ทันทีหลังล็อกอินสำเร็จ ซึ่งแย่กว่าการค้างที่หน้าจอ "สำเร็จ"
 *
 * พอสร้างหน้าของบทบาทใดเสร็จ ให้เพิ่มบทบาทนั้นเข้ามาในชุดนี้
 */
const ROLES_WITH_HOME: ReadonlySet<UserRole> = new Set<UserRole>(["operator"]);

export function hasHome(role: UserRole): boolean {
  return ROLES_WITH_HOME.has(role);
}
