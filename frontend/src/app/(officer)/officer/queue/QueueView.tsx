"use client";

import { ChevronRight, Clock, Inbox, MapPin } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Mascot } from "@/components/brand/Mascot";
import { ListToolbar } from "@/components/common/ListToolbar";
import { PageHeader } from "@/components/common/PageHeader";
import { StatusPill } from "@/components/common/StatusPill";
import { ApiError } from "@/lib/api";
import { type QueueItem, type QueueScope, officerQueue } from "@/lib/officer";
import type { ApplicationStatus } from "@/types/enums";

/**
 * แท็บเลือกว่าจะดึงคำขอกลุ่มไหนมา — คนละเรื่องกับ ListToolbar ที่กรองเฉพาะ
 * ข้อมูลที่โหลดมาแล้ว
 *
 * "รอดำเนินการ" รวมคำขอที่อนุมัติแล้วแต่ยังไม่ออกเอกสารด้วย เพราะยังค้างงาน
 * อยู่หนึ่งขั้น ถ้าไม่รวม พออนุมัติปุ๊บคำขอจะหายจากคิว แล้วเจ้าหน้าที่จะกด
 * "ออกใบอนุญาต" ไม่ได้อีกเลย (M10 เข้าไม่ถึงผ่านหน้าจอ)
 */
const TABS: { scope: QueueScope; label: string }[] = [
  { scope: "open", label: "รอฉันดำเนินการ" },
  { scope: "revision", label: "รอผู้ยื่นแก้ไข" },
  { scope: "closed", label: "จบแล้ว" },
  { scope: "all", label: "ทั้งหมด" },
];

const EMPTY_TEXT: Record<QueueScope, { title: string; hint: string }> = {
  open: {
    title: "ยังไม่มีคำขอรอคุณดำเนินการ",
    hint: "เมื่อมีผู้ประกอบการในเขตของคุณยื่นคำขอ รายการจะขึ้นที่นี่",
  },
  revision: {
    title: "ไม่มีคำขอที่รอผู้ยื่นแก้ไข",
    hint: "คำขอที่คุณส่งกลับให้แก้ไขจะมารออยู่ที่นี่จนกว่าผู้ยื่นจะส่งกลับมา",
  },
  closed: {
    title: "ยังไม่มีคำขอที่จบแล้ว",
    hint: "คำขอที่ออกเอกสารหรือไม่อนุมัติแล้วจะย้ายมาอยู่ที่นี่",
  },
  all: {
    title: "ยังไม่มีคำขอในเขตของคุณ",
    hint: "เมื่อมีผู้ประกอบการในเขตของคุณยื่นคำขอ รายการจะขึ้นที่นี่",
  },
};

export function QueueView() {
  const [scope, setScope] = useState<QueueScope>("open");
  const [rows, setRows] = useState<QueueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ไม่มีช่องกรองสถานะที่นี่ เพราะแท็บด้านบนทำหน้าที่นั้นแล้ว
  // เหลือเฉพาะการค้นหาด้วยชื่อที่พักหรือเลขคำขอ
  const [query, setQuery] = useState("");
  const keyword = query.trim().toLocaleLowerCase("th-TH");
  const visibleRows = rows?.filter((row) =>
    `${row.property_name} ${row.application_no}`.toLocaleLowerCase("th-TH").includes(keyword),
  );

  // ล้างผลเก่าตอนผู้ใช้กดสลับแท็บ ไม่ทำใน effect เพราะเป็นผลจากการกด ไม่ใช่การ sync
  function changeScope(next: QueueScope) {
    if (next === scope) return;
    setScope(next);
    setRows(null);
    setError(null);
    setQuery("");
  }

  useEffect(() => {
    let cancelled = false;
    officerQueue(scope)
      .then((data) => {
        if (!cancelled) setRows(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "โหลดคิวคำขอไม่ได้ กรุณาลองใหม่");
        }
      });
    // กันผลของคำขอเก่ามาทับผลใหม่ เวลาผู้ใช้กดสลับแท็บเร็ว ๆ
    return () => {
      cancelled = true;
    };
  }, [scope]);

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
      <PageHeader
        eyebrow="คิวคำขอ"
        illustration="hotel-sketch"
        title="คำขอที่รอคุณพิจารณา"
        description="แสดงเฉพาะคำขอในเขตที่คุณรับผิดชอบ เรียงคำขอที่ค้างนานที่สุดขึ้นก่อน คำขอที่อนุมัติแล้วยังอยู่ในคิวจนกว่าจะออกเอกสาร"
      />

      <div
        role="tablist"
        aria-label="กลุ่มคำขอ"
        className="mt-6 flex flex-wrap gap-2 border-b border-line"
      >
        {TABS.map((tab) => (
          <button
            key={tab.scope}
            type="button"
            role="tab"
            aria-selected={scope === tab.scope}
            onClick={() => changeScope(tab.scope)}
            className={`-mb-px min-h-11 border-b-2 px-4 text-sm font-semibold transition-colors ${
              scope === tab.scope
                ? "border-brand-500 text-brand-700"
                : "border-transparent text-ink-muted hover:text-ink"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <p
          role="alert"
          className="mt-6 rounded-xl bg-danger-bg px-4 py-3 text-sm font-medium text-danger-fg"
        >
          {error}
        </p>
      )}

      {rows === null && !error && <p className="mt-8 text-ink-muted">กำลังโหลดคิวคำขอ…</p>}

      {rows?.length === 0 && (
        <div className="mt-8 flex flex-col items-center rounded-card border border-dashed border-line bg-brand-50/30 p-10 text-center">
          <Mascot pose="inspect" size="md" className="w-40" />
          <p className="mt-4 font-semibold text-ink">{EMPTY_TEXT[scope].title}</p>
          <p className="mt-1 text-sm text-ink-muted">{EMPTY_TEXT[scope].hint}</p>
        </div>
      )}

      {rows && rows.length > 0 && (
        <ListToolbar
          query={query}
          onQueryChange={setQuery}
          count={visibleRows?.length ?? 0}
          total={rows.length}
        />
      )}
      {rows && rows.length > 0 && visibleRows?.length === 0 && (
        <div className="mt-5 rounded-2xl border border-dashed border-line bg-surface px-5 py-10 text-center">
          <p className="font-semibold">ไม่พบคำขอที่ตรงกับการค้นหา</p>
          <p className="mt-2 text-sm text-ink-muted">ลองเปลี่ยนคำค้นหรือเลือกสถานะอื่น</p>
        </div>
      )}
      {visibleRows && visibleRows.length > 0 && (
        <ul className="mt-5 space-y-3">
          {visibleRows.map((row) => (
            <li key={row.application_no}>
              <Link
                href={`/officer/applications/${row.application_no}`}
                className="group flex flex-wrap items-center gap-3 rounded-card border border-line bg-surface p-4 shadow-card transition-all hover:border-brand-200 hover:shadow-lift sm:gap-4 sm:p-5"
              >
                <div className="min-w-0 basis-full sm:flex-1 sm:basis-auto">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm text-ink-muted">
                      {row.application_no}
                    </span>
                    <StatusPill kind="application" status={row.status as ApplicationStatus} />
                  </div>
                  <p className="mt-2 text-lg font-semibold break-words text-ink group-hover:text-brand-700">{row.property_name}</p>
                  <p className="mt-0.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-muted">
                    <span className="flex items-center gap-1">
                      <MapPin className="size-3.5" aria-hidden />
                      {row.local_authority_name}
                    </span>
                    <span>{row.property_type_name}</span>
                  </p>
                </div>

                {/* คำขอค้างนานคือปัญหาที่โจทย์ยกมาโดยตรง จึงเน้นให้เห็นชัด */}
                <div className="shrink-0 text-right">
                  <p
                    className={`flex items-center justify-end gap-1 text-sm font-semibold ${
                      row.days_waiting >= 7 ? "text-danger-fg" : "text-ink-muted"
                    }`}
                  >
                    <Clock className="size-3.5" aria-hidden />
                    รอ {row.days_waiting} วัน
                  </p>
                </div>

                <ChevronRight className="ml-auto size-5 shrink-0 text-brand-600" aria-hidden />
              </Link>
            </li>
          ))}
        </ul>
      )}

      {rows && rows.length > 0 && (
        <p className="mt-6 flex items-center gap-2 text-sm text-ink-muted">
          <Inbox className="size-4 shrink-0" aria-hidden />
          คำขอของท้องถิ่นอื่นจะไม่ปรากฏในคิวนี้ และเปิดดูไม่ได้
        </p>
      )}
    </main>
  );
}
