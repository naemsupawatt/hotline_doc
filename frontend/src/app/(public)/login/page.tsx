import type { Metadata } from "next";

import { LoginView } from "./LoginView";

export const metadata: Metadata = {
  title: "เข้าสู่ระบบ",
  description: "เข้าสู่ระบบ HoTLinE Doc เพื่อจัดการคำขอใบอนุญาตที่พักของคุณ",
};

export default function LoginPage() {
  return <LoginView />;
}
