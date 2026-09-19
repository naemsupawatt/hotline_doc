import type { ReactNode } from "react";

import { AppNav } from "@/components/common/AppNav";

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <AppNav />
      {children}
    </>
  );
}
