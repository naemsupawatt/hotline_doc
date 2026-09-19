import type { Metadata } from "next";

import { MyApplicationsView } from "./MyApplicationsView";

export const metadata: Metadata = {
  title: "คำขอของฉัน",
  description: "ติดตามสถานะคำขอทั้งหมดของคุณ",
};

export default function MyApplicationsPage() {
  return <MyApplicationsView />;
}
