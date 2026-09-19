import type { Metadata } from "next";

import { QueueView } from "./QueueView";

export const metadata: Metadata = {
  title: "คิวคำขอ",
  description: "คำขอที่รอการพิจารณาในเขตที่รับผิดชอบ",
};

export default function OfficerQueuePage() {
  return <QueueView />;
}
