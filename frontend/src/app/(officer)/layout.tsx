import type { ReactNode } from "react";

import { AppNav } from "@/components/common/AppNav";

/** ทุกหน้าในกลุ่มนี้ใช้แถบนำทางเดียวกัน เมนูเปลี่ยนตามบทบาทของผู้ใช้เอง */
export default function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <AppNav />
      {children}
    </>
  );
}
