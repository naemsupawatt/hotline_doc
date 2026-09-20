import { CheckCircle2, Clock, Landmark, UserRound, XCircle } from "lucide-react";

import {
  APPLICATION_STEPS,
  type ProgressActor,
  type ProgressTone,
  applicationProgress,
} from "@/lib/progress";
import { cn } from "@/lib/utils";
import type { ApplicationStatus } from "@/types/enums";

/**
 * M7 — แถบความคืบหน้าของคำขอหนึ่งใบ
 *
 * ตอบสามคำถามที่ผู้ยื่นถามบ่อยที่สุดในที่เดียว: ไปถึงขั้นไหนแล้ว เหลืออะไรอีก
 * ใครกำลังถือเรื่องอยู่ และค้างมากี่วัน ส่วนการ map สถานะ -> ขั้นตอน
 * อยู่ที่ lib/progress.ts ที่เดียว คอมโพเนนต์นี้รู้แค่วิธีวาด
 *
 * ใช้ Stepper.tsx ไม่ได้เพราะอันนั้นเป็นวงกลม 4 วงพร้อมป้ายกำกับ
 * เหมาะกับหน้าเดี่ยว แต่ในรายการที่มีหลายสิบแถวต้องการของที่เตี้ยกว่านี้
 */

/** สีของแต่ละโทน — ชื่อคลาสอยู่ที่นี่ที่เดียว lib/progress.ts ไม่รู้จักสี */
const TONE: Record<ProgressTone, { current: string; chip: string }> = {
  action:    { current: "bg-linear-to-r from-brand-500 to-brand-100", chip: "bg-brand-50 text-brand-700" },
  waiting:   { current: "bg-linear-to-r from-brand-500 to-brand-100", chip: "bg-info-bg text-info-fg" },
  attention: { current: "bg-linear-to-r from-warn-fg to-warn-bg",     chip: "bg-warn-bg text-warn-fg" },
  done:      { current: "bg-success-fg",                              chip: "bg-success-bg text-success-fg" },
  stopped:   { current: "bg-danger-fg",                               chip: "bg-danger-bg text-danger-fg" },
};

const ACTOR_ICON: Record<ProgressActor, typeof UserRound> = {
  operator: UserRound,
  officer: Landmark,
  none: CheckCircle2,
};

type Props = {
  status: ApplicationStatus;
  /** อยู่ในขั้นนี้มากี่วันแล้ว — นับจากเวลาที่สถานะเปลี่ยนล่าสุด ไม่ใช่วันที่สร้าง */
  daysWaiting: number;
  className?: string;
};

export function ProgressTrack({ status, daysWaiting, className }: Props) {
  const { stepIndex, actor, actorLabel, nextAction, tone, halted } = applicationProgress(status);
  const total = APPLICATION_STEPS.length;
  const finished = stepIndex >= total;
  const ActorIcon = halted ? XCircle : ACTOR_ICON[actor];

  return (
    <div className={className}>
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 text-xs">
        <p className="font-medium text-ink">
          {finished
            ? `ครบทั้ง ${total} ขั้นตอนแล้ว`
            : `${halted ? "หยุดที่" : ""}ขั้นที่ ${stepIndex + 1} จาก ${total}`}
          {/* จอเล็กไม่มีที่พอโชว์ป้ายใต้แถบ จึงยกชื่อขั้นปัจจุบันมาไว้บรรทัดนี้แทน */}
          {!finished && <span className="font-normal text-ink-muted sm:hidden"> · {APPLICATION_STEPS[stepIndex]}</span>}
        </p>
        <p className="flex items-center gap-1 text-ink-muted">
          <Clock className="size-3.5" aria-hidden />
          อยู่ในขั้นนี้ {daysWaiting.toLocaleString("th-TH")} วัน
        </p>
      </div>

      <ol className="mt-2 flex gap-1.5" aria-label="ความคืบหน้าของคำขอ">
        {APPLICATION_STEPS.map((label, i) => {
          const done = i < stepIndex;
          const current = i === stepIndex;
          return (
            <li key={label} className="min-w-0 flex-1">
              <span
                className={cn(
                  "block h-1.5 rounded-full",
                  done && (tone === "done" ? "bg-success-fg" : "bg-brand-500"),
                  current && TONE[tone].current,
                  !done && !current && "bg-line",
                )}
                aria-hidden
              />
              {/* NFR Accessibility: แถบสีล้วนไม่สื่อความหมายกับ screen reader */}
              <span className="sr-only">
                ขั้นที่ {i + 1} {label}:{" "}
                {done ? "ผ่านแล้ว" : current ? (halted ? "หยุดที่ขั้นนี้" : "กำลังดำเนินการ") : "ยังไม่ถึง"}
              </span>
              <span
                className={cn(
                  "mt-1.5 hidden truncate text-[11px] sm:block",
                  current ? "font-medium text-ink" : "text-ink-muted",
                )}
                aria-hidden
              >
                {label}
              </span>
            </li>
          );
        })}
      </ol>

      <p className="mt-2.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
        <span
          className={cn(
            "inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 font-medium",
            TONE[tone].chip,
          )}
        >
          <ActorIcon className="size-3.5" aria-hidden />
          {actorLabel}
        </span>
        <span className="text-ink-muted">{nextAction}</span>
      </p>
    </div>
  );
}
