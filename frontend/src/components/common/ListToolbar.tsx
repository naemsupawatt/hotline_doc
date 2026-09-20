"use client";

import { Search, X } from "lucide-react";
import { useId } from "react";

import { applicationStatusLabel } from "@/components/common/StatusPill";
import type { ApplicationStatus } from "@/types/enums";

/**
 * ช่องสถานะเป็นตัวเลือก
 *
 * หน้าที่แบ่งกลุ่มด้วยแท็บอยู่แล้ว (เช่น คิวคำขอของเจ้าหน้าที่) ไม่ควรมีช่องนี้
 * เพราะกลายเป็นตัวกรองสองชั้นที่ทำงานคนละระดับ — แท็บเลือกว่าจะโหลดข้อมูล
 * กลุ่มไหน ส่วนช่องนี้กรองเฉพาะที่โหลดมาแล้ว ผู้ใช้จะงงว่าทำไมเลือกสถานะ
 * บางค่าแล้วไม่เจออะไรเลย
 */
type Props = {
  query: string;
  onQueryChange: (value: string) => void;
  count: number;
  total: number;
} & (
  | { status: string; onStatusChange: (value: string) => void; statuses: ApplicationStatus[] }
  | { status?: undefined; onStatusChange?: undefined; statuses?: undefined }
);

export function ListToolbar({
  query,
  onQueryChange,
  status,
  onStatusChange,
  statuses,
  count,
  total,
}: Props) {
  const id = useId();
  const showStatus = statuses !== undefined;
  return (
    <div className="mt-7 rounded-2xl border border-line bg-surface p-4 shadow-card">
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <label htmlFor={`${id}-search`} className="sr-only">
            ค้นหาชื่อที่พักหรือเลขคำขอ
          </label>
          <Search
            className="pointer-events-none absolute top-3.5 left-3 size-5 text-ink-muted"
            aria-hidden
          />
          <input
            id={`${id}-search`}
            type="search"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            placeholder="ค้นหาชื่อที่พักหรือเลขคำขอ"
            className="min-h-12 w-full rounded-xl border border-line bg-canvas py-3 pr-3 pl-10 text-sm"
          />
        </div>
        {showStatus && (
        <label className="flex items-center gap-3 text-sm text-ink-muted">
          <span className="shrink-0">สถานะ</span>
          <select
            value={status}
            onChange={(e) => onStatusChange?.(e.target.value)}
            className="min-h-12 min-w-0 flex-1 rounded-xl border border-line bg-surface px-3 text-ink sm:w-48"
          >
            <option value="">ทั้งหมด</option>
            {statuses?.map((value) => (
              <option key={value} value={value}>
                {applicationStatusLabel(value)}
              </option>
            ))}
          </select>
        </label>
        )}
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-ink-muted">
        <p role="status">
          แสดง {count.toLocaleString("th-TH")} จาก{" "}
          {total.toLocaleString("th-TH")} คำขอ
        </p>
        {(query || status) && (
          <button
            type="button"
            onClick={() => {
              onQueryChange("");
              onStatusChange?.("");
            }}
            className="flex min-h-9 items-center gap-1 text-brand-700"
          >
            <X className="size-3.5" aria-hidden />
            ล้างตัวกรอง
          </button>
        )}
      </div>
    </div>
  );
}
