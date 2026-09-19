import type { ReactNode } from "react";

import { AppShell } from "@/components/common/AppShell";

export default function Layout({ children }: { children: ReactNode }) {
  return <AppShell>{children}</AppShell>;
}
