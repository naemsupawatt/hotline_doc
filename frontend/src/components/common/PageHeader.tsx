import type { ReactNode } from "react";

import { Illustration } from "@/components/brand/Illustration";
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
  illustration?: "hotel-sketch" | "coastal-community";
  className?: string;
};

export function PageHeader({
  eyebrow,
  title,
  description,
  aside,
  illustration,
  className,
}: Props) {
  return (
    <div
      className={cn(
        "relative",
        illustration &&
          "overflow-hidden rounded-2xl border border-line bg-surface p-5 shadow-card sm:p-7",
        className,
      )}
    >
      <div
        className={cn(
          "relative z-10 flex flex-wrap items-end justify-between gap-4",
          illustration && "xl:pr-52",
        )}
      >
        <div className="min-w-0">
          {eyebrow && (
            <p className="mb-3 flex items-center gap-2 text-sm font-semibold text-brand-700">
              <span aria-hidden className="h-4 w-1 rounded-full bg-brand-500" />
              {eyebrow}
            </p>
          )}
          <h1 className="text-2xl leading-snug font-bold tracking-tight text-ink sm:text-3xl xl:text-4xl">
            {title}
          </h1>
          {description && (
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-ink-muted sm:text-base">
              {description}
            </p>
          )}
        </div>
        {aside}
      </div>
      {illustration && (
        <div className="pointer-events-none absolute top-1/2 right-2 hidden w-52 -translate-y-1/2 xl:block print:hidden">
          <Illustration scene={illustration} sizes="208px" />
        </div>
      )}
    </div>
  );
}
