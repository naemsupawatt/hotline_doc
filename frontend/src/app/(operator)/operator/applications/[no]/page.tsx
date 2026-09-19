import type { Metadata } from "next";

import { ApplicationView } from "./ApplicationView";

export const metadata: Metadata = {
  title: "คำขอของฉัน",
  description: "ติดตามสถานะคำขอ และเตรียมเอกสารที่ต้องใช้",
};

/** params เป็น Promise ตั้งแต่ Next 15 — ต้อง await ก่อนใช้ */
export default async function ApplicationPage({ params }: { params: Promise<{ no: string }> }) {
  const { no } = await params;
  return <ApplicationView applicationNo={decodeURIComponent(no)} />;
}
