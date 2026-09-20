"use client";

import {
  Building2,
  CheckCircle2,
  Clock,
  Landmark,
  MapPin,
  Paperclip,
  PencilLine,
  Plus,
  Printer,
  Send,
  Upload,
  Users,
  UtensilsCrossed,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Mascot } from "@/components/brand/Mascot";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { StatusPill } from "@/components/common/StatusPill";
import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api";
import {
  type Application,
  allDocuments,
  formatSize,
  getApplication,
  labelForKind,
  openDocumentFile,
  submitApplication,
  uploadDocument,
} from "@/lib/applications";
import { type RequiredDocument, describeAccepted } from "@/lib/wizard";
import type { ApplicationStatus, DocumentStatus } from "@/types/enums";

export function ApplicationView({ applicationNo }: { applicationNo: string }) {
  const [application, setApplication] = useState<Application | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getApplication(applicationNo)
      .then(setApplication)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "เปิดคำขอไม่ได้ กรุณาลองใหม่อีกครั้ง"),
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
      </main>
    );
  }

  if (!application) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center text-ink-muted">
        กำลังโหลดคำขอ…
      </main>
    );
  }

  const { property, documents } = application;
  const editable = application.status === "draft" || application.status === "needs_revision";

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <PageHeader
        eyebrow={`เลขที่คำขอ ${application.application_no}`}
        title={property.name}
        description={property.address.full_address}
        aside={
          <div className="text-right">
            <StatusPill kind="application" status={application.status as ApplicationStatus} />
            <p className="mt-1.5 flex items-center justify-end gap-1 text-sm text-ink-muted">
              <Clock className="size-3.5" aria-hidden />
              อยู่ในขั้นนี้ {application.days_waiting} วัน
            </p>
          </div>
        }
      />

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <SectionCard
          icon={Building2}
          title="ข้อมูลที่พัก"
          description="ใช้ประกอบแบบหนังสือแจ้งสถานที่พักที่ไม่เป็นโรงแรม"
          className="lg:col-span-2"
        >
          <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
            <Fact icon={Building2} label="จำนวนห้องพัก" value={`${property.room_count} ห้อง`} />
            <Fact icon={Users} label="รับผู้เข้าพักได้" value={`${property.max_guests} คน`} />
            <Fact
              icon={UtensilsCrossed}
              label="ห้องอาหาร"
              value={property.has_restaurant ? "มี" : "ไม่มี"}
            />
            <Fact
              icon={PencilLine}
              label="ลักษณะที่พัก"
              value={
                property.accommodation_kind === "other"
                  ? (property.accommodation_kind_other ?? "อื่น ๆ")
                  : labelForKind(property.accommodation_kind)
              }
            />
            <Fact
              icon={MapPin}
              label="พื้นที่ตั้ง"
              value={property.local_authority_name}
              className="sm:col-span-2"
            />
          </dl>
        </SectionCard>

        <div className="rounded-card border border-line bg-brand-50/40 p-5">
          <p className="text-sm font-semibold text-ink">ผลการจำแนกประเภท</p>
          <p className="mt-1 text-xl font-bold text-ink">{application.property_type_name}</p>
          <p className="mt-2 text-sm text-ink-muted">{application.reason}</p>

          {application.fee && (
            <p className="mt-3 text-sm text-ink">
              ค่าธรรมเนียม{" "}
              <span className="font-bold text-brand-600">
                {application.fee.amount.toLocaleString("th-TH")} บาท
              </span>{" "}
              ต่อ {application.fee.validity_years} ปี
            </p>
          )}

          {application.matched_rule_code && (
            <p className="mt-3 text-xs text-ink-muted">
              ตัดสินด้วยเกณฑ์รหัส{" "}
              <span className="font-mono">{application.matched_rule_code}</span> ณ วันที่เปิดคำขอ
            </p>
          )}
        </div>
      </div>

      <Progress application={application} />

      <div className="mt-5 grid gap-6 lg:grid-cols-2">
        <SectionCard
          icon={PencilLine}
          tone="brand"
          title="ทำเองได้เลย"
          description="เตรียมและอัปโหลดเอกสารด้วยตัวเอง"
        >
          <div className="space-y-3">
            {documents.self_service.map((doc) => (
              <DocumentRow
                key={doc.code}
                doc={doc}
                applicationNo={applicationNo}
                editable={editable}
                onUploaded={setApplication}
              />
            ))}
          </div>
        </SectionCard>

        <SectionCard
          icon={Landmark}
          tone="info"
          title="ต้องไปขอก่อน"
          description="ติดต่อหน่วยงานที่เกี่ยวข้อง แล้วนำฉบับที่ลงนามแล้วมาอัปโหลด"
        >
          <div className="space-y-3">
            {documents.external.map((doc) => (
              <DocumentRow
                key={doc.code}
                doc={doc}
                applicationNo={applicationNo}
                editable={editable}
                onUploaded={setApplication}
              />
            ))}
          </div>
        </SectionCard>
      </div>

      <SubmitPanel
        application={application}
        editable={editable}
        onSubmitted={setApplication}
      />
    </main>
  );
}

/* ------------------------------------------------------------ ความคืบหน้า */

function Progress({ application }: { application: Application }) {
  const docs = allDocuments(application);
  const total = docs.filter((d) => d.is_mandatory).length;
  const done = docs.filter((d) => d.is_mandatory && d.status !== "not_uploaded").length;
  const percent = total === 0 ? 0 : Math.round((done / total) * 100);

  return (
    <section className="mt-10" aria-labelledby="progress-heading">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 id="progress-heading" className="text-xl font-bold text-ink">
            เอกสารของคำขอนี้
          </h2>
          <p className="mt-1 text-ink-muted">
            ต้องครบทุกฉบับที่ระบุว่าบังคับ จึงจะยื่นคำขอได้
          </p>
        </div>
        <p className="text-sm font-semibold text-ink">
          เตรียมแล้ว {done} จาก {total} ฉบับ
        </p>
      </div>

      {/* NFR Accessibility: แถบสีสื่อความหมายลำพังไม่ได้ ต้องมีตัวเลขกำกับ (ข้างบน) */}
      <div
        className="mt-3 h-2 w-full overflow-hidden rounded-full bg-line"
        role="progressbar"
        aria-valuenow={done}
        aria-valuemin={0}
        aria-valuemax={total}
        aria-labelledby="progress-heading"
      >
        <div
          className="h-full rounded-full bg-brand-500 transition-all"
          style={{ width: `${percent}%` }}
        />
      </div>
    </section>
  );
}

/* --------------------------------------------------------------- ปุ่มยื่น */

function SubmitPanel({
  application,
  editable,
  onSubmitted,
}: {
  application: Application;
  editable: boolean;
  onSubmitted: (a: Application) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  if (!editable) {
    return (
      <div className="mt-8 flex items-start gap-3 rounded-card border border-line bg-success-bg/40 p-5">
        <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-success-fg" aria-hidden />
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-ink">
            {application.license_no ? "ได้รับอนุมัติแล้ว" : "ยื่นคำขอเรียบร้อยแล้ว"}
          </p>
          <p className="mt-1 text-sm text-ink-muted">
            {application.license_no
              ? "ระบบออกเอกสารให้แล้ว พิมพ์เก็บไว้เป็นหลักฐานหรือใช้ยื่นต่อนายทะเบียนได้"
              : "เจ้าหน้าที่จะตรวจเอกสารและแจ้งผลกลับ ระหว่างนี้แก้ไขเอกสารไม่ได้ หากเจ้าหน้าที่ขอให้แก้ไข ระบบจะเปิดให้ส่งใหม่เอง"}
          </p>

          {/* M10: "พิมพ์ใบอนุญาตหรือเอกสารอ้างอิงเมื่อได้รับอนุมัติ" (ตารางข้อ 5) */}
          {application.license_no && (
            <Link
              href={`/operator/applications/${application.application_no}/license`}
              className="mt-3 inline-flex min-h-12 items-center gap-2 rounded-xl bg-brand-500 px-5 py-3 font-semibold text-white hover:bg-brand-400"
            >
              <Printer className="size-5" aria-hidden />
              เปิดเอกสาร {application.license_no}
            </Link>
          )}
        </div>
      </div>
    );
  }

  async function onSubmit() {
    setError(null);
    setPending(true);
    try {
      onSubmitted(await submitApplication(application.application_no));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "ยื่นคำขอไม่สำเร็จ กรุณาลองใหม่อีกครั้ง");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mt-8 rounded-card border border-line bg-surface p-5">
      {/* M6: ห้ามทำแค่ปุ่มสีเทา ต้องบอกด้วยว่าขาดฉบับใด (T-06) */}
      {application.missing_documents.length > 0 && (
        <div className="mb-4 rounded-xl bg-warn-bg px-4 py-3">
          <p className="font-medium text-ink">
            ยังยื่นไม่ได้ เพราะขาดเอกสารบังคับอีก {application.missing_documents.length} ฉบับ
          </p>
          <ul className="mt-1.5 list-inside list-disc text-sm text-ink-muted">
            {application.missing_documents.map((m) => (
              <li key={m.code}>
                {m.code} {m.name_th}
                {/* แบบฟอร์มที่ระบบกรอกให้ ขาดลายมือชื่อ ไม่ใช่ขาดไฟล์ ต้องพูดให้ตรง */}
                {m.needs_signature && " — ยังไม่ได้ลงลายมือชื่อ"}
              </li>
            ))}
          </ul>
        </div>
      )}

      {error && (
        <p
          role="alert"
          className="mb-4 rounded-xl bg-danger-bg px-4 py-3 text-sm font-medium text-danger-fg"
        >
          {error}
        </p>
      )}

      <Button onClick={onSubmit} disabled={!application.can_submit || pending}>
        {pending ? "กำลังยื่นคำขอ…" : "ยื่นคำขอ"}
        {pending ? null : <Send className="size-5" aria-hidden />}
      </Button>
    </div>
  );
}

/* ----------------------------------------------------------- แถวเอกสาร */

function DocumentRow({
  doc,
  applicationNo,
  editable,
  onUploaded,
}: {
  doc: RequiredDocument;
  applicationNo: string;
  editable: boolean;
  onUploaded: (a: Application) => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function openFile(fileId: number) {
    setError(null);
    try {
      await openDocumentFile(applicationNo, fileId);
    } catch {
      setError("เปิดไฟล์ไม่ได้ กรุณาลองใหม่อีกครั้ง");
    }
  }

  async function upload(file: File, slotNo?: number) {
    setError(null);
    setPending(true);
    try {
      await uploadDocument(applicationNo, doc.code, file, slotNo);
      // ดึงคำขอใหม่ทั้งใบ เพื่อให้สถานะ แถบความคืบหน้า และปุ่มยื่น ตรงกันเสมอ
      onUploaded(await getApplication(applicationNo));
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "อัปโหลดไม่สำเร็จ กรุณาลองใหม่อีกครั้ง",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <article className="rounded-xl border border-line bg-surface p-3">
      <div className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-brand-50 text-sm font-bold text-brand-700">
          {doc.code}
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-medium text-ink">{doc.name_th}</h3>
            {doc.is_mandatory && (
              <span className="rounded-full bg-danger-bg px-2 py-0.5 text-xs font-medium text-danger-fg">
                บังคับ
              </span>
            )}
            <StatusPill status={doc.status as DocumentStatus} />
          </div>

          <p className="mt-1 flex items-center gap-1.5 text-sm text-ink-muted">
            {doc.is_system_form ? (
              <PencilLine className="size-3.5 shrink-0" aria-hidden />
            ) : (
              <Upload className="size-3.5 shrink-0" aria-hidden />
            )}
            {doc.is_system_form
              ? "ระบบกรอกให้จากข้อมูลคำขอ เหลือเพียงลงลายมือชื่อ ซึ่งต้องมีก่อนยื่นคำขอ"
              : describeAccepted(doc.accepted_mime)}
          </p>

          {doc.contact_point && (
            <p className="mt-1.5 flex items-start gap-1.5 text-sm text-ink-muted">
              <MapPin className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              ไปติดต่อที่ {doc.contact_point.office_name}
              {doc.contact_point.estimated_days
                ? ` · ใช้เวลาประมาณ ${doc.contact_point.estimated_days} วัน`
                : ""}
            </p>
          )}
        </div>
      </div>

      {/* ไฟล์แนบของแบบฟอร์มที่ระบบกรอกให้คือรูปลายเซ็น ไม่ใช่ตัวเอกสาร จึงไม่แสดง
          เป็นรายการไฟล์ เพราะผู้ยื่นเห็น "ลายมือชื่อ.png" แล้วเข้าใจว่านี่คือเอกสาร
          ที่ส่งไป ทั้งที่เอกสารจริงคือหนังสือทั้งใบ ซึ่งเปิดได้จากปุ่มด้านล่าง */}
      {!doc.is_system_form && doc.files.length > 0 && (
        <ul className="mt-3 space-y-2">
          {doc.files.map((file) => (
            <li
              key={file.id}
              className="flex flex-wrap items-center gap-2 rounded-lg bg-canvas px-3 py-2 text-sm"
            >
              <Paperclip className="size-3.5 shrink-0 text-ink-muted" aria-hidden />
              <button
                type="button"
                onClick={() => openFile(file.id)}
                className="min-w-0 flex-1 truncate text-left font-medium text-brand-600 underline underline-offset-4 hover:text-brand-400"
                title={file.original_name}
              >
                {file.original_name}
              </button>
              <span className="text-ink-muted">{formatSize(file.size_bytes)}</span>
              {file.version_no > 1 && (
                <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700">
                  รุ่นที่ {file.version_no}
                </span>
              )}
              {editable && (
                <FilePicker
                  label="ส่งใหม่"
                  accept={doc.accepted_mime}
                  disabled={pending}
                  onPick={(f) => upload(f, file.slot_no)}
                />
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

      {/* แบบฟอร์มทุกฉบับที่ระบบกรอกให้ มีหน้ากระดาษของตัวเองที่เส้นทางเดียวกัน */}
      {doc.is_system_form && (
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <Link
            href={`/operator/applications/${applicationNo}/forms/${doc.code}`}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border-2 border-brand-500 px-4 py-2.5 text-sm font-semibold text-brand-600 hover:bg-brand-50"
          >
            <Printer className="size-4" aria-hidden />
            {doc.files.length > 0
              ? "เปิดหนังสือที่ลงลายมือชื่อแล้ว · พิมพ์ / บันทึกเป็น PDF"
              : "เปิดแบบฟอร์ม · ลงลายมือชื่อ · บันทึกเป็น PDF"}
          </Link>
          {doc.files.length === 0 ? (
            <span className="text-sm font-medium text-warn-fg">
              ยังไม่ได้ลงลายมือชื่อ — ต้องเซ็นก่อนจึงจะยื่นคำขอได้
            </span>
          ) : (
            <span className="text-sm text-ink-muted">
              ลงลายมือชื่อแล้ว
              {doc.files[0].version_no > 1 && ` (ลายมือชื่อรุ่นที่ ${doc.files[0].version_no})`} —
              เจ้าหน้าที่จะเห็นหนังสือฉบับนี้พร้อมลายมือชื่อ
            </span>
          )}
        </div>
      )}

      {editable && !doc.is_system_form && (
        <div className="mt-3">
          <FilePicker
            label={
              doc.files.length === 0
                ? "เลือกไฟล์"
                : doc.allows_multiple
                  ? "แนบไฟล์เพิ่ม"
                  : "แนบไฟล์ใหม่แทนของเดิม"
            }
            icon={doc.files.length > 0 && doc.allows_multiple ? Plus : Upload}
            accept={doc.accepted_mime}
            disabled={pending}
            variant="outline"
            onPick={(f) => upload(f)}
          />
          {pending && <p className="mt-2 text-sm text-ink-muted">กำลังอัปโหลด…</p>}
        </div>
      )}
    </article>
  );
}

/**
 * ปุ่มเลือกไฟล์ — ซ่อน input จริงไว้ใต้ label เพราะ input[type=file] จัดสไตล์ไม่ได้
 * ใช้ label ห่อแทน div เพื่อให้ยังกดด้วยคีย์บอร์ดและ screen reader ได้
 */
function FilePicker({
  label,
  accept,
  disabled,
  onPick,
  icon: Icon,
  variant = "ghost",
}: {
  label: string;
  accept: string[];
  disabled?: boolean;
  onPick: (file: File) => void;
  icon?: typeof Upload;
  variant?: "ghost" | "outline";
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  const style =
    variant === "outline"
      ? "border-2 border-brand-500 bg-surface text-brand-600 hover:bg-brand-50 min-h-12 px-5 py-3 text-base w-full"
      : "text-brand-600 hover:bg-brand-50 min-h-10 px-3 py-2 text-sm";

  return (
    <>
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        className={`inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${style}`}
      >
        {Icon && <Icon className="size-5" aria-hidden />}
        {label}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept={accept.join(",")}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          // ล้างค่าเพื่อให้เลือกไฟล์ชื่อเดิมซ้ำแล้ว onChange ยังทำงาน
          e.target.value = "";
          if (file) onPick(file);
        }}
      />
    </>
  );
}

function Fact({
  icon: Icon,
  label,
  value,
  className,
}: {
  icon: typeof Building2;
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <dt className="flex items-center gap-1.5 text-sm text-ink-muted">
        <Icon className="size-3.5 shrink-0" aria-hidden />
        {label}
      </dt>
      <dd className="mt-0.5 font-medium text-ink">{value}</dd>
    </div>
  );
}
