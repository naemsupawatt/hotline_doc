import type { NextConfig } from "next";

/** ปลายทางจริงของ backend — เปลี่ยนได้ด้วย API_PROXY_TARGET ใน .env.local
    ค่านี้ใช้ฝั่งเซิร์ฟเวอร์ของ Next เท่านั้น ไม่ถูกฝังลงโค้ดในเบราว์เซอร์ */
const API_TARGET = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  /* Next 16 บล็อก /_next/* จาก origin ที่ไม่ใช่ localhost ตอน dev
     ทำให้ JS ฝั่งเบราว์เซอร์ไม่ทำงานเมื่อเปิดผ่าน ngrok (ปุ่มกดแล้วเงียบ)
     รายการนี้จำเป็นเฉพาะตอนเดโมผ่าน tunnel เท่านั้น */
  allowedDevOrigins: ["*.ngrok-free.app", "*.ngrok.app", "*.ngrok.io"],

  /* ให้ /api/v1/* ของเว็บวิ่งต่อไปที่ backend ในเครื่อง
     เบราว์เซอร์จึงยิง API ที่ origin เดียวกับหน้าเว็บเสมอ — เปิดผ่าน ngrok
     ด้วย tunnel เดียวก็ใช้ได้ และไม่ต้องพึ่ง CORS เพราะไม่ใช่ cross-origin */
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${API_TARGET}/api/v1/:path*` }];
  },
};

export default nextConfig;
