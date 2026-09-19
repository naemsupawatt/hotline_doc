import { AlertTriangle, Sparkles, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * กล่อง "AI ช่วยตรวจเบื้องต้น" (S1) — เช่น ภาพเบลออ่านไม่ออก (T-07)
 *
 * หลักที่ถือไว้: ผลจาก AI เป็นเพียงการเตือนก่อนยื่น ไม่ใช่คำตัดสิน
 * ข้อความจึงต้องบอกเสมอว่าไม่ใช่ผลอนุมัติ เพื่อไม่ให้ผู้ใช้เข้าใจผิด
 */
type Props = {
  level?: "info" | "warn" | "error";
  title: string;
  description?: string;
  /** รูปย่อของไฟล์ที่ตรวจพบปัญหา */
  thumbnail?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
};

const TONE = {
  info: { box: "bg-info-bg/60 border-info-fg/20", fg: "text-info-fg", Icon: Sparkles },
  warn: { box: "bg-warn-bg border-warn-fg/25", fg: "text-warn-fg", Icon: AlertTriangle },
  error: { box: "bg-danger-bg border-danger-fg/25", fg: "text-danger-fg", Icon: XCircle },
} as const;

export function AiNotice({ level = "warn", title, description, thumbnail, action, className }: Props) {
  const { box, fg, Icon } = TONE[level];
  return (
    <div className={cn("flex gap-3 rounded-xl border p-3", box, className)} role="status">
      {thumbnail ?? <Icon className={cn("mt-0.5 size-5 shrink-0", fg)} aria-hidden />}
      <div className="min-w-0 flex-1">
        <p className={cn("font-medium", fg)}>{title}</p>
        {description && <p className="mt-0.5 text-sm text-ink-muted">{description}</p>}
        {action && <div className="mt-2">{action}</div>}
      </div>
    </div>
  );
}
