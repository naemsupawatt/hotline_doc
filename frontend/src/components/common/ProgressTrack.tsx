import { Check, Clock, Landmark, UserRound, X } from "lucide-react";
import { Fragment } from "react";

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
 * วาดเป็นหมุดกลมต่อด้วยเส้น ไม่ใช่แถบสี่ท่อนแยกกัน เพราะหมุดที่ติ๊กถูกแล้ว
 * อ่านออกทันทีว่า "ผ่านไปกี่ขั้น" โดยไม่ต้องนับ และเป็นภาษาภาพเดียวกับ
 * Stepper.tsx ที่ wizard ใช้อยู่ — ผู้ใช้คนเดียวกันเห็นสองหน้านี้ต่อกัน
 *
 * ไม่เรียก Stepper.tsx มาใช้ตรง ๆ เพราะอันนั้นสูงกว่านี้ (หมุด 40px + ป้ายสองบรรทัด)
 * เหมาะกับหน้าเดี่ยวที่มีอันเดียว ส่วนที่นี่อยู่ในรายการที่มีหลายสิบใบ
 * และต้องมีหัวแถว เปอร์เซ็นต์ และป้ายผู้รับผิดชอบซึ่ง Stepper ไม่มี
 */

/**
 * สีของแต่ละโทน — ชื่อคลาสอยู่ที่นี่ที่เดียว lib/progress.ts ไม่รู้จักสี
 *
 * panel = พื้นหลังแผง, node = หมุดที่ผ่านแล้ว/ขั้นปัจจุบัน, chip = ป้ายผู้รับผิดชอบ
 */
const TONE: Record<ProgressTone, { panel: string; node: string; ring: string; chip: string; accent: string }> = {
  action: {
    panel: "bg-brand-50",
    node: "bg-brand-500 text-white",
    ring: "ring-brand-100",
    chip: "bg-white text-brand-700",
    accent: "text-brand-700",
  },
  waiting: {
    panel: "bg-info-bg/50",
    node: "bg-info-fg text-white",
    ring: "ring-info-bg",
    chip: "bg-white text-info-fg",
    accent: "text-info-fg",
  },
  attention: {
    panel: "bg-warn-bg/60",
    node: "bg-warn-fg text-white",
    ring: "ring-warn-bg",
    chip: "bg-white text-warn-fg",
    accent: "text-warn-fg",
  },
  done: {
    panel: "bg-success-bg/60",
    node: "bg-success-fg text-white",
    ring: "ring-success-bg",
    chip: "bg-white text-success-fg",
    accent: "text-success-fg",
  },
  stopped: {
    panel: "bg-danger-bg/50",
    node: "bg-danger-fg text-white",
    ring: "ring-danger-bg",
    chip: "bg-white text-danger-fg",
    accent: "text-danger-fg",
  },
};

/** สีแถบด้านซ้ายของการ์ดในรายการคำขอ — ใช้ชุดเดียวกับแผงนี้ จึงอยู่ไฟล์เดียวกัน */
export const PROGRESS_ACCENT: Record<ProgressTone, string> = {
  action: "bg-brand-500",
  waiting: "bg-info-fg",
  attention: "bg-warn-fg",
  done: "bg-success-fg",
  stopped: "bg-danger-fg",
};

const ACTOR_ICON: Record<ProgressActor, typeof UserRound> = {
  operator: UserRound,
  officer: Landmark,
  none: Check,
};

type Props = {
  status: ApplicationStatus;
  /** อยู่ในขั้นนี้มากี่วันแล้ว — นับจากเวลาที่สถานะเปลี่ยนล่าสุด ไม่ใช่วันที่สร้าง */
  daysWaiting: number;
  className?: string;
};

/**
 * ข้อความเวลา — "อยู่ในขั้นนี้ 0 วัน" อ่านแล้วสะดุดทุกครั้งที่เพิ่งเปลี่ยนสถานะ
 * และคำขอที่จบแล้วก็ไม่ได้ "อยู่ใน" ขั้นไหนอีก จึงแยกคำตามสถานการณ์
 */
function elapsedLabel(days: number, settled: boolean, halted: boolean): string {
  const count = days.toLocaleString("th-TH");
  if (settled) {
    if (days === 0) return halted ? "ปิดเรื่องวันนี้" : "เสร็จวันนี้";
    return halted ? `ปิดเรื่องเมื่อ ${count} วันก่อน` : `เสร็จเมื่อ ${count} วันก่อน`;
  }
  return days === 0 ? "เข้าสู่ขั้นนี้วันนี้" : `อยู่ในขั้นนี้ ${count} วัน`;
}

export function ProgressTrack({ status, daysWaiting, className }: Props) {
  const { stepIndex, actor, actorLabel, nextAction, tone, halted } = applicationProgress(status);
  const total = APPLICATION_STEPS.length;
  const finished = stepIndex >= total;
  const last = total - 1;
  const ActorIcon = halted ? X : ACTOR_ICON[actor];
  const percent = Math.round((Math.min(stepIndex, total) / total) * 100);
  const palette = TONE[tone];

  // ขั้นที่ผ่านไปแล้วใช้สีของ "ความสำเร็จ" เสมอ ไม่ใช่สีของโทนปัจจุบัน —
  // คำขอที่ถูกปฏิเสธที่ขั้น 3 ก็ยัง "ยื่นสำเร็จ" มาแล้วจริง ๆ สองขั้น
  // ถ้าย้อมหมุดเหล่านั้นเป็นสีแดงตามโทน จะอ่านเหมือนว่าทุกขั้นล้มเหลว
  const doneNode = tone === "done" ? "bg-success-fg text-white" : "bg-brand-500 text-white";
  const doneBar = tone === "done" ? "bg-success-fg" : "bg-brand-500";

  return (
    <div className={cn("rounded-2xl p-4 sm:p-5", palette.panel, className)}>
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
        <p className="text-sm font-bold text-ink">
          {finished
            ? `ครบทั้ง ${total} ขั้นตอนแล้ว`
            : `${halted ? "หยุดที่" : ""}ขั้นที่ ${stepIndex + 1} จาก ${total}`}
          {/* จอเล็กไม่มีที่พอโชว์ป้ายใต้หมุด จึงยกชื่อขั้นปัจจุบันมาไว้บรรทัดนี้แทน */}
          {!finished && (
            <span className="font-normal text-ink-muted sm:hidden"> · {APPLICATION_STEPS[stepIndex]}</span>
          )}
        </p>

        <p className="flex items-center gap-2 text-xs text-ink-muted">
          <span className="flex items-center gap-1">
            <Clock className="size-3.5" aria-hidden />
            {elapsedLabel(daysWaiting, actor === "none", halted)}
          </span>
          {/* คำขอที่ถูกปฏิเสธไม่แสดงเปอร์เซ็นต์ เพราะตัวเลขที่เดินไปครึ่งทาง
              จะอ่านเหมือนว่ายังไปต่อได้ ทั้งที่เรื่องจบแล้ว */}
          {!halted && (
            <>
              <span className="text-line" aria-hidden>
                |
              </span>
              <span className={cn("text-sm font-bold", palette.accent)}>{percent}%</span>
            </>
          )}
        </p>
      </div>

      {/* ป้ายชื่อขั้นวางไว้ "ใต้หมุดของตัวเอง" ด้วยตำแหน่งสัมบูรณ์ ไม่ใช่แถวแยก
          ที่แบ่งความกว้างเท่า ๆ กัน เพราะหมุดหัวท้ายชิดขอบส่วนหมุดกลางเว้นระยะ
          คนละจังหวะ ป้ายที่แบ่งเท่ากันจึงเยื้องจากหมุดเสมอ (pb เผื่อที่ให้ป้าย) */}
      <ol className="mt-3 flex items-center sm:pb-7" aria-label="ความคืบหน้าของคำขอ">
        {APPLICATION_STEPS.map((label, i) => {
          const done = i < stepIndex;
          const current = i === stepIndex;
          return (
            <Fragment key={label}>
              {i > 0 && (
                <li
                  aria-hidden
                  className={cn("h-1.5 flex-1 rounded-full", i <= stepIndex ? doneBar : "bg-white")}
                />
              )}
              <li className="relative shrink-0">
                <span
                  className={cn(
                    "grid size-8 place-items-center rounded-full text-xs font-bold sm:size-9",
                    done && doneNode,
                    current && cn(palette.node, "ring-4", palette.ring),
                    !done && !current && "bg-white text-ink-muted ring-1 ring-line",
                  )}
                  aria-current={current ? "step" : undefined}
                >
                  {done ? (
                    <Check className="size-4 sm:size-4.5" aria-hidden />
                  ) : current && halted ? (
                    <X className="size-4 sm:size-4.5" aria-hidden />
                  ) : (
                    i + 1
                  )}
                </span>
                {/* NFR Accessibility: หมุดสีล้วนไม่สื่อความหมายกับ screen reader */}
                <span className="sr-only">
                  ขั้นที่ {i + 1} {label}:{" "}
                  {done
                    ? "ผ่านแล้ว"
                    : current
                      ? halted
                        ? "หยุดที่ขั้นนี้"
                        : "กำลังดำเนินการ"
                      : "ยังไม่ถึง"}
                </span>
                {/* ซ่อนบนจอเล็ก — สี่ป้ายภาษาไทยเรียงกันอ่านไม่ออกที่ความกว้างมือถือ
                    ชื่อขั้นปัจจุบันไปโผล่บนหัวแถวแทน */}
                <span
                  aria-hidden
                  className={cn(
                    "absolute top-full mt-1.5 hidden whitespace-nowrap text-xs sm:block",
                    i === 0 && "left-0",
                    i === last && "right-0",
                    i !== 0 && i !== last && "left-1/2 -translate-x-1/2",
                    current ? "font-semibold text-ink" : "text-ink-muted",
                  )}
                >
                  {label}
                </span>
              </li>
            </Fragment>
          );
        })}
      </ol>

      <p className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1.5 text-sm">
        <span
          className={cn(
            "inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold",
            palette.chip,
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
