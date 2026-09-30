import type { Metadata } from "next";

import { DocumentBottlenecksView } from "./DocumentBottlenecksView";

export const metadata: Metadata = {
  title: "เอกสารที่ค้างตรวจ",
  description:
    "เอกสารฉบับไหนเป็นคอขวดของทั้งจังหวัด และค้างอยู่ที่ท้องถิ่นใดบ้าง เพื่อใช้วางแผนแก้ปัญหาเชิงระบบ",
};

export default function CentralDocumentsPage() {
  return <DocumentBottlenecksView />;
}
