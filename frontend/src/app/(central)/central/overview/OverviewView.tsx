"use client";

import { CheckCircle2, ClipboardList, Clock, PencilLine } from "lucide-react";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { StatusPill } from "@/components/common/StatusPill";
import { ApiError } from "@/lib/api";
import { type AuthorityRow, type Bucket, type Overview, getOverview } from "@/lib/reports";
import type { ApplicationStatus } from "@/types/enums";

/**
 * M11 — ภาพรวมทั้งจังหวัด
 *
 * ตอบปัญหาข้อสุดท้ายที่โจทย์ยกมาโดยตรง: "ส่วนกลางไม่มีข้อมูลภาพรวมว่าคำขอ
 * ทั้งจังหวัดติดขัดที่ขั้นตอนใดมากที่สุด จึงแก้ปัญหาเชิงระบบได้ยาก"
 *
 * หน้านี้ดูได้อย่างเดียว ไม่มีปุ่มที่เปลี่ยนผลพิจารณารายคำขอ และไม่แสดง
 * ชื่อผู้ยื่นหรือเลขที่คำขอ ตามข้อกำหนดในตารางข้อ 5 ของโจทย์
 */
export function OverviewView() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOverview()
      .then(setData)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "โหลดรายงานไม่ได้ กรุณาลองใหม่"),
      );
  }, []);

  if (error) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-ink">เปิดรายงานไม่ได้</h1>
        <p role="alert" className="mt-2 text-ink-muted">
          {error}
        </p>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center text-ink-muted">
        กำลังโหลดรายงาน…
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <PageHeader
        eyebrow="ภาพรวมส่วนกลาง"
        illustration="coastal-community"
        title="เห็นปัญหา เพื่อปรับปรุงบริการ"
        description="สรุปสถานการณ์คำขอจากทุกพื้นที่ในจังหวัดภูเก็ต เพื่อให้เห็นว่าติดขัดที่ขั้นตอนใด"
      />

      {/* ตัวเลขนำ 4 ตัว — แยก "ค้างที่เจ้าหน้าที่" กับ "ค้างที่ผู้ยื่น" ออกจากกัน
          เพราะสองอย่างนี้นำไปสู่การแก้ปัญหาคนละแบบ */}
      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat icon={ClipboardList} label="คำขอทั้งหมด" value={data.total} tone="brand" />
        <Stat icon={Clock} label="รอเจ้าหน้าที่ตรวจ" value={data.waiting_on_officer} tone="info" />
        <Stat
          icon={PencilLine}
          label="รอผู้ยื่นแก้ไข"
          value={data.waiting_on_applicant}
          tone="warn"
        />
        <Stat icon={CheckCircle2} label="ดำเนินการเสร็จ" value={data.finished} tone="success" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <SectionCard
          title="แยกตามประเภทที่พัก"
          description="นับจากผลจำแนกที่บันทึกไว้ตอนเปิดคำขอแต่ละใบ"
        >
          <BarList rows={data.by_property_type} />
        </SectionCard>

        <SectionCard
          title="คำขอค้างอยู่ที่ขั้นตอนใด"
          description="ขั้นตอนที่มีคำขอกองอยู่มากที่สุดคือจุดที่ควรเข้าไปแก้ก่อน"
        >
          <ul className="space-y-2">
            {data.by_status.map((row) => (
              <li key={row.key} className="flex items-center gap-3">
                <StatusPill kind="application" status={row.key as ApplicationStatus} />
                <span className="ml-auto text-lg font-bold text-ink">{row.count}</span>
                <span className="text-sm text-ink-muted">รายการ</span>
              </li>
            ))}
          </ul>
        </SectionCard>
      </div>

      <SectionCard
        className="mt-6"
        title="พื้นที่ที่ควรติดตาม"
        description="เรียงจากพื้นที่ที่มีคำขอค้างมากที่สุด"
      >
        <AuthorityTable rows={data.by_authority} />
      </SectionCard>

      <p className="mt-6 text-sm text-ink-muted">
        หน้านี้แสดงเฉพาะข้อมูลสรุป ไม่แสดงชื่อผู้ยื่นหรือเลขที่คำขอรายใบ
        และไม่มีปุ่มที่เปลี่ยนผลพิจารณา
      </p>
    </main>
  );
}

const TONE = {
  brand: "border-brand-100 bg-brand-50 text-brand-700",
  info: "border-info-fg/15 bg-info-bg/60 text-info-fg",
  warn: "border-warn-fg/15 bg-warn-bg/60 text-warn-fg",
  success: "border-success-fg/15 bg-success-bg/60 text-success-fg",
} as const;

function Stat({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: typeof Clock;
  label: string;
  value: number;
  tone: keyof typeof TONE;
}) {
  return (
    <div className={`flex items-center gap-4 rounded-card border p-5 shadow-card ${TONE[tone]}`}>
      <span className="grid size-12 shrink-0 place-items-center rounded-full bg-surface/80">
        <Icon className="size-6" aria-hidden />
      </span>
      <div className="min-w-0">
        <p className="text-sm text-ink-muted">{label}</p>
        <p className="mt-1 text-3xl font-bold tabular-nums text-ink">
          {value.toLocaleString("th-TH")}
          <span className="ml-1 text-sm font-normal text-ink-muted">รายการ</span>
        </p>
      </div>
    </div>
  );
}

/**
 * แท่งเปรียบเทียบขนาด — สีเดียวทั้งชุด
 *
 * เป็นการวัด "ปริมาณ" ของหมวดที่ไม่ได้แข่งกันเชิงตัวตน จึงใช้สีเดียว
 * ถ้าไล่สีต่างกันรายแท่ง สีจะกลายเป็นข้อมูลปลอมที่ไม่ได้สื่ออะไร
 * ตัวเลขกำกับทุกแท่ง จึงอ่านได้โดยไม่ต้องพึ่งความยาวแท่งหรือสี
 */
function BarList({ rows }: { rows: Bucket[] }) {
  const max = Math.max(...rows.map((r) => r.count), 1);

  return (
    <ul className="space-y-3">
      {rows.map((row) => (
        <li key={row.key}>
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-sm text-ink">{row.label}</span>
            <span className="text-sm font-bold text-ink">{row.count}</span>
          </div>
          <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-line">
            <div
              className="h-full rounded-full bg-brand-500"
              style={{ width: `${(row.count / max) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

function AuthorityTable({ rows }: { rows: AuthorityRow[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[40rem] text-sm">
        <thead className="bg-info-bg/50">
          <tr className="border-b border-line text-left text-ink-muted">
            <th scope="col" className="px-3 py-3 font-medium">
              พื้นที่
            </th>
            <th scope="col" className="px-3 py-3 text-right font-medium">
              ทั้งหมด
            </th>
            <th scope="col" className="px-3 py-3 text-right font-medium">
              รอเจ้าหน้าที่
            </th>
            <th scope="col" className="px-3 py-3 text-right font-medium">
              รอผู้ยื่น
            </th>
            <th scope="col" className="px-3 py-3 text-right font-medium">
              เสร็จแล้ว
            </th>
            <th scope="col" className="px-3 py-3 text-right font-medium">
              ค้างนานสุด
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const pending = row.waiting_on_officer + row.waiting_on_applicant;
            return (
              <tr key={row.name} className="border-b border-line/60 last:border-0">
                <th scope="row" className="px-3 py-3 text-left font-medium text-ink">
                  {row.name}
                </th>
                <td className="px-3 py-3 text-right text-ink">{row.total}</td>
                <td
                  className={`px-3 py-3 text-right ${row.waiting_on_officer > 0 ? "font-semibold text-ink" : "text-ink-muted"}`}
                >
                  {row.waiting_on_officer}
                </td>
                <td
                  className={`px-3 py-3 text-right ${row.waiting_on_applicant > 0 ? "font-semibold text-ink" : "text-ink-muted"}`}
                >
                  {row.waiting_on_applicant}
                </td>
                <td className="px-3 py-3 text-right text-ink-muted">{row.finished}</td>
                <td className="px-3 py-3 text-right">
                  {pending === 0 ? (
                    <span className="text-ink-muted">—</span>
                  ) : (
                    <span
                      className={
                        row.longest_wait_days >= 7 ? "font-semibold text-danger-fg" : "text-ink"
                      }
                    >
                      {row.longest_wait_days} วัน
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
