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
        {eyebrow && <p className="text-sm font-medium text-brand-600">{eyebrow}</p>}
        <h1 className="mt-1 text-3xl font-bold tracking-tight text-ink sm:text-4xl">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-ink-muted">{description}</p>}
      </div>
      {aside}
    </div>
  );
}
