import Image from "next/image";

import { cn } from "@/lib/utils";

const ART = {
  "hotel-garden": { width: 1200, height: 800 },
  "coastal-community": { width: 768, height: 512 },
  "hotel-sketch": { width: 768, height: 512 },
} as const;

export type IllustrationScene = keyof typeof ART;

/** ภาพตกแต่งเท่านั้น ข้อความและสถานะสำคัญต้องแสดงด้วย HTML ข้างภาพเสมอ */
export function Illustration({
  scene,
  sizes,
  className,
}: {
  scene: IllustrationScene;
  sizes: string;
  className?: string;
}) {
  return (
    <Image
      src={`/illustrations/${scene}.webp`}
      {...ART[scene]}
      alt=""
      aria-hidden="true"
      draggable={false}
      sizes={sizes}
      className={cn("pointer-events-none h-auto w-full select-none", className)}
    />
  );
}
