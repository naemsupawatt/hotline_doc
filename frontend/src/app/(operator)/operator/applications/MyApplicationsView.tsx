"use client";

import { ChevronRight, Plus } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Mascot } from "@/components/brand/Mascot";
import { ListToolbar } from "@/components/common/ListToolbar";
import { PageHeader } from "@/components/common/PageHeader";
import { PROGRESS_ACCENT, ProgressTrack } from "@/components/common/ProgressTrack";
import { StatusPill } from "@/components/common/StatusPill";
import { ApiError } from "@/lib/api";
import { type ApplicationSummary, myApplications } from "@/lib/applications";
import { type ProgressActor, applicationProgress } from "@/lib/progress";
import { cn } from "@/lib/utils";
import type { ApplicationStatus } from "@/types/enums";

/**
 * M7 — ผู้ยื่นต้องรู้ว่าคำขออยู่ขั้นตอนใดและรอมากี่วันแล้ว
 *
 * แบ่งกลุ่มด้วย "ลูกบอลอยู่ในมือใคร" แบบเดียวกับแท็บคิวของเจ้าหน้าที่
 * (frontend/src/app/(officer)/README.md) แต่มองจากฝั่งผู้ยื่น คำถามแรกของคน
 * ที่เปิดหน้านี้คือ "มีอะไรที่ฉันต้องทำไหม" ไม่ใช่ "คำขอนี้สถานะชื่ออะไร"
 * การจัดกลุ่มจึงตอบคำถามนั้นก่อน แล้วค่อยบอกสถานะเป็นรายละเอียด
 *
 * กลุ่มคำนวณจาก actor ใน lib/progress.ts ไม่ได้ไล่เช็กชื่อสถานะเองที่นี่
 * เพิ่มสถานะใหม่ในอนาคตจึงไม่ต้องกลับมาแก้หน้านี้
 */
type Group = "action" | "waiting" | "settled";

const GROUP_OF: Record<ProgressActor, Group> = {
  operator: "action",
  officer: "waiting",
  none: "settled",
};

const TABS: { key: Group | "all"; label: string }[] = [
  { key: "action", label: "ต้องทำต่อ" },
  { key: "waiting", label: "รอเจ้าหน้าที่" },
  { key: "settled", label: "จบแล้ว" },
  { key: "all", label: "ทั้งหมด" },
];

const EMPTY_TEXT: Record<Group | "all", { title: string; hint: string }> = {
  action: {
    title: "ไม่มีคำขอที่รอคุณทำอะไร",
    hint: "ทุกคำขออยู่ที่เจ้าหน้าที่หรือจบแล้ว ถ้าถูกส่งกลับมาให้แก้ รายการจะขึ้นที่นี่",
  },
  waiting: {
    title: "ยังไม่มีคำขอที่รอเจ้าหน้าที่",
    hint: "คำขอที่ยื่นไปแล้วจะมารออยู่ที่นี่จนกว่าเจ้าหน้าที่จะพิจารณาเสร็จ",
  },
  settled: {
    title: "ยังไม่มีคำขอที่จบแล้ว",
    hint: "คำขอที่ได้รับเอกสารแล้วหรือไม่ผ่านการพิจารณา จะย้ายมาอยู่ที่นี่",
  },
  all: {
    title: "ไม่พบคำขอที่ตรงกับการค้นหา",
    hint: "ลองเปลี่ยนคำค้น หรือดูแท็บอื่น",
  },
};

function groupOf(row: ApplicationSummary): Group {
  return GROUP_OF[applicationProgress(row.status as ApplicationStatus).actor];
}

export function MyApplicationsView() {
  const [rows, setRows] = useState<ApplicationSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Group | "all">("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    myApplications()
      .then(setRows)
      .catch((err) => setError(err instanceof ApiError ? err.message : "โหลดรายการคำขอไม่ได้"));
  }, []);

  const counts = useMemo(() => {
    const tally: Record<Group | "all", number> = {
      action: 0,
      waiting: 0,
      settled: 0,
      all: rows?.length ?? 0,
    };
    for (const row of rows ?? []) tally[groupOf(row)] += 1;
    return tally;
  }, [rows]);

  const visibleRows = useMemo(() => {
    const keyword = query.trim().toLocaleLowerCase("th-TH");
    return (rows ?? []).filter(
      (row) =>
        (tab === "all" || groupOf(row) === tab) &&
        `${row.property_name} ${row.application_no}`.toLocaleLowerCase("th-TH").includes(keyword),
    );
  }, [rows, tab, query]);

  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 sm:py-12">
      <PageHeader
        eyebrow="คำขอของฉัน"
        illustration="hotel-sketch"
        title="ติดตามคำขอของคุณ"
        description="ดูว่าแต่ละคำขออยู่ขั้นตอนใด ใครกำลังถือเรื่องอยู่ และรอมากี่วันแล้ว"
        aside={
          <Link
            href="/operator/wizard"
            className="inline-flex min-h-12 items-center gap-2 rounded-xl border-2 border-brand-500 px-5 py-3 font-semibold text-brand-600 hover:bg-brand-50"
          >
            <Plus className="size-5" aria-hidden />
            ประเมินที่พักใหม่
          </Link>
        }
      />

      {error && (
        <p
          role="alert"
          className="mt-6 rounded-xl bg-danger-bg px-4 py-3 text-sm font-medium text-danger-fg"
        >
          {error}
        </p>
      )}

      {rows === null && !error && <p className="mt-8 text-ink-muted">กำลังโหลด…</p>}

      {rows?.length === 0 && (
        <div className="mt-8 flex flex-col items-center rounded-card border border-dashed border-line bg-brand-50/30 p-10 text-center">
          <Mascot pose="wave" size="md" className="w-40" />
          <p className="mt-4 font-semibold text-ink">ยังไม่มีคำขอ</p>
          <p className="mt-1 max-w-sm text-sm text-ink-muted">
            เริ่มจากประเมินที่พักของคุณ ระบบจะบอกว่าต้องใช้เอกสารอะไรบ้าง
          </p>
          <Link
            href="/operator/wizard"
            className="mt-5 inline-flex min-h-12 items-center rounded-xl bg-brand-500 px-5 py-3 font-semibold text-white hover:bg-brand-400"
          >
            เริ่มประเมินที่พัก
          </Link>
        </div>
      )}

      {rows && rows.length > 0 && (
        <>
          {/* แท็บพร้อมจำนวน — เห็นตั้งแต่ยังไม่กดว่ามีอะไรค้างอยู่ฝั่งเราบ้าง */}
          <div
            role="tablist"
            aria-label="กลุ่มคำขอ"
            className="mt-6 flex flex-wrap gap-2 border-b border-line"
          >
            {TABS.map((item) => (
              <button
                key={item.key}
                type="button"
                role="tab"
                aria-selected={tab === item.key}
                onClick={() => setTab(item.key)}
                className={cn(
                  "-mb-px inline-flex min-h-11 items-center gap-2 border-b-2 px-4 text-sm font-semibold transition-colors",
                  tab === item.key
                    ? "border-brand-500 text-brand-700"
                    : "border-transparent text-ink-muted hover:text-ink",
                )}
              >
                {item.label}
                <span
                  className={cn(
                    "rounded-full px-2 py-0.5 text-xs font-semibold",
                    tab === item.key ? "bg-brand-100 text-brand-700" : "bg-canvas text-ink-muted",
                  )}
                >
                  {counts[item.key].toLocaleString("th-TH")}
                </span>
              </button>
            ))}
          </div>

          <ListToolbar
            query={query}
            onQueryChange={setQuery}
            count={visibleRows.length}
            total={rows.length}
          />
        </>
      )}

      {rows && rows.length > 0 && visibleRows.length === 0 && (
        <div className="mt-5 rounded-2xl border border-dashed border-line bg-surface px-5 py-10 text-center">
          <p className="font-semibold text-ink">
            {query ? EMPTY_TEXT.all.title : EMPTY_TEXT[tab].title}
          </p>
          <p className="mt-2 text-sm text-ink-muted">
            {query ? EMPTY_TEXT.all.hint : EMPTY_TEXT[tab].hint}
          </p>
        </div>
      )}

      {visibleRows.length > 0 && (
        <ul className="mt-5 space-y-3">
          {visibleRows.map((row) => (
            <ApplicationCard key={row.application_no} row={row} />
          ))}
        </ul>
      )}
    </main>
  );
}

/**
 * การ์ดหนึ่งใบ = คำขอหนึ่งคำขอ
 *
 * ลำดับที่ตาไล่: ชื่อที่พัก (สิ่งที่ผู้ใช้จำได้) -> สถานะ -> ความคืบหน้า
 * เลขคำขอถูกลดชั้นลงมาอยู่บรรทัดรอง เพราะเป็นสิ่งที่ใช้ตอน "อ้างอิง"
 * ไม่ใช่ตอน "มองหา" — คนจำชื่อที่พักของตัวเองได้ แต่ไม่มีใครจำเลขคำขอ
 *
 * แถบสีด้านซ้ายทำให้กวาดตาทีเดียวรู้ว่าใบไหนต้องรีบ โดยไม่ต้องอ่านทีละใบ
 * (สีไม่ได้สื่อความหมายลำพัง — มีป้ายสถานะและป้ายผู้รับผิดชอบเป็นข้อความกำกับ)
 */
function ApplicationCard({ row }: { row: ApplicationSummary }) {
  const status = row.status as ApplicationStatus;
  const { tone } = applicationProgress(status);

  return (
    <li>
      <Link
        href={`/operator/applications/${row.application_no}`}
        className="group relative block overflow-hidden rounded-card border border-line bg-surface shadow-card transition-all hover:border-brand-200 hover:shadow-lift"
      >
        <span className={cn("absolute inset-y-0 left-0 w-1.5", PROGRESS_ACCENT[tone])} aria-hidden />

        <div className="p-4 pl-5 sm:p-5 sm:pl-6">
          <div className="flex items-start gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
                <h3 className="text-xl font-bold break-words text-ink group-hover:text-brand-700 sm:text-2xl">
                  {row.property_name}
                </h3>
                <StatusPill kind="application" status={status} size="md" />
              </div>
              <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-ink-muted">
                <span>{row.property_type_name}</span>
                <span aria-hidden>·</span>
                <span className="font-mono text-sm">{row.application_no}</span>
              </p>
            </div>
            <ChevronRight
              className="mt-1.5 size-6 shrink-0 text-ink-muted transition-colors group-hover:text-brand-600"
              aria-hidden
            />
          </div>

          {/* M7: แถบความคืบหน้าตอบว่าเหลือขั้นตอนอะไร ใครถือเรื่อง และค้างมากี่วัน */}
          <ProgressTrack status={status} daysWaiting={row.days_waiting} className="mt-4" />
        </div>
      </Link>
    </li>
  );
}
