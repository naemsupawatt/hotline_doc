"use client";

import {
  ArrowRight,
  Building2,
  CheckCircle2,
  Clock,
  FileText,
  Landmark,
  MapPin,
  PencilLine,
  RotateCcw,
  Upload,
} from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Mascot } from "@/components/brand/Mascot";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { Stepper } from "@/components/common/Stepper";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError } from "@/lib/api";
import {
  ACCOMMODATION_KINDS,
  type AccommodationKind,
  type AddressInput,
  startApplication,
} from "@/lib/applications";
import { getUser } from "@/lib/auth";
import {
  type ClassifyResult,
  type LocalAuthority,
  type RequiredDocument,
  classify,
  describeAccepted,
  listLocalAuthorities,
} from "@/lib/wizard";

const STEPS = [{ label: "ข้อมูลที่พักและบริการ" }, { label: "ผลประเมินและเอกสาร" }];

/** คำตอบทั้งหมดของ wizard เก็บไว้ที่ตัวหน้า เพราะขั้น "เริ่มยื่นคำขอ" ต้องใช้ค่าชุดเดียวกัน
    ส่งซ้ำไปให้เซิร์ฟเวอร์จำแนกใหม่ ไม่ได้ส่งผลจำแนกที่ได้มาแล้วกลับไป */
export type Answers = {
  rooms: string;
  guests: string;
  hasRestaurant: boolean;
  authorityId: string;
};

const EMPTY: Answers = { rooms: "", guests: "", hasRestaurant: false, authorityId: "" };

const EMPTY_ADDRESS: AddressInput = {
  address_no: "",
  moo: "",
  soi: "",
  road: "",
  sub_district: "",
  district: "",
  postal_code: "",
};

export function WizardView() {
  const [result, setResult] = useState<ClassifyResult | null>(null);
  const [answers, setAnswers] = useState<Answers>(EMPTY);
  const [authorities, setAuthorities] = useState<LocalAuthority[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  // อปท. 19 แห่งมาจากฐานข้อมูล ไม่ได้เขียนตายตัวไว้ในหน้าเว็บ (ข้อ 4 ของโจทย์)
  // ดึงที่ตัวหน้าเพราะใช้สองที่: ช่องเลือกพื้นที่ และรายการอำเภอในฟอร์มที่อยู่
  useEffect(() => {
    listLocalAuthorities()
      .then(setAuthorities)
      .catch(() => setLoadError("โหลดรายชื่อหน่วยงานท้องถิ่นไม่ได้ กรุณารีเฟรชหน้าอีกครั้ง"));
  }, []);

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <PageHeader
        eyebrow="01 / ประเมินที่พัก"
        title="ที่พักของคุณต้องดำเนินการอะไร?"
        description="ตอบข้อมูลเบื้องต้น เพื่อรับแนวทางการดำเนินการตามกฎหมายอย่างเข้าใจง่าย"
      />

      <Stepper steps={STEPS} current={result ? 1 : 0} className="mt-8 max-w-xl rounded-2xl border border-line bg-surface px-5 py-5" />

      <div className="mt-6 grid items-start gap-6 xl:grid-cols-[1.2fr_1fr]">
        <AssessmentForm
          answers={answers}
          onAnswersChange={(next) => { setAnswers(next); setResult(null); }}
          onResult={setResult}
          onReset={() => setResult(null)}
          authorities={authorities}
          loadError={loadError}
        />
        <ResultPanel result={result} />
      </div>

      {result && <DocumentChecklist result={result} />}
      {result && (
        <StartApplicationSection answers={answers} result={result} authorities={authorities} />
      )}
    </main>
  );
}

/* ------------------------------------------------------------------ ฟอร์ม */

type FormProps = {
  answers: Answers;
  onAnswersChange: (a: Answers) => void;
  onResult: (r: ClassifyResult) => void;
  onReset: () => void;
  authorities: LocalAuthority[];
  loadError: string | null;
};

function AssessmentForm({
  answers,
  onAnswersChange,
  onResult,
  onReset,
  authorities,
  loadError,
}: FormProps) {
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const error = submitError ?? loadError;
  const setError = setSubmitError;
  const hasRestaurant = answers.hasRestaurant;
  const authorityId = answers.authorityId;
  const setHasRestaurant = (v: boolean) => onAnswersChange({ ...answers, hasRestaurant: v });
  const setAuthorityId = (v: string) => onAnswersChange({ ...answers, authorityId: v });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    onReset();

    const rooms = Number(answers.rooms);
    const guests = Number(answers.guests);

    // ตรวจฝั่งนี้ก่อนยิง API เพื่อให้ผู้ใช้รู้ผลทันที ไม่ใช่เพื่อแทนการตรวจฝั่งเซิร์ฟเวอร์
    if (!Number.isInteger(rooms) || rooms < 1) {
      setError("กรุณากรอกจำนวนห้องพักเป็นตัวเลขตั้งแต่ 1 ห้องขึ้นไป");
      return;
    }
    if (!Number.isInteger(guests) || guests < 1) {
      setError("กรุณากรอกจำนวนผู้เข้าพักเป็นตัวเลขตั้งแต่ 1 คนขึ้นไป");
      return;
    }

    setPending(true);
    try {
      onResult(
        await classify({
          rooms,
          guests,
          has_restaurant: hasRestaurant,
          local_authority_id: authorityId ? Number(authorityId) : null,
        }),
      );
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "เชื่อมต่อระบบไม่ได้ กรุณาตรวจสอบอินเทอร์เน็ตแล้วลองใหม่อีกครั้ง",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="rounded-card border border-line bg-surface p-5 shadow-card sm:p-7">
      <div className="grid gap-5 sm:grid-cols-2">
        <TextField
          label="จำนวนห้องพัก"
          icon={Building2}
          inputMode="numeric"
          placeholder="20"
          hint="นับทุกห้องที่ให้ผู้เข้าพักใช้"
          value={answers.rooms}
          onChange={(e) =>
            onAnswersChange({ ...answers, rooms: e.target.value.replace(/\D/g, "").slice(0, 4) })
          }
        />
        <TextField
          label="จำนวนผู้เข้าพักสูงสุด"
          inputMode="numeric"
          placeholder="40"
          hint="จำนวนคนที่รับได้พร้อมกันทั้งหมด"
          value={answers.guests}
          onChange={(e) =>
            onAnswersChange({ ...answers, guests: e.target.value.replace(/\D/g, "").slice(0, 5) })
          }
        />
      </div>

      <fieldset className="mt-6">
        <legend className="text-sm font-semibold text-ink">มีห้องอาหารหรือไม่</legend>
        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          <ChoiceCard
            checked={!hasRestaurant}
            onSelect={() => setHasRestaurant(false)}
            title="ไม่มี"
            description="ไม่มีการให้บริการห้องอาหารในสถานประกอบการ"
          />
          <ChoiceCard
            checked={hasRestaurant}
            onSelect={() => setHasRestaurant(true)}
            title="มี"
            description="มีการให้บริการห้องอาหารในสถานประกอบการ"
          />
        </div>
      </fieldset>

      <div className="mt-6 space-y-2">
        <label htmlFor="authority" className="block text-sm font-semibold text-ink">
          พื้นที่ตั้งสถานประกอบการ
        </label>
        <select
          id="authority"
          value={authorityId}
          onChange={(e) => setAuthorityId(e.target.value)}
          aria-describedby="authority-hint"
          className="min-h-12 w-full rounded-xl border border-line bg-canvas px-4 py-3 text-base text-ink"
        >
          <option value="">เลือกองค์กรปกครองส่วนท้องถิ่น</option>
          {authorities.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name} ({a.district})
            </option>
          ))}
        </select>
        <p id="authority-hint" className="text-sm text-ink-muted">
          ใช้บอกว่าเอกสารที่ต้องขอจากหน่วยงานอื่น ต้องไปติดต่อที่ใด
        </p>
      </div>

      {error && (
        <p
          role="alert"
          className="mt-5 rounded-xl bg-danger-bg px-4 py-3 text-sm font-medium text-danger-fg"
        >
          {error}
        </p>
      )}

      <Button type="submit" disabled={pending} className="mt-6">
        {pending ? "กำลังประเมิน…" : "ดูแนวทางของฉัน"}
        {pending ? null : <ArrowRight className="size-5" aria-hidden />}
      </Button>
    </form>
  );
}

function ChoiceCard({
  checked,
  onSelect,
  title,
  description,
}: {
  checked: boolean;
  onSelect: () => void;
  title: string;
  description: string;
}) {
  return (
    <label
      className={[
        "flex cursor-pointer gap-3 rounded-xl border-2 p-4 transition-colors",
        checked ? "border-brand-500 bg-brand-50/60" : "border-line bg-surface hover:border-brand-200",
      ].join(" ")}
    >
      <input
        type="radio"
        name="has_restaurant"
        checked={checked}
        onChange={onSelect}
        className="mt-0.5 size-5 shrink-0 accent-brand-500"
      />
      <span className="min-w-0">
        <span className="block font-semibold text-ink">{title}</span>
        <span className="mt-0.5 block text-sm text-ink-muted">{description}</span>
      </span>
    </label>
  );
}

/* --------------------------------------------------------------- ผลประเมิน */

function ResultPanel({ result }: { result: ClassifyResult | null }) {
  if (!result) return <EmptyResult />;

  return (
    <div className="rounded-card border border-brand-100 bg-brand-50 p-6 shadow-card">
      <div className="flex items-start gap-4">
        <span className="grid size-14 shrink-0 place-items-center rounded-2xl bg-surface text-brand-500">
          <FileText className="size-7" aria-hidden />
        </span>
        <div className="min-w-0">
          <h2 className="text-2xl font-bold text-ink">{result.property_type_name}</h2>
          <p className="mt-1 text-ink-muted">{result.outcome_message}</p>
        </div>
      </div>

      {/* M2 บังคับให้บอก "เหตุผลว่าทำไมจึงได้ผลนั้น" ไม่ใช่แค่ชื่อประเภท */}
      <div className="mt-5 rounded-xl border border-line bg-surface p-4">
        <p className="flex items-center gap-2 text-sm font-semibold text-ink">
          <CheckCircle2 className="size-4 text-brand-500" aria-hidden />
          ระบบสรุปแบบนี้เพราะ
        </p>
        <p className="mt-1.5 text-ink">{result.reason}</p>
        {result.matched_rule_code && (
          <p className="mt-2 text-xs text-ink-muted">
            ตัดสินด้วยเกณฑ์รหัส <span className="font-mono">{result.matched_rule_code}</span>{" "}
            ซึ่งผู้ดูแลระบบแก้ไขได้เองโดยไม่ต้องแก้โปรแกรม
          </p>
        )}
      </div>

      {result.fee && (
        <div className="mt-3 flex flex-wrap items-baseline gap-x-2 rounded-xl border border-line bg-surface p-4">
          <span className="text-sm font-semibold text-ink">ค่าธรรมเนียม</span>
          <span className="text-2xl font-bold text-brand-600">
            {result.fee.amount.toLocaleString("th-TH")} บาท
          </span>
          <span className="text-sm text-ink-muted">ต่อระยะเวลา {result.fee.validity_years} ปี</span>
        </div>
      )}

      {result.is_out_of_scope && (
        <p className="mt-3 rounded-xl bg-warn-bg px-4 py-3 text-sm text-ink">
          กรณีนี้อยู่นอกขอบเขตของระบบในระยะนี้ กรุณาติดต่อนายทะเบียนโดยตรง
        </p>
      )}
    </div>
  );
}

function EmptyResult() {
  return (
    <aside className="rounded-card border border-brand-100 bg-brand-50 p-6 sm:p-7">
      <p className="text-xs font-semibold text-brand-700">เริ่มต้นอย่างมั่นใจ</p>
      <h2 className="mt-2 text-2xl font-bold text-navy-900">เรื่องเอกสารที่พัก<br />ให้เราช่วยวางแผน</h2>
      <p className="mt-3 text-sm leading-relaxed text-ink-muted">กรอกข้อมูลที่พักของคุณ แล้วระบบจะสรุปแนวทางที่เหมาะกับที่พักให้ในขั้นตอนถัดไป</p>
      <div className="mt-5 space-y-3 rounded-xl border border-brand-100 bg-surface/90 p-4">
        {[
          { icon: Building2, text: "รู้ว่าที่พักเข้าข่ายประเภทใด" },
          { icon: FileText, text: "เห็นรายการเอกสารที่ต้องเตรียม" },
          { icon: Landmark, text: "รู้จุดติดต่อหน่วยงานที่เกี่ยวข้อง" },
        ].map(({ icon: ItemIcon, text }) => {
          return <p key={text} className="flex items-center gap-3 text-sm text-navy-700"><ItemIcon className="size-5 shrink-0 text-brand-600" aria-hidden />{text}</p>;
        })}
      </div>
      <div className="mt-5 flex items-center justify-center gap-4">
        <Mascot pose="wave" size="md" className="w-28" />
        <p className="text-sm leading-relaxed font-medium text-brand-700">เอกสารพร้อม<br />ก้าวต่อได้อย่างมั่นใจ</p>
      </div>
    </aside>
  );
}

/* ------------------------------------------------------- รายการเอกสาร 2 หมวด */

function DocumentChecklist({ result }: { result: ClassifyResult }) {
  const { self_service, external, needs_local_authority } = result.documents;

  if (self_service.length === 0 && external.length === 0) {
    return (
      <p className="mt-8 rounded-card border border-line bg-warn-bg px-5 py-4 text-ink">
        ยังไม่มีการกำหนดรายการเอกสารสำหรับประเภทนี้ในระบบ
        กรุณาติดต่อเจ้าหน้าที่เพื่อขอรายการเอกสาร
      </p>
    );
  }

  return (
    <div className="mt-10">
      <h2 className="text-xl font-bold text-ink">เอกสารที่ต้องเตรียม</h2>
      <p className="mt-1 text-ink-muted">
        แบ่งเป็น 2 หมวด เพื่อให้รู้ตั้งแต่ต้นว่าฉบับใดทำเองได้ และฉบับใดต้องเผื่อเวลาไปติดต่อหน่วยงาน
      </p>

      <div className="mt-5 grid gap-6 lg:grid-cols-2">
        <SectionCard
          icon={PencilLine}
          tone="brand"
          title="ทำเองได้เลย"
          description="เตรียมและอัปโหลดเอกสารด้วยตัวเอง ผ่านระบบ HoTLinE Doc"
        >
          <div className="space-y-3">
            {self_service.map((doc) => (
              <DocumentCard key={doc.code} doc={doc} />
            ))}
          </div>
        </SectionCard>

        <SectionCard
          icon={Landmark}
          tone="info"
          title="ต้องไปขอก่อน"
          description="ติดต่อหน่วยงานที่เกี่ยวข้อง เพื่อขอเอกสารจากภายนอก"
        >
          {needs_local_authority && (
            <p className="mb-3 rounded-xl bg-warn-bg px-4 py-3 text-sm text-ink">
              เลือกพื้นที่ตั้งสถานประกอบการด้านบนก่อน ระบบจึงจะบอกได้ว่าต้องไปติดต่อที่ใด
            </p>
          )}
          <div className="space-y-3">
            {external.map((doc) => (
              <DocumentCard key={doc.code} doc={doc} />
            ))}
          </div>
        </SectionCard>
      </div>

      <p className="mt-6 flex items-start gap-2 text-sm text-ink-muted">
        <RotateCcw className="mt-0.5 size-4 shrink-0" aria-hidden />
        เกณฑ์ ค่าใช้จ่าย และระยะเวลาเป็นข้อมูลตั้งต้นสำหรับการสาธิต
        ผู้ดูแลระบบแก้ไขได้เองเมื่อระเบียบเปลี่ยน
      </p>
    </div>
  );
}

function DocumentCard({ doc }: { doc: RequiredDocument }) {
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
            {doc.is_system_form && (
              <span className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700">
                กรอกในระบบ
              </span>
            )}
            {doc.allows_multiple && (
              <span className="rounded-full bg-info-bg px-2 py-0.5 text-xs font-medium text-info-fg">
                แนบได้หลายไฟล์
              </span>
            )}
          </div>

          {doc.description && <p className="mt-1 text-sm text-ink-muted">{doc.description}</p>}

          <p className="mt-1.5 flex items-center gap-1.5 text-sm text-ink-muted">
            {doc.is_system_form ? (
              <PencilLine className="size-3.5 shrink-0" aria-hidden />
            ) : (
              <Upload className="size-3.5 shrink-0" aria-hidden />
            )}
            {doc.is_system_form
              ? "ระบบสร้างเอกสารให้จากข้อมูลที่กรอก"
              : describeAccepted(doc.accepted_mime)}
          </p>
        </div>
      </div>

      {doc.contact_point && <ContactBlock contact={doc.contact_point} note={doc.preparation_note} />}

      {/* หมวดต้องไปขอ แต่ยังไม่รู้เขต — บอกเท่าที่รู้ ไม่เดาที่อยู่ให้ผิดเขต */}
      {!doc.contact_point && doc.estimated_days && (
        <p className="mt-2 flex items-center gap-1.5 text-sm text-ink-muted">
          <Clock className="size-3.5 shrink-0" aria-hidden />
          ใช้เวลาประมาณ {doc.estimated_days} วัน
        </p>
      )}
    </article>
  );
}

function ContactBlock({ contact, note }: { contact: RequiredDocument["contact_point"]; note: string | null }) {
  if (!contact) return null;
  return (
    <div className="mt-3 rounded-lg bg-info-bg/40 p-3">
      <p className="flex items-start gap-1.5 text-sm font-semibold text-ink">
        <MapPin className="mt-0.5 size-4 shrink-0 text-info-fg" aria-hidden />
        ไปติดต่อที่ {contact.office_name}
      </p>
      <dl className="mt-1.5 space-y-1 text-sm text-ink-muted">
        {contact.office_hours && (
          <div className="flex gap-1.5">
            <dt className="shrink-0">เวลาทำการ</dt>
            <dd>{contact.office_hours}</dd>
          </div>
        )}
        {contact.estimated_days && (
          <div className="flex gap-1.5">
            <dt className="shrink-0">ใช้เวลาประมาณ</dt>
            <dd>{contact.estimated_days} วัน</dd>
          </div>
        )}
        {note && (
          <div className="flex gap-1.5">
            <dt className="shrink-0">เตรียมไปด้วย</dt>
            <dd>{note}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}


/* --------------------------------------------------------- เริ่มยื่นคำขอ (M6) */

/**
 * เข้าสู่ระบบอยู่หรือไม่ — อ่านจาก storage ซึ่งเป็น external store ของฝั่งเบราว์เซอร์
 *
 * ใช้ useSyncExternalStore แทน useEffect + setState เพราะ:
 *   - ฝั่งเซิร์ฟเวอร์ไม่มี storage จึงต้องมี snapshot แยก (คืน false) กัน hydration พัง
 *   - ถ้าผู้ใช้ล็อกอิน/ออกจากระบบในแท็บอื่น หน้านี้อัปเดตตามทันที
 */
function subscribeToAuth(onChange: () => void) {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function useSignedIn(): boolean {
  return useSyncExternalStore(
    subscribeToAuth,
    () => getUser() !== null,
    () => false,
  );
}

/**
 * ขั้นสุดท้ายของ wizard: เก็บข้อมูลที่พักที่ยังไม่ได้ถาม แล้วเปิดคำขอ
 *
 * สามช่องนี้ (ชื่อสถานที่ ที่อยู่ ลักษณะที่พัก) คือช่องในแบบหนังสือแจ้งฯ (A01)
 * เก็บตั้งแต่ตอนเปิดคำขอ เพื่อให้ระบบสร้างแบบฟอร์มนั้นให้ได้เลยโดยไม่ต้องถามซ้ำ
 */
function StartApplicationSection({
  answers,
  result,
  authorities,
}: {
  answers: Answers;
  result: ClassifyResult;
  authorities: LocalAuthority[];
}) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [address, setAddress] = useState<AddressInput>(EMPTY_ADDRESS);
  const [kind, setKind] = useState<AccommodationKind>("detached_house");
  const [kindOther, setKindOther] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const signedIn = useSignedIn();

  // รายชื่ออำเภอมาจากข้อมูล อปท. ในฐานข้อมูล ไม่ได้พิมพ์ไว้ในหน้าเว็บ
  // ตัด "ทั้งจังหวัด" ของ อบจ. ออก เพราะไม่ใช่ชื่ออำเภอจริง
  const districts = [...new Set(authorities.map((a) => a.district))]
    .filter((d) => d !== "ทั้งจังหวัด")
    .sort((a, b) => a.localeCompare(b, "th"));

  // เติมอำเภอให้ล่วงหน้าจาก อปท. ที่เลือกไว้ ผู้ใช้แก้เองได้
  // (ที่พักใต้ อบจ. ซึ่งครอบทั้งจังหวัด จะไม่ถูกเติมให้ ต้องเลือกเอง)
  //
  // คำนวณตอน render ไม่ sync ลง state ด้วย useEffect เพราะค่านี้เป็นค่าที่
  // "ได้จากข้อมูลอื่น" อยู่แล้ว การเก็บซ้ำลง state จะทำให้ต้องคอยไล่ให้ตรงกัน
  const selectedAuthority = authorities.find((a) => String(a.id) === answers.authorityId);
  const suggestedDistrict =
    selectedAuthority && selectedAuthority.district !== "ทั้งจังหวัด"
      ? selectedAuthority.district
      : "";

  // ค่าที่ผู้ใช้เลือกเองมาก่อนเสมอ ถ้ายังไม่เลือกจึงใช้ค่าที่เดาให้
  const effectiveAddress: AddressInput = {
    ...address,
    district: address.district || suggestedDistrict,
  };

  // เกินขอบเขตของระบบ: เซิร์ฟเวอร์ไม่เปิดคำขอให้อยู่แล้ว จึงไม่ต้องขึ้นฟอร์มให้เสียเวลากรอก
  if (result.is_out_of_scope) return null;

  if (!signedIn) {
    return (
      <SectionCard
        icon={FileText}
        tone="brand"
        title="เริ่มยื่นคำขอ"
        description="เข้าสู่ระบบก่อน เพื่อให้ระบบเก็บคำขอและเอกสารของคุณไว้ติดตามได้"
        className="mt-8"
      >
        <div className="flex flex-wrap gap-3">
          <Link
            href="/login"
            className="inline-flex min-h-12 items-center justify-center rounded-xl bg-brand-500 px-5 py-3 font-semibold text-white hover:bg-brand-400"
          >
            เข้าสู่ระบบ
          </Link>
          <Link
            href="/register"
            className="inline-flex min-h-12 items-center justify-center rounded-xl border-2 border-brand-500 bg-surface px-5 py-3 font-semibold text-brand-600 hover:bg-brand-50"
          >
            สมัครสมาชิก
          </Link>
        </div>
        <p className="mt-3 text-sm text-ink-muted">
          ผลประเมินด้านบนดูได้โดยไม่ต้องเข้าสู่ระบบ ส่วนการยื่นคำขอต้องระบุตัวตนผู้ยื่น
        </p>
      </SectionCard>
    );
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!name.trim()) return setError("กรุณากรอกชื่อสถานที่");
    if (!effectiveAddress.address_no.trim()) return setError("กรุณากรอกบ้านเลขที่");
    if (!effectiveAddress.sub_district.trim()) return setError("กรุณากรอกตำบล");
    if (!effectiveAddress.district.trim()) return setError("กรุณาเลือกอำเภอ");
    if (!/^\d{5}$/.test(effectiveAddress.postal_code)) {
      return setError("รหัสไปรษณีย์ต้องเป็นตัวเลข 5 หลัก");
    }
    if (kind === "other" && !kindOther.trim()) {
      return setError('เลือกลักษณะที่พักเป็น "อื่น ๆ" กรุณาระบุเพิ่มเติมด้วย');
    }
    if (!answers.authorityId) {
      return setError("กรุณาเลือกพื้นที่ตั้งสถานประกอบการด้านบนก่อนเริ่มยื่นคำขอ");
    }

    setPending(true);
    try {
      const created = await startApplication({
        rooms: Number(answers.rooms),
        guests: Number(answers.guests),
        has_restaurant: answers.hasRestaurant,
        local_authority_id: Number(answers.authorityId),
        property_name: name.trim(),
        address: {
          address_no: effectiveAddress.address_no.trim(),
          moo: effectiveAddress.moo?.trim() || null,
          soi: effectiveAddress.soi?.trim() || null,
          road: effectiveAddress.road?.trim() || null,
          sub_district: effectiveAddress.sub_district.trim(),
          district: effectiveAddress.district.trim(),
          postal_code: effectiveAddress.postal_code,
        },
        accommodation_kind: kind,
        accommodation_kind_other: kind === "other" ? kindOther.trim() : null,
      });
      router.push(`/operator/applications/${created.application_no}`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "เปิดคำขอไม่สำเร็จ กรุณาลองใหม่อีกครั้ง",
      );
      setPending(false);
    }
  }

  return (
    <SectionCard
      icon={FileText}
      tone="brand"
      title="เริ่มยื่นคำขอ"
      description="กรอกข้อมูลสถานที่อีกเล็กน้อย ระบบจะออกเลขที่คำขอให้ใช้อ้างอิง"
      className="mt-8"
    >
      <form onSubmit={onSubmit} noValidate className="space-y-5">
        <TextField
          label="ชื่อสถานที่"
          icon={Building2}
          placeholder="บ้านพักริมเลกะรน"
          hint="ชื่อที่ใช้เรียกที่พักของคุณ ใช้ในแบบหนังสือแจ้งฯ"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <AddressFields value={effectiveAddress} onChange={setAddress} districts={districts} />

        <fieldset>
          <legend className="text-sm font-semibold text-ink">ลักษณะที่พัก</legend>
          <div className="mt-2 grid gap-3 sm:grid-cols-2">
            {ACCOMMODATION_KINDS.map((option) => (
              <label
                key={option.value}
                className={[
                  "flex cursor-pointer items-center gap-3 rounded-xl border-2 p-3 transition-colors",
                  kind === option.value
                    ? "border-brand-500 bg-brand-50/60"
                    : "border-line bg-surface hover:border-brand-200",
                ].join(" ")}
              >
                <input
                  type="radio"
                  name="accommodation_kind"
                  checked={kind === option.value}
                  onChange={() => setKind(option.value)}
                  className="size-5 shrink-0 accent-brand-500"
                />
                <span className="font-medium text-ink">{option.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        {kind === "other" && (
          <TextField
            label="ระบุลักษณะที่พัก"
            placeholder="เช่น อาคารพาณิชย์ดัดแปลง"
            value={kindOther}
            onChange={(e) => setKindOther(e.target.value)}
          />
        )}

        {error && (
          <p
            role="alert"
            className="rounded-xl bg-danger-bg px-4 py-3 text-sm font-medium text-danger-fg"
          >
            {error}
          </p>
        )}

        <Button type="submit" disabled={pending}>
          {pending ? "กำลังเปิดคำขอ…" : "เริ่มยื่นคำขอ"}
          {pending ? null : <ArrowRight className="size-5" aria-hidden />}
        </Button>
      </form>
    </SectionCard>
  );
}


/* ------------------------------------------------------------- ที่อยู่แยกช่อง */

/**
 * ช่องที่อยู่ตามแบบหนังสือแจ้งฯ
 *
 * แยกช่องแทนกล่องข้อความก้อนเดียว เพราะระบบต้องเอาไปกรอกลงแบบฟอร์มราชการ
 * ที่มีช่องว่างแยกกันอยู่แล้ว และส่วนกลางต้องสรุปจำนวนคำขอรายอำเภอได้ (M11)
 *
 * "จังหวัด" ไม่มีช่องให้กรอก เพราะระบบรับเฉพาะภูเก็ตตามขอบเขตของโจทย์
 * เซิร์ฟเวอร์เป็นคนเติมค่านี้ ไม่ใช่รับมาจากหน้าเว็บ
 */
function AddressFields({
  value,
  onChange,
  districts,
}: {
  value: AddressInput;
  onChange: (next: AddressInput) => void;
  districts: string[];
}) {
  const set = (patch: Partial<AddressInput>) => onChange({ ...value, ...patch });

  return (
    <fieldset className="space-y-5">
      <legend className="text-sm font-semibold text-ink">ที่อยู่สถานที่</legend>

      <div className="grid gap-5 sm:grid-cols-2">
        <TextField
          label="บ้านเลขที่"
          icon={MapPin}
          placeholder="99/9"
          value={value.address_no}
          onChange={(e) => set({ address_no: e.target.value })}
        />
        <TextField
          label="หมู่ที่"
          inputMode="numeric"
          placeholder="1"
          hint="เว้นว่างได้ถ้าที่พักอยู่ในเขตเทศบาลที่ไม่มีหมู่"
          value={value.moo ?? ""}
          onChange={(e) => set({ moo: e.target.value.replace(/\D/g, "").slice(0, 3) })}
        />
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <TextField
          label="ซอย"
          placeholder="เว้นว่างได้"
          value={value.soi ?? ""}
          onChange={(e) => set({ soi: e.target.value })}
        />
        <TextField
          label="ถนน"
          placeholder="กะรน"
          hint="ไม่ต้องพิมพ์คำว่า ถนน"
          value={value.road ?? ""}
          onChange={(e) => set({ road: e.target.value })}
        />
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <TextField
          label="ตำบล"
          placeholder="กะรน"
          value={value.sub_district}
          onChange={(e) => set({ sub_district: e.target.value })}
        />

        <div className="space-y-2">
          <label htmlFor="district" className="block text-sm font-semibold text-ink">
            อำเภอ
          </label>
          <select
            id="district"
            value={value.district}
            onChange={(e) => set({ district: e.target.value })}
            className="min-h-12 w-full rounded-xl border border-line bg-canvas px-4 py-3 text-base text-ink"
          >
            <option value="">เลือกอำเภอ</option>
            {districts.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <TextField
          label="รหัสไปรษณีย์"
          inputMode="numeric"
          maxLength={5}
          placeholder="83100"
          value={value.postal_code}
          onChange={(e) => set({ postal_code: e.target.value.replace(/\D/g, "").slice(0, 5) })}
        />
        <div className="space-y-2">
          <span className="block text-sm font-semibold text-ink">จังหวัด</span>
          <p className="flex min-h-12 items-center rounded-xl border border-line bg-canvas px-4 py-3 text-base text-ink-muted">
            ภูเก็ต
          </p>
          <p className="text-sm text-ink-muted">ระบบนี้รับคำขอเฉพาะจังหวัดภูเก็ต</p>
        </div>
      </div>
    </fieldset>
  );
}
