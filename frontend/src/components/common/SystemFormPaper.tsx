"use client";

import { ArrowLeft, Check, PenLine, Printer, UserCog } from "lucide-react";
import Link from "next/link";
import { type ReactNode, useCallback, useEffect, useState } from "react";

import { Logo } from "@/components/brand/Logo";
import { Mascot } from "@/components/brand/Mascot";
import { SignaturePad } from "@/components/common/SignaturePad";
import { StatusPill } from "@/components/common/StatusPill";
import { ApiError } from "@/lib/api";
import { fetchDocumentFileUrl, thaiDate } from "@/lib/applications";
import {
  type SystemForm,
  formatJuristicNo,
  getSystemForm,
  saveSignature,
  updateApplicant,
} from "@/lib/systemForm";
import { cn } from "@/lib/utils";
import type { DocumentStatus } from "@/types/enums";

/**
 * โครงกระดาษของแบบฟอร์มที่ระบบกรอกให้ (A01 หนังสือแจ้งฯ / A06 ร.ร.1)
 *
 * ทั้งสองฉบับใช้ทุกอย่างร่วมกันยกเว้นเนื้อความตรงกลาง จึงรวมไว้ที่นี่ที่เดียว:
 * โหลดข้อมูล ปุ่มพิมพ์ หัวกระดาษ ช่องลงชื่อ การแก้ชื่อผู้ยื่น และแผงลงลายมือชื่อ
 * หน้าของแต่ละแบบฟอร์มส่งมาแค่ `body` ซึ่งเป็นข้อความในแบบฟอร์มฉบับนั้น
 *
 * ใช้การพิมพ์ของเบราว์เซอร์แทนการสร้าง PDF ฝั่งเซิร์ฟเวอร์ ด้วยเหตุผลเดียวกับ
 * หน้าใบอนุญาต (M10) — หน้าต่างพิมพ์ของทุกเบราว์เซอร์มีปุ่ม "บันทึกเป็น PDF"
 * อยู่แล้ว จึงไม่ต้องเพิ่มไลบรารีและไม่ต้องสู้กับฟอนต์ไทยในไฟล์ PDF
 *
 * คลาส print:hidden คือสิ่งที่หายไปตอนพิมพ์ (ปุ่ม ลิงก์ และแผงแก้ไขทั้งหมด)
 */
type Props = {
  applicationNo: string;
  code: string;
  /** คำเรียกผู้ลงชื่อบนกระดาษ — หนังสือแจ้งฯ ใช้ "ผู้แจ้ง" ส่วน ร.ร.1 ใช้ "ผู้ขออนุญาต" */
  signerLabel: string;
  body: (form: SystemForm) => ReactNode;
};

export function SystemFormPaper({ applicationNo, code, signerLabel, body }: Props) {
  const [form, setForm] = useState<SystemForm | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [signatureUrl, setSignatureUrl] = useState<string | null>(null);

  const load = useCallback(
    () =>
      getSystemForm(applicationNo, code)
        .then(setForm)
        .catch((err) =>
          setError(err instanceof ApiError ? err.message : "เปิดแบบฟอร์มไม่ได้ กรุณาลองใหม่"),
        ),
    [applicationNo, code],
  );

  useEffect(() => {
    load();
  }, [load]);

  // รูปลายมือชื่อต้องโหลดพร้อม token จึงเป็น object URL ที่ต้องคืนหน่วยความจำเอง
  useEffect(() => {
    const fileId = form?.signature?.file_id;
    let url: string | null = null;
    let cancelled = false;

    if (fileId !== undefined) {
      fetchDocumentFileUrl(applicationNo, fileId)
        .then((created) => {
          url = created;
          if (cancelled) URL.revokeObjectURL(created);
          else setSignatureUrl(created);
        })
        // โหลดรูปไม่ได้ไม่ควรทำให้ทั้งหน้าพัง แบบฟอร์มยังพิมพ์ได้โดยเว้นช่องเซ็นไว้
        .catch(() => setSignatureUrl(null));
    }

    return () => {
      cancelled = true;
      // เคลียร์ state พร้อมคืนหน่วยความจำ ไม่งั้น <img> จะชี้ไปยัง URL ที่ถูกยกเลิกแล้ว
      setSignatureUrl(null);
      if (url) URL.revokeObjectURL(url);
    };
  }, [applicationNo, form?.signature?.file_id]);

  if (error) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center">
        <Mascot pose="support" size="md" className="mx-auto w-40" />
        <h1 className="mt-6 text-2xl font-bold text-ink">เปิดแบบฟอร์มนี้ไม่ได้</h1>
        <p role="alert" className="mt-2 text-ink-muted">
          {error}
        </p>
        <BackLink applicationNo={applicationNo} className="mt-6" />
      </main>
    );
  }

  if (!form) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center text-ink-muted">
        กำลังโหลดแบบฟอร์ม…
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-8 sm:py-12 print:max-w-none print:p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 print:hidden">
        <BackLink applicationNo={applicationNo} />
        <button
          type="button"
          onClick={() => window.print()}
          className="inline-flex min-h-12 items-center gap-2 rounded-xl bg-brand-500 px-5 py-3 font-semibold text-white hover:bg-brand-400"
        >
          <Printer className="size-5" aria-hidden />
          พิมพ์ / บันทึกเป็น PDF
        </button>
      </div>

      <p className="mt-3 text-sm text-ink-muted print:hidden">
        กดปุ่มพิมพ์แล้วเลือกปลายทางเป็น “บันทึกเป็น PDF” เพื่อเก็บไฟล์ไว้ยื่นหรือส่งต่อ
      </p>

      {/* ---------- ตัวกระดาษ ---------- */}
      <article className="mt-5 rounded-card border border-line bg-surface p-8 text-ink print:mt-0 print:rounded-none print:border-0 print:p-0">
        <header className="flex items-start justify-between gap-4 border-b border-line pb-5">
          <Logo className="h-12 w-auto" />
          <div className="text-right text-sm text-ink-muted">
            <p>เลขที่คำขอ</p>
            <p className="font-mono text-base font-bold text-ink">{form.application_no}</p>
          </div>
        </header>

        <h1 className="mt-6 text-center text-xl font-bold sm:text-2xl">{form.title}</h1>

        <div className="mt-6 space-y-1 text-right text-sm">
          <p>
            เขียนที่ <Fill value={form.local_authority_name} />
          </p>
          <p>
            วันที่ <Fill value={form.filed_on ? thaiDate(form.filed_on) : null} />
          </p>
        </div>

        <div className="mt-6 space-y-4 leading-loose">{body(form)}</div>

        {/* ---------- ช่องลงลายมือชื่อ ---------- */}
        <div className="mt-10 flex justify-end">
          <div className="w-72 text-center">
            <div className="flex h-24 items-end justify-center">
              {signatureUrl ? (
                // ใช้ <img> ธรรมดา ไม่ใช่ next/image เพราะต้นทางเป็น blob: ของ
                // ไฟล์ที่โหลดมาพร้อม token ไม่ใช่ URL ที่ตัว optimizer เข้าถึงได้
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={signatureUrl}
                  alt={`ลายมือชื่อของ ${form.applicant.display_name}`}
                  className="max-h-24 w-auto object-contain"
                />
              ) : (
                <span className="pb-2 text-sm text-ink-muted print:hidden">
                  (ยังไม่ได้ลงลายมือชื่อ)
                </span>
              )}
            </div>
            <p className="border-t border-dotted border-ink/60 pt-2">ลงชื่อ {signerLabel}</p>
            <p className="mt-1">( {form.applicant.display_name} )</p>
          </div>
        </div>

        <footer className="mt-10 border-t border-line pt-4 text-xs text-ink-muted">
          <p>แบบฟอร์มนี้สร้างจากข้อมูลคำขอเลขที่ {form.application_no} ในระบบ HoTLinE Doc</p>
          <p className="mt-1">ต้นแบบสำหรับการสาธิต ข้อมูลทั้งหมดเป็นข้อมูลจำลอง</p>
        </footer>
      </article>

      <ApplicantPanel form={form} applicationNo={applicationNo} onSaved={load} />

      {/* ---------- ส่วนที่ไม่ถูกพิมพ์: ลงลายมือชื่อในระบบ ---------- */}
      <section className="mt-6 rounded-card border border-line bg-surface p-5 shadow-card print:hidden">
        <div className="flex flex-wrap items-center gap-2">
          <PenLine className="size-5 text-brand-600" aria-hidden />
          <h2 className="text-lg font-semibold">ลายมือชื่อ{signerLabel}</h2>
          {form.signature && (
            <StatusPill status={form.signature.status as DocumentStatus} className="ml-auto" />
          )}
        </div>

        {form.signature ? (
          <p className="mt-2 text-sm text-ink-muted">
            ลงลายมือชื่อไว้แล้วเมื่อ {thaiDate(form.signature.signed_at)}
            {form.signature.version_no > 1 && ` (รุ่นที่ ${form.signature.version_no})`} —
            ลายมือชื่อจะปรากฏบนแบบฟอร์มด้านบนทั้งบนหน้าจอและตอนพิมพ์
          </p>
        ) : (
          <p className="mt-2 text-sm text-ink-muted">
            <span className="font-medium text-warn-fg">ต้องลงลายมือชื่อก่อนจึงจะยื่นคำขอได้</span>{" "}
            เพราะลายมือชื่อเป็นสิ่งที่ทำให้เอกสารฉบับนี้มีผล ถ้าถนัดเซ็นบนกระดาษ
            ให้พิมพ์ออกไปเซ็นแล้วถ่ายรูปมาอัปโหลดได้
          </p>
        )}

        {form.can_sign ? (
          <SignaturePad
            className="mt-4"
            onSave={async (png) => {
              await saveSignature(applicationNo, png, form.form_code);
              await load();
            }}
          />
        ) : (
          <p className="mt-4 rounded-xl bg-canvas px-4 py-3 text-sm text-ink-muted">
            คำขอนี้ยื่นไปแล้ว จึงแก้ลายมือชื่อไม่ได้ หากเจ้าหน้าที่ขอให้แก้ไข
            ระบบจะเปิดให้ลงลายมือชื่อใหม่เอง
          </p>
        )}
      </section>
    </main>
  );
}

/**
 * แผงแก้ชื่อผู้ยื่นบนแบบฟอร์ม
 *
 * ตอนสมัคร ระบบตั้งชื่อผู้ประกอบการให้เท่ากับชื่อ-นามสกุลของผู้สมัครไปก่อน
 * แต่แบบ ร.ร.1 มีช่องให้ระบุว่ายื่นในนามบุคคลธรรมดาหรือนิติบุคคล
 * ผู้ยื่นจึงต้องแก้ได้เอง ไม่ใช่ต้องให้คนแก้ในฐานข้อมูลให้
 */
function ApplicantPanel({
  form,
  applicationNo,
  onSaved,
}: {
  form: SystemForm;
  applicationNo: string;
  onSaved: () => Promise<unknown>;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState(form.applicant.display_name);
  const [juristic, setJuristic] = useState(form.applicant.is_juristic);
  const [regNo, setRegNo] = useState(form.applicant.juristic_reg_no ?? "");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setError(null);
    setPending(true);
    try {
      await updateApplicant(applicationNo, {
        display_name: name.trim(),
        is_juristic: juristic,
        juristic_reg_no: juristic ? regNo : null,
      });
      await onSaved();
      setOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "บันทึกไม่สำเร็จ กรุณาลองใหม่อีกครั้ง");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="mt-6 rounded-card border border-line bg-surface p-5 shadow-card print:hidden">
      <div className="flex flex-wrap items-center gap-2">
        <UserCog className="size-5 text-brand-600" aria-hidden />
        <h2 className="text-lg font-semibold">ชื่อผู้ยื่นบนแบบฟอร์ม</h2>
        {form.can_sign && !open && (
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="ml-auto min-h-9 text-sm font-semibold text-brand-600 underline underline-offset-4"
          >
            แก้ไข
          </button>
        )}
      </div>

      {!open && (
        <p className="mt-2 text-sm text-ink-muted">
          {form.applicant.display_name} ·{" "}
          {form.applicant.is_juristic
            ? `นิติบุคคล ทะเบียนเลขที่ ${formatJuristicNo(form.applicant.juristic_reg_no)}`
            : "บุคคลธรรมดา"}
        </p>
      )}

      {open && (
        <div className="mt-4 space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-ink">ชื่อผู้ยื่น (บุคคลหรือนิติบุคคล)</span>
            <input
              type="text"
              value={name}
              maxLength={160}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 min-h-12 w-full rounded-xl border border-line bg-canvas px-3 py-2 text-ink"
            />
          </label>

          <fieldset>
            <legend className="text-sm font-medium text-ink">ยื่นในนาม</legend>
            <div className="mt-1 flex flex-wrap gap-4">
              {[
                { value: false, label: "บุคคลธรรมดา" },
                { value: true, label: "นิติบุคคล" },
              ].map((option) => (
                <label key={String(option.value)} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="applicant-kind"
                    checked={juristic === option.value}
                    onChange={() => setJuristic(option.value)}
                    className="size-4"
                  />
                  <span className="text-sm">{option.label}</span>
                </label>
              ))}
            </div>
          </fieldset>

          {juristic && (
            <label className="block">
              <span className="text-sm font-medium text-ink">เลขทะเบียนนิติบุคคล 13 หลัก</span>
              {/* รับตัวเลขล้วน ไม่แทรกขีดระหว่างพิมพ์ เพราะเคอร์เซอร์จะกระโดดจนเลขสลับ */}
              <input
                type="text"
                inputMode="numeric"
                value={regNo}
                maxLength={13}
                onChange={(e) => setRegNo(e.target.value.replace(/\D/g, ""))}
                className="mt-1 min-h-12 w-full rounded-xl border border-line bg-canvas px-3 py-2 font-mono text-ink"
              />
              <span className="mt-1 block text-xs text-ink-muted">
                {regNo.length === 13 ? formatJuristicNo(regNo) : `กรอกแล้ว ${regNo.length} จาก 13 หลัก`}
              </span>
            </label>
          )}

          {error && (
            <p role="alert" className="rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger-fg">
              {error}
            </p>
          )}

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={save}
              disabled={pending || !name.trim()}
              className="inline-flex min-h-11 items-center rounded-xl bg-brand-500 px-4 py-2.5 font-semibold text-white hover:bg-brand-400 disabled:opacity-50"
            >
              {pending ? "กำลังบันทึก…" : "บันทึก"}
            </button>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="inline-flex min-h-11 items-center rounded-xl border border-line px-4 py-2.5 font-semibold text-ink hover:bg-canvas"
            >
              ยกเลิก
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

function BackLink({ applicationNo, className }: { applicationNo: string; className?: string }) {
  return (
    <Link
      href={`/operator/applications/${applicationNo}`}
      className={cn(
        "inline-flex items-center gap-2 text-sm font-semibold text-brand-600 underline underline-offset-4",
        className,
      )}
    >
      <ArrowLeft className="size-4" aria-hidden />
      กลับไปหน้าคำขอ
    </Link>
  );
}

/** ช่องกรอกบนกระดาษ — มีค่าก็พิมพ์ค่านั้น ไม่มีก็เว้นเส้นไว้ให้เขียนด้วยปากกา */
export function Fill({ value, className }: { value?: string | null; className?: string }) {
  return (
    <span
      className={cn(
        "inline-block min-w-40 border-b border-dotted border-ink/50 px-2 text-center font-medium",
        className,
      )}
    >
      {value || " "}
    </span>
  );
}

/** ช่องติ๊กบนกระดาษ — ระบบติ๊กให้จากข้อมูลที่มี ผู้ใช้ไม่ต้องติ๊กเอง */
export function Tick({ checked, label }: { checked: boolean; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={cn(
          "grid size-4 shrink-0 place-items-center border",
          checked ? "border-ink bg-ink/5" : "border-ink/40",
        )}
        aria-hidden
      >
        {checked && <Check className="size-3" />}
      </span>
      {/* NFR Accessibility: เครื่องหมายถูกเป็นภาพ จึงต้องมีข้อความบอกสถานะด้วย */}
      <span>
        {label}
        <span className="sr-only">{checked ? " (เลือก)" : " (ไม่ได้เลือก)"}</span>
      </span>
    </span>
  );
}

export function Item({
  no,
  label,
  children,
}: {
  no: number;
  label: string;
  children: ReactNode;
}) {
  return (
    <li className="flex flex-wrap items-baseline gap-x-2">
      <span className="font-medium">
        {no}. {label}
      </span>
      {children}
    </li>
  );
}
