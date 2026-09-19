import { Check } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * ใช้ 2 ที่: wizard ประเมินที่พัก (3 ขั้น) และหน้าติดตามคำขอ (4 ขั้น M7)
 * ในหน้าติดตาม ให้ส่ง note ของขั้นปัจจุบันเป็น "อยู่ในขั้นนี้ 2 วัน"
 */
export type Step = { label: string; note?: string };

type Props = {
  steps: Step[];
  /** ดัชนีขั้นปัจจุบัน เริ่มที่ 0 */
  current: number;
  className?: string;
};

export function Stepper({ steps, current, className }: Props) {
  return (
    <ol className={cn("flex w-full items-start", className)}>
      {steps.map((step, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={step.label} className="flex flex-1 items-start last:flex-none">
            <div className="flex flex-col items-center gap-2 px-1 text-center">
              <span
                className={cn(
                  "grid size-8 shrink-0 place-items-center rounded-full border-2 text-sm font-semibold",
                  done && "border-brand-500 bg-brand-500 text-white",
                  active && "border-brand-500 bg-white text-brand-600",
                  !done && !active && "border-line bg-white text-ink-muted",
                )}
                aria-current={active ? "step" : undefined}
              >
                {done ? <Check className="size-4" aria-hidden /> : i + 1}
              </span>
              <span className="min-w-0">
                <span
                  className={cn(
                    "block text-sm font-medium",
                    active ? "text-brand-600" : done ? "text-ink" : "text-ink-muted",
                  )}
                >
                  {step.label}
                </span>
                {step.note && <span className="block text-xs text-ink-muted">{step.note}</span>}
              </span>
            </div>
            {i < steps.length - 1 && (
              <span
                className={cn("mt-4 h-0.5 flex-1 rounded", done ? "bg-brand-500" : "bg-line")}
                aria-hidden
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
