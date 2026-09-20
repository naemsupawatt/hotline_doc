/**
 * ตัวเรียก API ตัวเดียวของทั้งแอป — ห้าม fetch() ตรงในคอมโพเนนต์
 * เพราะจะทำให้จัดการ token / base URL / error message กระจัดกระจาย
 */
/** ที่อยู่ API — ประกาศที่นี่ที่เดียว ที่อื่นต้อง import ไปใช้ ห้ามอ่าน env ซ้ำ */
export const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

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

/**
 * ยิงไม่ถึงเซิร์ฟเวอร์เลย — ต่างจาก "เซิร์ฟเวอร์ตอบว่าผิดพลาด"
 *
 * เคสนี้เจอบ่อยสองแบบ และเดิมทั้งคู่ขึ้นข้อความว่า "ตรวจสอบอินเทอร์เน็ต"
 * ซึ่งพาไปหาสาเหตุผิดทาง:
 *   1. ลืมเปิด backend ตอนพัฒนา
 *   2. เว็บถูก deploy ขึ้นโฮสต์ แต่ NEXT_PUBLIC_API_URL ยังชี้ localhost
 *
 * ผู้ใช้ทั่วไปเห็นข้อความกลาง ๆ ตาม NFR Usability
 * ส่วนคนพัฒนาเห็น URL ที่ยิงไปต่อท้าย เฉพาะตอนไม่ใช่ production
 */
const UNREACHABLE = 0;

function unreachableMessage(url: string): string {
  const base = "ขณะนี้ติดต่อระบบไม่ได้ กรุณาลองใหม่อีกครั้งในอีกสักครู่";
  if (process.env.NODE_ENV === "production") return base;
  return `${base} (ยิงไปที่ ${url} แล้วไม่มีการตอบกลับ — เซิร์ฟเวอร์ API เปิดอยู่หรือไม่)`;
}

export async function api<T>(path: string, init?: RequestInit & { token?: string }): Promise<T> {
  const { token, headers, ...rest } = init ?? {};
  const url = `${BASE}${path}`;

  // อัปโหลดไฟล์ส่งเป็น FormData ซึ่งเบราว์เซอร์ต้องเป็นคนตั้ง Content-Type เอง
  // เพราะต้องแนบ boundary ต่อท้าย ถ้าเราตั้งเป็น application/json ทับ เซิร์ฟเวอร์
  // จะแกะ multipart ไม่ออกและตอบ 422 โดยไม่บอกสาเหตุที่แท้จริง
  const isFormData = rest.body instanceof FormData;

  let res: Response;
  try {
    res = await fetch(url, {
      ...rest,
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
    });
  } catch {
    // fetch โยน TypeError เมื่อยิงไม่ถึงปลายทาง รวมถึงกรณีถูก CORS บล็อก
    throw new ApiError(unreachableMessage(url), UNREACHABLE);
  }

  if (!res.ok) {
    // NFR Usability: ต้องแสดงข้อความที่ผู้ใช้ทั่วไปเข้าใจ ไม่ใช่ raw error code
    const body = await res.json().catch(() => null);
    throw new ApiError(readDetail(body), res.status);
  }

  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}
