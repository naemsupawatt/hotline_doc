import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** รวม className แบบปลอดภัย (ใช้ร่วมกับ shadcn/ui ได้) */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** แปลงวันที่เป็นรูปแบบไทย พ.ศ. เช่น 12 มี.ค. 2568 */
export function formatThaiDate(value: string | Date): string {
  const d = typeof value === "string" ? new Date(value) : value;
  return new Intl.DateTimeFormat("th-TH", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(d);
}

/** M7: "รออยู่กี่วันแล้ว" — นับจากเวลาที่ระบบประทับ ไม่ใช่เวลาที่ผู้ใช้กรอก */
export function daysSince(value: string | Date): number {
  const d = typeof value === "string" ? new Date(value) : value;
  return Math.floor((Date.now() - d.getTime()) / 86_400_000);
}
