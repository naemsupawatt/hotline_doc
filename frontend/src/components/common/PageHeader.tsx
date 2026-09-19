import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * หัวหน้าเพจ — สไตล์ของโปรเจกต์นี้คือ "หัวข้อเป็นคำถามที่พูดกับผู้ใช้"
 * เช่น "ที่พักของคุณต้องดำเนินการอะไร?" ไม่ใช่ "แบบฟอร์มประเมินประเภทที่พัก"
 */
type Props = {
  /** ตัวเล็กสีแบรนด์เหนือหัวข้อ เช่น "01 / ประเมินที่พัก" */
  eyebrow?: string;
  title: string;
  description?: string;
  aside?: ReactNode;
  className?: string;
};

export function PageHeader({ eyebrow, title, description, aside, className }: Props) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-4", className)}>
      <div className="min-w-0">
        {eyebrow && <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-brand-700"><span aria-hidden className="h-4 w-1 rounded-full bg-brand-500" />{eyebrow}</p>}
        <h1 className="text-2xl leading-snug font-bold tracking-tight text-ink sm:text-3xl xl:text-4xl">{title}</h1>
        {description && <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink-muted sm:text-base">{description}</p>}
      </div>
      {aside}
    </div>
  );
}
