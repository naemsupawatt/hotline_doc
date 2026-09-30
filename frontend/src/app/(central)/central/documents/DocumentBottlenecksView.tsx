"use client";

import { CheckCircle2, Clock, FileStack, MapPin } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Mascot } from "@/components/brand/Mascot";
import { RankedDocumentRow, ReportStat } from "@/components/common/DocumentReport";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { ApiError } from "@/lib/api";
import { type DocumentBottleneck, getDocumentBottlenecks } from "@/lib/reports";

/**
 * เอกสารฉบับไหนเป็นคอขวดของทั้งจังหวัด — ฝั่งที่ค้างอยู่ที่เจ้าหน้าที่
 *
 * หน้าภาพรวมตอบได้ว่าคำขอค้างที่ "ขั้นตอน" ใด หน้านี้ลงลึกอีกชั้นว่าค้างที่
 * "เอกสารฉบับ" ใด ซึ่งนำไปสู่การแก้คนละแบบ:
 *   เอกสารฉบับเดียวค้างแทบทุกเขต -> ปัญหาอยู่ที่ตัวเอกสารหรือกระบวนการ
 *   หลายฉบับค้างกระจุกอยู่เขตเดียว -> เขตนั้นกำลังมีปัญหากำลังคน
 *
 * ยังอยู่ใต้กติกาเดิมของหน้าส่วนกลาง (ตารางข้อ 5): ดูได้อย่างเดียว
 * ไม่มีปุ่มที่เปลี่ยนผลพิจารณา และไม่มีเลขที่คำขอหรือชื่อผู้ยื่นให้เห็น
 */
export function DocumentBottlenecksView() {
  const [rows, setRows] = useState<DocumentBottleneck[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDocumentBottlenecks()
      .then(setRows)
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

  if (!rows) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center text-ink-muted">
        กำลังโหลดรายงาน…
      </main>
    );
  }

  const stuckDocuments = rows.reduce((sum, row) => sum + row.count, 0);
  const longestWait = rows.reduce((longest, row) => Math.max(longest, row.oldest_days), 0);

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
      <PageHeader
        eyebrow="ภาพรวมส่วนกลาง"
        illustration="coastal-community"
        title="เอกสารฉบับไหนทำให้งานติด"
        description="เอกสารที่ผู้ยื่นส่งมาแล้วแต่ยังไม่มีเจ้าหน้าที่ลงความเห็น เรียงจากฉบับที่ติดขัดมากที่สุด นับเฉพาะคำขอที่ยังอยู่ในกระบวนการ"
      />

      <SiblingReportLink />

      {rows.length === 0 ? (
        <div className="mt-6 flex flex-col items-center rounded-card border border-dashed border-line bg-success-bg/30 p-10 text-center">
          <Mascot pose="success" size="md" className="w-40" />
          <p className="mt-4 flex items-center gap-2 font-semibold text-ink">
            <CheckCircle2 className="size-5 text-success-fg" aria-hidden />
            ไม่มีเอกสารค้างตรวจในขณะนี้
          </p>
          <p className="mt-1 max-w-md text-sm text-ink-muted">
            เอกสารทุกฉบับของคำขอที่ยังอยู่ในกระบวนการ มีเจ้าหน้าที่ลงความเห็นครบแล้ว
          </p>
        </div>
      ) : (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <ReportStat icon={FileStack} label="ฉบับที่รอการตรวจ" value={`${stuckDocuments} ฉบับ`} />
            <ReportStat icon={MapPin} label="ชนิดเอกสารที่ติดขัด" value={`${rows.length} ชนิด`} />
            <ReportStat
              icon={Clock}
              label="ค้างนานที่สุด"
              value={longestWait === 0 ? "ไม่ถึงหนึ่งวัน" : `${longestWait} วัน`}
              alarming={longestWait >= 7}
            />
          </div>

          <SectionCard
            icon={FileStack}
            title="เรียงจากฉบับที่ติดขัดมากที่สุด"
            description="ตัวเลขคือจำนวนคำขอที่ค้างอยู่ที่เอกสารฉบับนั้น ไม่ใช่จำนวนไฟล์"
            className="mt-6"
          >
            <ol className="space-y-5">
              {rows.map((row, index) => (
                <RankedDocumentRow
                  key={row.code}
                  rank={index + 1}
                  code={row.code}
                  name={row.name_th}
                  count={row.count}
                  unit="คำขอ"
                  max={rows[0].count}
                  areas={row.by_authority}
                >
                  {/* ค้างนานสุดบอกความเร่งด่วน ส่วนจำนวนบอกขนาดของปัญหา — คนละเรื่องกัน
                      ฉบับที่ค้างใบเดียวแต่ค้างมาสามสัปดาห์ ก็ควรถูกมองเห็น */}
                  <span
                    className={`flex items-center gap-1.5 ${row.oldest_days >= 7 ? "font-semibold text-danger-fg" : "text-ink-muted"}`}
                  >
                    <Clock className="size-3.5 shrink-0" aria-hidden />
                    {row.oldest_days === 0
                      ? "ค้างไม่ถึงหนึ่งวัน"
                      : `ค้างนานสุด ${row.oldest_days} วัน`}
                  </span>
                </RankedDocumentRow>
              ))}
            </ol>
          </SectionCard>
        </>
      )}
    </main>
  );
}

/** คู่แฝดอีกหน้าอยู่คนละฝั่งของกระบวนการ ถ้าไม่โยงกันไว้ คนจะอ่านหน้านี้
    แล้วสรุปว่า "เอกสารไม่ติดแล้ว" ทั้งที่อีกฝั่งอาจกองอยู่ที่ผู้ยื่น */
function SiblingReportLink() {
  return (
    <p className="mt-6 text-sm text-ink-muted">
      หน้านี้ดูของที่ส่งเข้ามาแล้ว ส่วนของที่ผู้ยื่นยังไม่ได้ส่ง ดูที่{" "}
      <Link
        href="/central/missing-documents"
        className="font-semibold text-brand-600 underline underline-offset-4 hover:text-brand-400"
      >
        เอกสารที่ยังไม่ส่ง
      </Link>
    </p>
  );
}
