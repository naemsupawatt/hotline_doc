import type { Metadata } from "next";

import { SettingsView } from "./SettingsView";

export const metadata: Metadata = {
  title: "ตั้งค่าเกณฑ์",
  description: "แก้เงื่อนไขจำแนกประเภทและอัตราค่าธรรมเนียมโดยไม่ต้องแก้โปรแกรม",
};

export default function AdminSettingsPage() {
  return <SettingsView />;
}
