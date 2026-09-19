import Image from "next/image";
import Link from "next/link";

import { cn } from "@/lib/utils";

type Props = {
  /** lockup = มาสคอต+ชื่อ (navbar desktop) | mark = มาสคอตอย่างเดียว (mobile/sidebar) */
  variant?: "lockup" | "mark" | "wordmark";
  href?: string;
  className?: string;
};

const SRC = {
  lockup: { src: "/brand/logo-lockup-640.webp", w: 320, h: 109 },
  mark: { src: "/brand/logo-mark-128.webp", w: 40, h: 41 },
  wordmark: { src: "/brand/logo-wordmark-480.webp", w: 240, h: 66 },
} as const;

export function Logo({ variant = "lockup", href = "/", className }: Props) {
  const { src, w, h } = SRC[variant];
  const img = (
    <Image src={src} width={w} height={h} alt="HoTLinE Doc" priority className={cn("h-auto", className)} />
  );
  return href ? (
    <Link href={href} className="inline-flex items-center" aria-label="HoTLinE Doc หน้าแรก">
      {img}
    </Link>
  ) : (
    img
  );
}

/**
 * แบดจ์ "ต้นแบบ • ข้อมูลจำลอง" ที่วางข้างโลโก้ทุกหน้า
 * โจทย์ข้อ 14 กำหนดว่าห้ามใช้ข้อมูลส่วนบุคคลจริง — แบดจ์นี้ประกาศเรื่องนั้นให้ชัด
 */
export function PrototypeBadge({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700",
        className,
      )}
    >
      ต้นแบบ • ข้อมูลจำลอง
    </span>
  );
}
