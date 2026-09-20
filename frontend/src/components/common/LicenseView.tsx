"use client";

import { ArrowLeft, Printer } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Logo } from "@/components/brand/Logo";
import { Mascot } from "@/components/brand/Mascot";
import { ApiError } from "@/lib/api";
import {
  type LicenseDocument,
  getLicense,
  licenseSignatureUrl,
  thaiDate,
} from "@/lib/applications";

/**
 * M10 — เอกสารอนุญาตอิเล็กทรอนิกส์ที่ "พิมพ์ออกมาได้"
 *
 * ใช้การพิมพ์ของเบราว์เซอร์แทนการสร้าง PDF ฝั่งเซิร์ฟเวอร์ เพราะได้ผลเหมือนกัน
 * (บันทึกเป็น PDF ได้จากหน้าต่างพิมพ์) โดยไม่ต้องเพิ่ม dependency และฟอนต์ไทย
 * ซึ่งเป็นจุดที่พังบ่อยตอนสร้าง PDF ฝั่งเซิร์ฟเวอร์
 *
 * คลาส print:* คือสิ่งที่หายไปตอนพิมพ์ เช่น ปุ่มและลิงก์กลับ
 */
export function LicenseView({ applicationNo }: { applicationNo: string }) {
  const [doc, setDoc] = useState<LicenseDocument | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [signatureUrl, setSignatureUrl] = useState<string | null>(null);

  useEffect(() => {
    getLicense(applicationNo)
      .then(setDoc)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "เปิดเอกสารไม่ได้ กรุณาลองใหม่"),
      );
  }, [applicationNo]);

  // ลายมือชื่อผู้ลงนามต้องโหลดพร้อม token จึงเป็น object URL ที่ต้องคืนหน่วยความจำเอง
  useEffect(() => {
    let url: string | null = null;
    let cancelled = false;

    if (doc?.has_issuer_signature) {
      licenseSignatureUrl(applicationNo)
        .then((created) => {
          url = created;
          if (cancelled) URL.revokeObjectURL(created);
          else setSignatureUrl(created);
        })
        // โหลดรูปไม่ได้ต้องไม่ทำให้พิมพ์เอกสารไม่ได้ เหลือชื่อผู้ลงนามเป็นข้อความเหมือนเดิม
        .catch(() => setSignatureUrl(null));
    }

    return () => {
      cancelled = true;
      setSignatureUrl(null);
      if (url) URL.revokeObjectURL(url);
    };
  }, [applicationNo, doc?.has_issuer_signature]);

  if (error) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center">
        <Mascot pose="waiting" size="md" className="mx-auto w-40" />
        <h1 className="mt-6 text-2xl font-bold text-ink">ยังไม่มีเอกสารให้พิมพ์</h1>
        <p role="alert" className="mt-2 text-ink-muted">
          {error}
        </p>
        <Link
          href={`/operator/applications/${applicationNo}`}
          className="mt-6 inline-flex items-center gap-2 font-semibold text-brand-600 underline underline-offset-4"
        >
          <ArrowLeft className="size-4" aria-hidden />
          กลับไปหน้าคำขอ
        </Link>
      </main>
    );
  }

  if (!doc) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center text-ink-muted">
        กำลังโหลดเอกสาร…
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-8 sm:py-12 print:max-w-none print:p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <Link
          href={`/operator/applications/${applicationNo}`}
          className="inline-flex items-center gap-2 text-sm font-semibold text-brand-600 underline underline-offset-4"
        >
          <ArrowLeft className="size-4" aria-hidden />
          กลับไปหน้าคำขอ
        </Link>
        <button
          type="button"
          onClick={() => window.print()}
          className="inline-flex min-h-12 items-center gap-2 rounded-xl bg-brand-500 px-5 py-3 font-semibold text-white hover:bg-brand-400"
        >
          <Printer className="size-5" aria-hidden />
          พิมพ์เอกสาร
        </button>
      </div>

      <article className="mt-6 rounded-card border border-line bg-surface p-8 print:mt-0 print:rounded-none print:border-0 print:p-0">
        <header className="flex items-start justify-between gap-4 border-b border-line pb-5">
          <Logo className="h-12 w-auto" />
          <div className="text-right text-sm text-ink-muted">
            <p>เลขที่เอกสาร</p>
            <p className="font-mono text-base font-bold text-ink">{doc.license_no}</p>
          </div>
        </header>

        <h1 className="mt-6 text-center text-2xl font-bold text-ink">{doc.title}</h1>
        <p className="mt-1 text-center text-ink-muted">{doc.local_authority_name}</p>

        {(doc.is_revoked || doc.is_expired) && (
          <p className="mt-4 rounded-xl bg-danger-bg px-4 py-3 text-center font-semibold text-danger-fg">
            {doc.is_revoked ? "เอกสารนี้ถูกเพิกถอนแล้ว" : "เอกสารนี้หมดอายุแล้ว"}
          </p>
        )}

        <dl className="mt-8 space-y-3 text-ink">
          <Line label="ผู้ถือเอกสาร" value={doc.holder_name} />
          <Line label="ชื่อสถานที่" value={doc.property.name} />
          <Line label="ที่ตั้ง" value={doc.property.address.full_address} />
          <Line label="ประเภทที่พัก" value={doc.property_type_name} />
          <Line
            label="ขนาด"
            value={`${doc.property.room_count} ห้อง · รับผู้เข้าพักได้ ${doc.property.max_guests} คน · ${doc.property.has_restaurant ? "มีห้องอาหาร" : "ไม่มีห้องอาหาร"}`}
          />
          <Line label="เลขที่คำขออ้างอิง" value={doc.application_no} mono />
          <Line label="วันที่ออกเอกสาร" value={thaiDate(doc.issued_at)} />
          <Line label="มีผลตั้งแต่" value={thaiDate(doc.valid_from)} />
          <Line
            label="ใช้ได้ถึง"
            value={doc.valid_until ? thaiDate(doc.valid_until) : "ไม่มีกำหนดหมดอายุ"}
          />
          {doc.fee_amount !== null && (
            <Line
              label="ค่าธรรมเนียม"
              value={`${doc.fee_amount.toLocaleString("th-TH")} บาท`}
            />
          )}
        </dl>

        {/* ช่องลงนามของผู้ออกเอกสาร — เซ็นตอนกดออกเอกสาร (ดู decisions ข้อ 12) */}
        <div className="mt-10 flex justify-end">
          <div className="w-72 text-center text-ink">
            <div className="flex h-24 items-end justify-center">
              {signatureUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={signatureUrl}
                  alt={`ลายมือชื่อของ ${doc.issued_by_name}`}
                  className="max-h-24 w-auto object-contain"
                />
              ) : (
                <span className="pb-2 text-sm text-ink-muted print:hidden">
                  (เอกสารใบนี้ไม่มีลายมือชื่อเก็บไว้ในระบบ)
                </span>
              )}
            </div>
            <p className="border-t border-dotted border-ink/60 pt-2">ลงชื่อ ผู้ออกเอกสาร</p>
            <p className="mt-1">( {doc.issued_by_name} )</p>
          </div>
        </div>

        <footer className="mt-10 border-t border-line pt-5 text-sm text-ink-muted">
          <p>ออกโดย {doc.issued_by_name} · {doc.local_authority_name}</p>
          <p className="mt-1">
            ตรวจสอบความถูกต้องของเอกสารได้ด้วยเลขที่{" "}
            <span className="font-mono">{doc.license_no}</span>
          </p>
          <p className="mt-3 text-xs">
            เอกสารนี้ออกจากระบบ HoTLinE Doc — ต้นแบบสำหรับการสาธิต ข้อมูลทั้งหมดเป็นข้อมูลจำลอง
          </p>
        </footer>
      </article>
    </main>
  );
}

function Line({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 border-b border-line/60 pb-2">
      <dt className="w-44 shrink-0 text-ink-muted">{label}</dt>
      <dd className={`min-w-0 flex-1 font-medium ${mono ? "font-mono" : ""}`}>{value}</dd>
    </div>
  );
}
