import type { Metadata, Viewport } from "next";
import { IBM_Plex_Sans_Thai } from "next/font/google";

import "./globals.css";

const thai = IBM_Plex_Sans_Thai({
  subsets: ["thai", "latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-thai",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "HoTLinE Doc — ผู้ช่วยขออนุญาตโรงแรมออนไลน์",
    template: "%s | HoTLinE Doc",
  },
  description:
    "ระบบยื่นขอใบอนุญาตประกอบธุรกิจโรงแรมและที่พักแรมแบบออนไลน์ จังหวัดภูเก็ต — ต้นแบบสำหรับการสาธิต ใช้ข้อมูลจำลองทั้งหมด",
};

// NFR: ต้องใช้งานบนหน้าจอเล็กได้จริง และผู้ใช้ต้องซูมได้ (ห้ามใส่ maximumScale=1)
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="th" className={thai.variable}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
