import type { Metadata } from "next";

import { OverviewView } from "./OverviewView";

export const metadata: Metadata = {
  title: "ภาพรวมทั้งจังหวัด",
  description: "สรุปคำขอทั้งจังหวัด แยกตามประเภท ท้องถิ่น และขั้นตอนที่ค้าง",
};

export default function CentralOverviewPage() {
  return <OverviewView />;
}
