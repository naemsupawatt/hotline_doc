import type { Metadata } from "next";

import { FormView } from "./FormView";

export const metadata: Metadata = {
  title: "แบบฟอร์มของคำขอ",
  description: "แบบฟอร์มที่ระบบกรอกให้ ลงลายมือชื่อ แล้วพิมพ์หรือบันทึกเป็น PDF",
};

export default async function FormPage({
  params,
}: {
  params: Promise<{ no: string; code: string }>;
}) {
  const { no, code } = await params;
  return <FormView applicationNo={decodeURIComponent(no)} code={decodeURIComponent(code)} />;
}
