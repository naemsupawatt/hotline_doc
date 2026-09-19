/**
 * ตัวเรียก API ตัวเดียวของทั้งแอป — ห้าม fetch() ตรงในคอมโพเนนต์
 * เพราะจะทำให้จัดการ token / base URL / error message กระจัดกระจาย
 */
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

/**
 * ดึงข้อความผิดพลาดออกจาก response
 *
 * FastAPI คืน detail สองแบบ: ข้อความเดียว (HTTPException) หรือ
 * อาร์เรย์ของ validation error (422) — ต้องรองรับทั้งคู่
 * ไม่งั้นหน้าเว็บจะโชว์ "[object Object]" ให้ผู้ใช้เห็น
 */
function readDetail(body: unknown): string {
  const fallback = "ระบบขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้ง";
  if (!body || typeof body !== "object") return fallback;

  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;

  if (Array.isArray(detail) && detail.length > 0) {
    const msg = (detail[0] as { msg?: unknown }).msg;
    // Pydantic เติม "Value error, " นำหน้าข้อความจาก field_validator
    if (typeof msg === "string") return msg.replace(/^Value error, /, "");
  }
  return fallback;
}

export async function api<T>(path: string, init?: RequestInit & { token?: string }): Promise<T> {
  const { token, headers, ...rest } = init ?? {};
  const res = await fetch(`${BASE}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!res.ok) {
    // NFR Usability: ต้องแสดงข้อความที่ผู้ใช้ทั่วไปเข้าใจ ไม่ใช่ raw error code
    const body = await res.json().catch(() => null);
    throw new ApiError(readDetail(body), res.status);
  }

  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}
