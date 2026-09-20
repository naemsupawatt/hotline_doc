import type { Metadata } from "next";

import { AccountView } from "./AccountView";

export const metadata: Metadata = {
  title: "บัญชีของฉัน",
  description: "ดูและแก้ข้อมูลบัญชีผู้ใช้ และเปลี่ยนรหัสผ่าน",
};

export default function AccountPage() {
  return <AccountView />;
}
