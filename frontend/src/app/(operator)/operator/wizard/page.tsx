import type { Metadata } from "next";

import { WizardView } from "./WizardView";

export const metadata: Metadata = {
  title: "ประเมินที่พัก",
  description:
    "ตอบคำถามไม่กี่ข้อ แล้วรู้ทันทีว่าที่พักของคุณต้องขอใบอนุญาตหรือไม่ ต้องใช้เอกสารอะไร และต้องไปติดต่อที่ไหน",
};

export default function WizardPage() {
  return <WizardView />;
}
