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
    throw new ApiError(body?.detail ?? "ระบบขัดข้องชั่วคราว กรุณาลองใหม่อีกครั้ง", res.status);
  }

  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}
