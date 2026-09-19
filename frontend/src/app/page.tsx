import { redirect } from "next/navigation";

/**
 * หน้าแรกของระบบคือหน้าเข้าสู่ระบบ (M1)
 *
 * หน้าตรวจสอบระบบดีไซน์ย้ายไปอยู่ที่ /scaffold แล้ว — ยังเก็บไว้เพราะใช้ดู
 * ได้เร็วว่า token / คอมโพเนนต์กลาง / สถานะทั้ง 7 แบบยังแสดงถูกต้องอยู่หรือไม่
 */
export default function RootPage() {
  redirect("/login");
}
