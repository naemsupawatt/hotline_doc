import Image from "next/image";

import { cn } from "@/lib/utils";

/** ท่าทางมาสคอต — แมปกับสถานะของระบบ ไม่ใช่เลือกตามความสวย */
export type MascotPose =
  | "wave"     // ต้อนรับ / หน้าแรก / empty state ทั่วไป
  | "upload"   // ยังไม่มีไฟล์ / กำลังอัปโหลด (M5)
  | "inspect"  // ระบบหรือเจ้าหน้าที่กำลังตรวจ / ผลค้นหาว่าง (M8, S1)
  | "waiting"  // รอดำเนินการ / คำขอค้าง (M7)
  | "success"  // ยื่นสำเร็จ / อนุมัติ / ออกใบอนุญาต (M6, M10)
  | "support"; // ช่วยเหลือ / FAQ / ติดต่อเจ้าหน้าที่ / หน้า error

const SIZES = { sm: 80, md: 160, lg: 240 } as const;

/** ไฟล์ที่มีจริงใน /public/mascot คือ 160 / 320 / 640 */
function srcFor(pose: MascotPose, size: keyof typeof SIZES) {
  const file = size === "lg" ? 640 : size === "md" ? 320 : 160;
  return `/mascot/${pose}-${file}.webp`;
}

type Props = {
  pose: MascotPose;
  size?: keyof typeof SIZES;
  /** ข้อความอธิบาย — เว้นว่างไว้เมื่อข้างๆ มีข้อความอยู่แล้ว (decorative) */
  alt?: string;
  className?: string;
  priority?: boolean;
};

export function Mascot({ pose, size = "md", alt = "", className, priority }: Props) {
  const px = SIZES[size];
  return (
    <Image
      src={srcFor(pose, size)}
      width={px}
      height={px}
      alt={alt}
      priority={priority}
      aria-hidden={alt === "" || undefined}
      className={cn("h-auto select-none", className)}
    />
  );
}
