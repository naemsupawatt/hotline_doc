import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * การ์ดขาวหัวมีไอคอน — โครงที่ใช้ซ้ำแทบทุกหน้าในแบบหน้าจอ
 * กติกาของสไตล์นี้: ทุกหัวข้อต้องมีคำอธิบายสั้นใต้ชื่อเสมอ ห้ามมี label ลอย
 */
type Props = {
  icon?: LucideIcon;
  title: string;
  description?: string;
  /** แถบสีอ่อนหลังหัวการ์ด: ใช้ brand สำหรับหมวด "ทำเองได้" และ info สำหรับ "ต้องไปขอ" */
  tone?: "plain" | "brand" | "info";
  action?: ReactNode;
  children?: ReactNode;
  className?: string;
};

const TONE = {
  plain: "bg-surface",
  brand: "bg-brand-50/60",
  info: "bg-info-bg/50",
} as const;

export function SectionCard({
  icon: Icon,
  title,
  description,
  tone = "plain",
  action,
  children,
  className,
}: Props) {
  return (
    <section className={cn("overflow-hidden rounded-card border border-line bg-surface", className)}>
      <header className={cn("flex items-start gap-3 border-b border-line px-5 py-4", TONE[tone])}>
        {Icon && (
          <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-xl bg-surface text-brand-500">
            <Icon className="size-5" aria-hidden />
          </span>
        )}
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold text-ink">{title}</h2>
          {description && <p className="mt-0.5 text-sm text-ink-muted">{description}</p>}
        </div>
        {action}
      </header>
      {children && <div className="p-5">{children}</div>}
    </section>
  );
}
