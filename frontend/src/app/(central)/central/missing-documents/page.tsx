import type { Metadata } from "next";

import { MissingUploadsView } from "./MissingUploadsView";

export const metadata: Metadata = {
  title: "เอกสารที่ยังไม่ส่ง",
  description:
    "เอกสารฉบับไหนที่ผู้ประกอบการยังไม่ได้อัปโหลดเข้ามามากที่สุด เพื่อดูว่าผู้ยื่นติดขัดตรงไหน",
};

export default function CentralMissingDocumentsPage() {
  return <MissingUploadsView />;
}
