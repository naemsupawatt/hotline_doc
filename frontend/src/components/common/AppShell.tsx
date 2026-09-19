import type { ReactNode } from "react";

import { AppNav } from "@/components/common/AppNav";

/** โครงพื้นที่ทำงานร่วมกันทุกบทบาท เมนูเลือกจากผู้ใช้ที่เข้าสู่ระบบ */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <>
      <AppNav />
      <div
        id="workspace-content"
        tabIndex={-1}
        className="workspace-content min-w-0 lg:pl-56 print:pl-0"
      >
        {children}
        <footer className="no-print mx-auto flex max-w-7xl flex-wrap justify-between gap-2 border-t border-line px-6 py-5 text-xs text-ink-muted">
          <span>HoTLinE Doc · ผู้ช่วยขออนุญาตที่พัก จังหวัดภูเก็ต</span>
          <span>ระบบต้นแบบเพื่อการสาธิต · ใช้ข้อมูลจำลองทั้งหมด</span>
        </footer>
      </div>
    </>
  );
}
