import type { ReactNode } from "react";

import { AppShell } from "@/components/common/AppShell";
import { ChatAssistant } from "@/components/common/ChatAssistant";

/**
 * ผู้ช่วยตอบคำถามอยู่ที่ layout ของกลุ่มนี้ ไม่ใช่รายหน้า
 * เพราะคำถามมักเกิดตอนกำลังทำอย่างอื่นค้างอยู่ ต้องถามได้จากทุกหน้า
 * และประวัติการคุยจะไม่หายเมื่อเปลี่ยนหน้าในกลุ่มเดียวกัน
 */
export default function Layout({ children }: { children: ReactNode }) {
  return (
    <AppShell>
      {children}
      <ChatAssistant />
    </AppShell>
  );
}
