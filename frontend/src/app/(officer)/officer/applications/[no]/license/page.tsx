import type { Metadata } from "next";

import { LicenseView } from "@/components/common/LicenseView";

export const metadata: Metadata = {
  title: "เอกสารอนุญาต (เจ้าหน้าที่)",
  description: "ใบอนุญาตหรือหนังสือรับรองการแจ้งที่ออกให้คำขอนี้ สำหรับพิมพ์",
};

/**
 * เอกสารใบเดียวกับที่ผู้ยื่นเห็น เปิดจากฝั่งเจ้าหน้าที่
 *
 * เจ้าหน้าที่เป็นคนลงนามออกเอกสาร แต่เดิมหลังกดออกเอกสารแล้วเห็นแค่เลขที่
 * จึงไม่มีทางตรวจว่าใบที่ออกไปข้อความถูกต้องหรือพิมพ์ส่งมอบให้ผู้มาติดต่อได้
 */
export default async function OfficerLicensePage({ params }: { params: Promise<{ no: string }> }) {
  const { no } = await params;
  return <LicenseView applicationNo={decodeURIComponent(no)} viewer="officer" />;
}
