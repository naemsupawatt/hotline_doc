"use client";

import { CheckCircle2, CircleAlert, FileStack, Inbox, MapPin } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Mascot } from "@/components/brand/Mascot";
import { RankedDocumentRow, ReportStat } from "@/components/common/DocumentReport";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { ApiError } from "@/lib/api";
import { type MissingUpload, getMissingUploads } from "@/lib/reports";

/**
 * เอกสารที่ผู้ประกอบการยังไม่ได้อัปโหลดเข้ามา
 *
 * คู่แฝดของหน้า "เอกสารที่ค้างตรวจ" แต่มองอีกฝั่งของกระบวนการ — อันนั้นคือของ
 * ที่ส่งมาแล้วค้างที่เจ้าหน้าที่ อันนี้คือของที่ยังไม่ถูกส่งมา ซึ่งแก้คนละทาง
 * (เร่งเจ้าหน้าที่ กับ ช่วยผู้ยื่นหาเอกสาร)
 *
 * รวมคำขอที่ยังเป็นร่างด้วย เพราะนั่นคือจุดที่ผู้ประกอบการกำลังเตรียมเอกสาร
 * และเป็นที่ที่คนหยุดไปกลางคันมากที่สุด
 *
 * ยังอยู่ใต้กติกาเดิมของหน้าส่วนกลาง: ดูได้อย่างเดียว ไม่มีเลขที่คำขอหรือชื่อผู้ยื่น
 */
export function MissingUploadsView() {
  const [rows, setRows] = useState<MissingUpload[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMissingUploads()
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

  const missing = rows.reduce((sum, row) => sum + row.count, 0);
  const mandatoryMissing = rows.reduce((sum, row) => sum + row.mandatory_count, 0);

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
      <PageHeader
        eyebrow="ภาพรวมส่วนกลาง"
        illustration="coastal-community"
        title="ผู้ยื่นติดตรงเอกสารฉบับไหน"
        description="เอกสารที่ยังไม่ได้อัปโหลดเข้ามา นับจากคำขอที่ยังไม่ถูกตัดสิน รวมคำขอที่ยังเป็นร่างซึ่งเป็นจุดที่คนหยุดไปกลางคันมากที่สุด"
      />

      <p className="mt-6 text-sm text-ink-muted">
        หน้านี้ดูของที่ยังไม่ถูกส่งมา ส่วนของที่ส่งแล้วแต่ค้างรอเจ้าหน้าที่ตรวจ ดูที่{" "}
        <Link
          href="/central/documents"
          className="font-semibold text-brand-600 underline underline-offset-4 hover:text-brand-400"
        >
          เอกสารที่ค้างตรวจ
        </Link>
      </p>

      {rows.length === 0 ? (
        <div className="mt-6 flex flex-col items-center rounded-card border border-dashed border-line bg-success-bg/30 p-10 text-center">
          <Mascot pose="success" size="md" className="w-40" />
          <p className="mt-4 flex items-center gap-2 font-semibold text-ink">
            <CheckCircle2 className="size-5 text-success-fg" aria-hidden />
            ไม่มีเอกสารที่ค้างส่งในขณะนี้
          </p>
          <p className="mt-1 max-w-md text-sm text-ink-muted">
            คำขอที่ยังไม่ถูกตัดสินทุกใบ แนบเอกสารครบตามรายการของประเภทที่พักแล้ว
          </p>
        </div>
      ) : (
        <>
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <ReportStat icon={Inbox} label="ฉบับที่ยังไม่ได้ส่ง" value={`${missing} ฉบับ`} />
            <ReportStat
              icon={CircleAlert}
              label="ในจำนวนนั้น เป็นเอกสารบังคับ"
              value={`${mandatoryMissing} ฉบับ`}
              alarming={mandatoryMissing > 0}
            />
            <ReportStat icon={MapPin} label="ชนิดเอกสารที่ขาด" value={`${rows.length} ชนิด`} />
          </div>

          <SectionCard
            icon={FileStack}
            title="เรียงจากฉบับที่ขาดมากที่สุด"
            description="ตัวเลขคือจำนวนคำขอที่ยังไม่ได้แนบเอกสารฉบับนั้น"
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
                  {/* แยก "บังคับ" ออกมาเสมอ เพราะเอกสารไม่บังคับบางฉบับตั้งใจให้ขาดได้
                      (ช่องแนบใน ร.ร.1 ที่บุคคลธรรมดาไม่มีอยู่แล้ว) ถ้าอ่านรวมกัน
                      จะสรุปผิดว่าผู้ยื่นทิ้งงานทั้งที่แนบครบทุกฉบับที่ต้องแนบแล้ว */}
                  <span
                    className={`flex items-center gap-1.5 ${row.mandatory_count > 0 ? "font-semibold text-danger-fg" : "text-ink-muted"}`}
                  >
                    <CircleAlert className="size-3.5 shrink-0" aria-hidden />
                    {row.mandatory_count === 0
                      ? "ไม่บังคับทุกใบ ขาดได้"
                      : `บังคับ ${row.mandatory_count.toLocaleString("th-TH")} ใบ`}
                  </span>
                </RankedDocumentRow>
              ))}
            </ol>
          </SectionCard>

          <p className="mt-4 text-sm text-ink-muted">
            เอกสารบังคับที่ขาดคือสิ่งที่ทำให้ผู้ยื่นกดยื่นคำขอไม่ได้ (M6)
            ส่วนฉบับที่ไม่บังคับบางชนิดตั้งใจให้ขาดได้ตามรูปแบบกิจการ
            จึงไม่ควรอ่านสองอย่างนี้รวมกัน
          </p>
        </>
      )}
    </main>
  );
}
