import type { Metadata } from "next";

import { SystemFormView } from "@/components/common/SystemFormView";

export const metadata: Metadata = {
  title: "แบบฟอร์มของคำขอ (เจ้าหน้าที่)",
  description: "หนังสือที่ผู้ยื่นลงลายมือชื่อแล้ว สำหรับเจ้าหน้าที่ตรวจก่อนตัดสิน",
};

/**
 * หน้ากระดาษฉบับเดียวกับที่ผู้ยื่นเห็น แต่เปิดแบบอ่านอย่างเดียว
 *
 * มีหน้านี้เพราะไฟล์แนบของแบบฟอร์มที่ระบบกรอกให้คือรูปลายเซ็นเพียงอย่างเดียว
 * เจ้าหน้าที่ที่ต้องตัดสินว่าเอกสารผ่านหรือไม่ผ่านจึงเคยเห็นแค่รูปลายเซ็นลอย ๆ
 * ซึ่งบอกไม่ได้ว่าเซ็นกำกับข้อความอะไรไว้
 */
export default async function OfficerFormPage({
  params,
}: {
  params: Promise<{ no: string; code: string }>;
}) {
  const { no, code } = await params;
  return (
    <SystemFormView
      applicationNo={decodeURIComponent(no)}
      code={decodeURIComponent(code)}
      viewer="officer"
    />
  );
}
