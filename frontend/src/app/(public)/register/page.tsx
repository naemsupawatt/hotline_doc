import type { Metadata } from "next";

import { RegisterView } from "./RegisterView";

export const metadata: Metadata = {
  title: "สมัครสมาชิก",
  description: "สมัครสมาชิก HoTLinE Doc เพื่อเริ่มยื่นขอใบอนุญาตที่พักแรมออนไลน์",
};

export default function RegisterPage() {
  return <RegisterView />;
}
