import type { Metadata } from "next";

import { LicenseView } from "./LicenseView";

export const metadata: Metadata = {
  title: "เอกสารอนุญาต",
  description: "ใบอนุญาตหรือหนังสือรับรองการแจ้ง สำหรับพิมพ์",
};

export default async function LicensePage({ params }: { params: Promise<{ no: string }> }) {
  const { no } = await params;
  return <LicenseView applicationNo={decodeURIComponent(no)} />;
}
