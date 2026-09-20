"use client";

import {
  ArrowLeft,
  Check,
  Clock,
  ExternalLink,
  FileCheck,
  FileText,
  PencilLine,
  Send,
  X,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Mascot } from "@/components/brand/Mascot";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { SignaturePad } from "@/components/common/SignaturePad";
import { StatusPill } from "@/components/common/StatusPill";
import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api";
import { labelForKind } from "@/lib/applications";
import {
  type Decision,
  type OfficerApplication,
  type ReviewDecision,
  decideApplication,
  issueLicense,
  officerApplication,
  openDocumentFile,
  reviewDocument,
} from "@/lib/officer";
import { type RequiredDocument } from "@/lib/wizard";
import type { ApplicationStatus, DocumentStatus } from "@/types/enums";

/** สถานะที่ยังแก้ผลได้ — ตรงกับ OPEN_STATUSES ใน services/officer.py */
const OPEN = ["submitted", "under_review", "needs_revision"];

export function ReviewView({ applicationNo }: { applicationNo: string }) {
  const [app, setApp] = useState<OfficerApplication | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    officerApplication(applicationNo)
      .then(setApp)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "เปิดคำขอไม่ได้ กรุณาลองใหม่"),
      );
  }, [applicationNo]);

  if (error) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center">
        <Mascot pose="support" size="md" className="mx-auto w-40" />
        <h1 className="mt-6 text-2xl font-bold text-ink">เปิดคำขอนี้ไม่ได้</h1>
        <p role="alert" className="mt-2 text-ink-muted">
          {error}
        </p>
        <Link
          href="/officer/queue"
          className="mt-6 inline-flex items-center gap-2 font-semibold text-brand-600 underline underline-offset-4"
        >
          <ArrowLeft className="size-4" aria-hidden />
          กลับไปคิวคำขอ
        </Link>
      </main>
    );
  }

  if (!app) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center text-ink-muted">
        กำลังโหลดคำขอ…
      </main>
    );
  }

  const open = OPEN.includes(app.status);
  const documents = [...app.documents.self_service, ...app.documents.external];

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <Link
        href="/officer/queue"
        className="inline-flex items-center gap-2 text-sm font-semibold text-brand-600 underline underline-offset-4"
      >
        <ArrowLeft className="size-4" aria-hidden />
        กลับไปคิวคำขอ
      </Link>

      <PageHeader
        className="mt-4"
        eyebrow={`เลขที่คำขอ ${app.application_no}`}
        title={app.property.name}
        description={app.property.address.full_address}
        aside={
          <div className="text-right">
            <StatusPill kind="application" status={app.status as ApplicationStatus} />
            <p className="mt-1.5 flex items-center justify-end gap-1 text-sm text-ink-muted">
              <Clock className="size-3.5" aria-hidden />
              อยู่ในขั้นนี้ {app.days_waiting} วัน
            </p>
          </div>
        }
      />

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_20rem]">
        <SectionCard
          icon={PencilLine}
          title="เอกสารประกอบการพิจารณา"
          description="ตรวจทีละฉบับ แล้วบันทึกผล ผู้ยื่นจะเห็นเหตุผลที่คุณระบุ"
        >
          <div className="space-y-3">
            {documents.map((doc) => (
              <DocumentReviewRow
                key={doc.code}
                doc={doc}
                applicationNo={applicationNo}
                open={open}
                onUpdated={setApp}
              />
            ))}
          </div>
        </SectionCard>

        <div className="space-y-6">
          <div className="rounded-card border border-line bg-brand-50/40 p-5">
            <p className="text-sm font-semibold text-ink">ข้อมูลคำขอ</p>
            <dl className="mt-2 space-y-2 text-sm">
              <Row label="ประเภท" value={app.property_type_name} />
              <Row label="จำนวนห้อง" value={`${app.property.room_count} ห้อง`} />
              <Row label="ผู้เข้าพัก" value={`${app.property.max_guests} คน`} />
              <Row label="ห้องอาหาร" value={app.property.has_restaurant ? "มี" : "ไม่มี"} />
              <Row
                label="ลักษณะที่พัก"
                value={
                  app.property.accommodation_kind === "other"
                    ? (app.property.accommodation_kind_other ?? "อื่น ๆ")
                    : labelForKind(app.property.accommodation_kind)
                }
              />
              <Row label="พื้นที่" value={app.property.local_authority_name} />
              {app.fee && (
                <Row
                  label="ค่าธรรมเนียม"
                  value={`${app.fee.amount.toLocaleString("th-TH")} บาท / ${app.fee.validity_years} ปี`}
                />
              )}
            </dl>
            <p className="mt-3 border-t border-line pt-3 text-sm text-ink-muted">
              {app.reason}
            </p>
          </div>

          <DecisionPanel app={app} open={open} onDecided={setApp} />
        </div>
      </div>
    </main>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-2">
      <dt className="shrink-0 text-ink-muted">{label}</dt>
      <dd className="ml-auto text-right font-medium text-ink">{value}</dd>
    </div>
  );
}

/* --------------------------------------------------------- ตรวจรายฉบับ */

/**
 * ผลตรวจรายฉบับที่เจ้าหน้าที่กดได้
 *
 * **ไม่มีปุ่ม "ไม่ผ่าน" โดยตั้งใจ** (มติทีม) แม้ `fail` จะยังมีอยู่ในชนิดข้อมูลและ
 * ฝั่งเซิร์ฟเวอร์ยังรับอยู่ เพราะผลลัพธ์ของมันเหมือน "ขอแก้ไข" ทุกประการ —
 * เอกสารกลับไปสถานะ revision_requested ให้ผู้ยื่นส่งไฟล์ใหม่เหมือนกัน
 * (ดู DOCUMENT_STATUS_OF ใน backend/app/services/officer.py) ปุ่มสองปุ่มที่ทำ
 * สิ่งเดียวกันแต่ใช้คำต่างกัน ทำให้เจ้าหน้าที่ลังเลว่าควรกดอันไหน และทำให้ผู้ยื่น
 * เห็นคำว่า "ไม่ผ่าน" ทั้งที่แก้ไฟล์แล้วไปต่อได้ตามปกติ
 *
 * การปฏิเสธคำขอทั้งใบยังทำได้ที่ปุ่ม "ไม่อนุมัติ" ระดับคำขอเหมือนเดิม
 */
const REVIEW_BUTTONS: { value: ReviewDecision; label: string; icon: typeof Check; cls: string }[] =
  [
    { value: "pass", label: "ผ่าน", icon: Check, cls: "bg-success-bg text-success-fg" },
    {
      value: "request_revision",
      label: "ขอแก้ไข",
      icon: PencilLine,
      cls: "bg-warn-bg text-warn-fg",
    },
  ];

function DocumentReviewRow({
  doc,
  applicationNo,
  open,
  onUpdated,
}: {
  doc: RequiredDocument;
  applicationNo: string;
  open: boolean;
  onUpdated: (a: OfficerApplication) => void;
}) {
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function review(decision: ReviewDecision) {
    setError(null);
    setPending(true);
    try {
      onUpdated(await reviewDocument(applicationNo, doc.files[0].id, decision, comment));
      setComment("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "บันทึกผลตรวจไม่สำเร็จ");
    } finally {
      setPending(false);
    }
  }

  async function openFile(fileId: number) {
    setError(null);
    try {
      await openDocumentFile(applicationNo, fileId);
    } catch {
      setError("เปิดไฟล์ไม่ได้ กรุณาลองใหม่อีกครั้ง");
    }
  }

  return (
    <article className="rounded-xl border border-line bg-surface p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-brand-50 text-sm font-bold text-brand-700">
          {doc.code}
        </span>
        <h3 className="font-medium text-ink">{doc.name_th}</h3>
        {doc.is_mandatory && (
          <span className="rounded-full bg-danger-bg px-2 py-0.5 text-xs font-medium text-danger-fg">
            บังคับ
          </span>
        )}
        <StatusPill status={doc.status as DocumentStatus} className="ml-auto" />
      </div>

      {doc.is_system_form && (
        <p className="mt-2 text-sm text-ink-muted">
          {doc.files.length > 0
            ? "แบบฟอร์มที่ระบบสร้างจากข้อมูลคำขอ ไฟล์ที่แนบเป็นเพียงรูปลายมือชื่อ ให้เปิดตัวหนังสือด้านล่างเพื่อดูว่าลงชื่อกำกับข้อความใด"
            : "แบบฟอร์มที่ระบบสร้างจากข้อมูลคำขอ ผู้แจ้งยังไม่ได้ลงลายมือชื่อ"}
        </p>
      )}

      {/* ตัวเอกสารที่ต้องตัดสิน ไม่ใช่ไฟล์แนบ — กระดาษใบเดียวกับที่ผู้ยื่นเซ็น */}
      {doc.is_system_form && (
        <Link
          href={`/officer/applications/${applicationNo}/forms/${doc.code}`}
          className="mt-2 inline-flex min-h-10 items-center gap-2 rounded-lg border-2 border-brand-500 px-3 py-2 text-sm font-semibold text-brand-600 hover:bg-brand-50"
        >
          <FileText className="size-4" aria-hidden />
          {doc.files.length > 0 ? "เปิดหนังสือที่ลงลายมือชื่อแล้ว" : "เปิดหนังสือ (ยังไม่มีลายมือชื่อ)"}
        </Link>
      )}

      {doc.files.length > 0 && (
        <ul className="mt-2 space-y-1.5">
          {doc.files.map((file) => (
            <li key={file.id} className="flex flex-wrap items-center gap-2 text-sm">
              <button
                type="button"
                onClick={() => openFile(file.id)}
                className="inline-flex items-center gap-1.5 font-medium text-brand-600 underline underline-offset-4 hover:text-brand-400"
              >
                <ExternalLink className="size-3.5" aria-hidden />
                {file.original_name}
              </button>
              {file.version_no > 1 && (
                <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700">
                  รุ่นที่ {file.version_no}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      {error && (
        <p role="alert" className="mt-2 rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger-fg">
          {error}
        </p>
      )}

      {open && doc.files.length > 0 && (
        <div className="mt-3 space-y-2">
          <label className="block">
            <span className="sr-only">เหตุผล สำหรับ {doc.name_th}</span>
            <input
              type="text"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              maxLength={1000}
              placeholder="ระบุเหตุผล (บังคับเมื่อขอให้แก้ไข)"
              className="min-h-10 w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink placeholder:text-ink-muted/70"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            {REVIEW_BUTTONS.map((b) => (
              <button
                key={b.value}
                type="button"
                disabled={pending}
                onClick={() => review(b.value)}
                className={`inline-flex min-h-10 items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-60 ${b.cls}`}
              >
                <b.icon className="size-4" aria-hidden />
                {b.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </article>
  );
}

/* --------------------------------------------------------- สรุปผลคำขอ */

function DecisionPanel({
  app,
  open,
  onDecided,
}: {
  app: OfficerApplication;
  open: boolean;
  onDecided: (a: OfficerApplication) => void;
}) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function issue(signature: Blob) {
    setError(null);
    setPending(true);
    try {
      onDecided(await issueLicense(app.application_no, signature));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "ออกเอกสารไม่สำเร็จ");
      throw err; // ให้ช่องลายมือชื่อรู้ว่าไม่สำเร็จ จะได้ไม่ล้างลายเซ็นทิ้ง
    } finally {
      setPending(false);
    }
  }

  if (!open) {
    return (
      <div className="rounded-card border border-line bg-surface p-5">
        <p className="font-semibold text-ink">พิจารณาเสร็จแล้ว</p>
        <p className="mt-1 text-sm text-ink-muted">
          ผลคือ <StatusPill kind="application" status={app.status as ApplicationStatus} />
        </p>
        {app.decision_reason && (
          <p className="mt-2 text-sm text-ink-muted">เหตุผล: {app.decision_reason}</p>
        )}

        {/* M10 — ออกเอกสารเป็นขั้นแยกจากการอนุมัติ */}
        {app.license_no && (
          <div className="mt-3 rounded-xl bg-success-bg/60 px-3 py-2 text-sm text-ink">
            <p>
              ออกเอกสารแล้ว เลขที่{" "}
              <span className="font-mono font-semibold">{app.license_no}</span>
            </p>
            {/* คนลงนามต้องเปิดดูใบที่ออกไปได้ ไม่ใช่เห็นแค่เลขที่
                หน้าเอกสารมีปุ่มพิมพ์ / บันทึกเป็น PDF อยู่ในตัว (M10) */}
            <Link
              href={`/officer/applications/${app.application_no}/license`}
              className="mt-2 inline-flex min-h-10 items-center gap-2 rounded-lg border-2 border-brand-500 bg-surface px-3 py-2 font-semibold text-brand-600 hover:bg-brand-50"
            >
              <FileCheck className="size-4" aria-hidden />
              เปิดเอกสารที่ออกให้ · พิมพ์ / บันทึกเป็น PDF
            </Link>
          </div>
        )}

        {error && (
          <p
            role="alert"
            className="mt-3 rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger-fg"
          >
            {error}
          </p>
        )}

        {/* เจ้าหน้าที่ควรรู้ว่าการกดปุ่มนี้มีผลออกไปถึงผู้ยื่นทันที */}
        <p className="mt-3 text-xs text-ink-muted">
          ทุกครั้งที่บันทึกผลพิจารณาหรือออกเอกสาร ระบบจะส่งอีเมลแจ้งผู้ยื่นตามที่อยู่ที่ใช้สมัครสมาชิกโดยอัตโนมัติ
        </p>

        {app.can_issue_license && (
          <div className="mt-4 rounded-xl border border-line bg-canvas p-4">
            <p className="flex items-center gap-2 font-semibold text-ink">
              <FileCheck className="size-5 text-brand-600" aria-hidden />
              ลงนามเพื่อออกเอกสาร
            </p>
            {/* เอกสารที่ไม่มีใครลงนามใช้ไม่ได้ การเซ็นจึงเป็นขั้นตอนเดียวกับการออกเอกสาร */}
            <p className="mt-1 text-sm text-ink-muted">
              ลายมือชื่อของคุณจะปรากฏบนใบอนุญาต/หนังสือรับรองที่ผู้ยื่นพิมพ์ออกไป
            </p>
            <SignaturePad className="mt-3" onSave={issue} saveLabel="ลงนามและออกเอกสาร" />
          </div>
        )}
      </div>
    );
  }

  async function decide(decision: Decision) {
    setError(null);
    setPending(true);
    try {
      onDecided(await decideApplication(app.application_no, decision, reason));
      setReason("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "บันทึกผลไม่สำเร็จ");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="rounded-card border border-line bg-surface p-5">
      <p className="font-semibold text-ink">ผลการพิจารณา</p>

      {/* บอกเหตุผลที่ยังกดอนุมัติไม่ได้ ดีกว่าทำปุ่มเป็นสีเทาเฉย ๆ */}
      {app.pending_documents.length > 0 && (
        <div className="mt-3 rounded-xl bg-warn-bg px-3 py-2 text-sm">
          <p className="font-medium text-ink">ยังอนุมัติไม่ได้ เพราะเอกสารเหล่านี้ยังไม่ผ่าน</p>
          <ul className="mt-1 list-inside list-disc text-ink-muted">
            {app.pending_documents.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </div>
      )}

      <label className="mt-3 block">
        <span className="text-sm font-medium text-ink">เหตุผล</span>
        <textarea
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          maxLength={1000}
          placeholder="บังคับเมื่อไม่อนุมัติหรือขอให้แก้ไข"
          className="mt-1 w-full rounded-xl border border-line bg-canvas px-3 py-2 text-sm text-ink placeholder:text-ink-muted/70"
        />
      </label>

      {error && (
        <p role="alert" className="mt-2 rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger-fg">
          {error}
        </p>
      )}

      <div className="mt-3 space-y-2">
        <Button onClick={() => decide("approve")} disabled={!app.can_approve || pending}>
          <Check className="size-5" aria-hidden />
          อนุมัติคำขอ
        </Button>
        <Button variant="outline" onClick={() => decide("request_revision")} disabled={pending}>
          <Send className="size-5" aria-hidden />
          ส่งกลับให้แก้ไข
        </Button>
        <button
          type="button"
          onClick={() => decide("reject")}
          disabled={pending}
          className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border-2 border-danger-fg/30 bg-surface px-5 py-3 font-semibold text-danger-fg hover:bg-danger-bg disabled:opacity-60"
        >
          <X className="size-5" aria-hidden />
          ไม่อนุมัติ
        </button>
      </div>
    </div>
  );
}
