import { ChevronRight, FileText } from "lucide-react";
import type { ReactNode } from "react";

import { StatusPill } from "@/components/common/StatusPill";
import { cn } from "@/lib/utils";
import type { DocumentStatus } from "@/types/enums";

/**
 * แถวเอกสาร 1 รายการ — ใช้ทั้งฝั่ง "ทำเองได้" (A01, A02...) และ
 * "ต้องไปขอก่อน" (B01, B02...) รหัสนำหน้าเสมอ เพื่อให้ผู้ใช้อ้างอิงกับเจ้าหน้าที่ได้
 */
type Props = {
  code: string;
  title: string;
  description?: string;
  status?: DocumentStatus;
  /** บังคับยื่น — M6 บล็อกการยื่นถ้ารายการที่ required ยังไม่ครบ */
  required?: boolean;
  /** เอกสารหมวด external: ระยะเวลาโดยประมาณ เช่น "30 – 45 วัน" (M4) */
  leadTime?: string;
  action?: ReactNode;
  onClickHref?: string;
  className?: string;
};

export function DocRow({
  code,
  title,
  description,
  status,
  required,
  leadTime,
  action,
  className,
}: Props) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-xl border border-line bg-surface p-3 transition-colors hover:border-brand-200",
        className,
      )}
    >
      <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-brand-50 text-sm font-bold text-brand-700">
        {code}
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium text-ink">{title}</p>
          {required && (
            <span className="rounded-full bg-danger-bg px-2 py-0.5 text-xs font-medium text-danger-fg">
              บังคับ
            </span>
          )}
          {status && <StatusPill status={status} />}
        </div>
        {description && <p className="mt-0.5 text-sm text-ink-muted">{description}</p>}
        {leadTime && (
          <p className="mt-0.5 flex items-center gap-1 text-sm text-ink-muted">
            <FileText className="size-3.5" aria-hidden />
            ใช้เวลาประมาณ {leadTime}
          </p>
        )}
      </div>

      {action ?? <ChevronRight className="size-5 shrink-0 text-ink-muted" aria-hidden />}
    </div>
  );
}
