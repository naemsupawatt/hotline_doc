import type { ReactNode } from "react";

import { AppShell } from "@/components/common/AppShell";

/**
 * กลุ่มนี้มีหน้าเดียวคือ "บัญชีของฉัน" ซึ่งทุกบทบาทใช้ร่วมกัน
 * จึงไม่ได้อยู่ใต้กลุ่มของบทบาทใดบทบาทหนึ่ง แต่ยังใช้ AppShell เดียวกัน
 * เมนูด้านข้างจึงเปลี่ยนตามบทบาทของคนที่เปิดเหมือนหน้าอื่น
 */
export default function Layout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
