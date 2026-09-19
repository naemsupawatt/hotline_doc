"use client";

import { ChevronRight, Clock, Plus } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Mascot } from "@/components/brand/Mascot";
import { PageHeader } from "@/components/common/PageHeader";
import { StatusPill } from "@/components/common/StatusPill";
import { ApiError } from "@/lib/api";
import { type ApplicationSummary, myApplications } from "@/lib/applications";
import type { ApplicationStatus } from "@/types/enums";

/** M7 — ผู้ยื่นต้องรู้ว่าคำขออยู่ขั้นตอนใดและรอมากี่วันแล้ว */
export function MyApplicationsView() {
  const [rows, setRows] = useState<ApplicationSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    myApplications()
      .then(setRows)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "โหลดรายการคำขอไม่ได้"),
      );
  }, []);

  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-8 sm:px-6 sm:py-12">
      <PageHeader
        eyebrow="คำขอของฉัน"
        title="ติดตามคำขอของคุณ"
        description="ดูว่าแต่ละคำขออยู่ขั้นตอนใด และรออยู่กี่วันแล้ว"
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
        <ul className="mt-8 space-y-3">
          {rows.map((row) => (
            <li key={row.application_no}>
              <Link
                href={`/operator/applications/${row.application_no}`}
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
                  <p className="mt-0.5 text-sm text-ink-muted">{row.property_type_name}</p>
                </div>
                <p className="flex shrink-0 items-center gap-1 text-sm text-ink-muted">
                  <Clock className="size-3.5" aria-hidden />
                  {row.days_waiting} วัน
                </p>
                <ChevronRight className="size-5 shrink-0 text-ink-muted" aria-hidden />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
