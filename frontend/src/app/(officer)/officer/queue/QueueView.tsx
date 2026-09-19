"use client";

import { ChevronRight, Clock, Inbox, MapPin } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Mascot } from "@/components/brand/Mascot";
import { PageHeader } from "@/components/common/PageHeader";
import { StatusPill } from "@/components/common/StatusPill";
import { ApiError } from "@/lib/api";
import { type QueueItem, officerQueue } from "@/lib/officer";
import type { ApplicationStatus } from "@/types/enums";

export function QueueView() {
  const [rows, setRows] = useState<QueueItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    officerQueue()
      .then(setRows)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "โหลดคิวคำขอไม่ได้ กรุณาลองใหม่"),
      );
  }, []);

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
      <PageHeader
        eyebrow="คิวคำขอ"
        title="คำขอที่รอคุณพิจารณา"
        description="แสดงเฉพาะคำขอในเขตที่คุณรับผิดชอบ เรียงคำขอที่ค้างนานที่สุดขึ้นก่อน"
      />

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
          <p className="mt-4 font-semibold text-ink">ยังไม่มีคำขอรอพิจารณา</p>
          <p className="mt-1 text-sm text-ink-muted">
            เมื่อมีผู้ประกอบการในเขตของคุณยื่นคำขอ รายการจะขึ้นที่นี่
          </p>
        </div>
      )}

      {rows && rows.length > 0 && (
        <ul className="mt-8 space-y-3">
          {rows.map((row) => (
            <li key={row.application_no}>
              <Link
                href={`/officer/applications/${row.application_no}`}
                className="flex items-center gap-4 rounded-card border border-line bg-surface p-4 transition-colors hover:border-brand-200"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm text-ink-muted">
                      {row.application_no}
                    </span>
                    <StatusPill kind="application" status={row.status as ApplicationStatus} />
                  </div>
                  <p className="mt-1 font-semibold text-ink">{row.property_name}</p>
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

                <ChevronRight className="size-5 shrink-0 text-ink-muted" aria-hidden />
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
