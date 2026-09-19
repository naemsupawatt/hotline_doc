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
import { useEffect, useState } from "react";

import { Mascot } from "@/components/brand/Mascot";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { Stepper } from "@/components/common/Stepper";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError } from "@/lib/api";
import {
  type ClassifyResult,
  type LocalAuthority,
  type RequiredDocument,
  classify,
  describeAccepted,
  listLocalAuthorities,
} from "@/lib/wizard";

const STEPS = [{ label: "ข้อมูลที่พัก" }, { label: "บริการ" }, { label: "ผลประเมิน" }];

export function WizardView() {
  const [result, setResult] = useState<ClassifyResult | null>(null);
  const [answers, setAnswers] = useState<{ rooms: string; guests: string }>({
    rooms: "",
    guests: "",
  });

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <PageHeader
        eyebrow="01 / ประเมินที่พัก"
        title="ที่พักของคุณต้องดำเนินการอะไร?"
        description="ตอบข้อมูลเบื้องต้น เพื่อรับแนวทางการดำเนินการตามกฎหมายอย่างเข้าใจง่าย"
      />

      <Stepper steps={STEPS} current={result ? 2 : 0} className="mt-8 max-w-xl" />

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <AssessmentForm
          answers={answers}
          onAnswersChange={setAnswers}
          onResult={setResult}
          onReset={() => setResult(null)}
        />
        <ResultPanel result={result} />
      </div>

      {result && <DocumentChecklist result={result} />}
    </main>
  );
}

/* ------------------------------------------------------------------ ฟอร์ม */

type FormProps = {
  answers: { rooms: string; guests: string };
  onAnswersChange: (a: { rooms: string; guests: string }) => void;
  onResult: (r: ClassifyResult) => void;
  onReset: () => void;
};

function AssessmentForm({ answers, onAnswersChange, onResult, onReset }: FormProps) {
  const [hasRestaurant, setHasRestaurant] = useState(false);
  const [authorityId, setAuthorityId] = useState<string>("");
  const [authorities, setAuthorities] = useState<LocalAuthority[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  // อปท. 19 แห่งมาจากฐานข้อมูล ไม่ได้เขียนตายตัวไว้ในหน้าเว็บ (ข้อ 4 ของโจทย์)
  useEffect(() => {
    listLocalAuthorities()
      .then(setAuthorities)
      .catch(() => setError("โหลดรายชื่อหน่วยงานท้องถิ่นไม่ได้ กรุณารีเฟรชหน้าอีกครั้ง"));
  }, []);

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
    <form onSubmit={onSubmit} noValidate className="rounded-card border border-line bg-surface p-5">
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
    <div className="rounded-card border border-line bg-brand-50/40 p-5">
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
    <div className="flex flex-col items-center justify-center rounded-card border border-dashed border-line bg-brand-50/30 p-8 text-center">
      <Mascot pose="wave" size="md" className="w-40" />
      <p className="mt-4 font-semibold text-ink">กรอกข้อมูลด้านซ้ายเพื่อดูผลประเมิน</p>
      <p className="mt-1 max-w-sm text-sm text-ink-muted">
        ระบบจะบอกว่าที่พักของคุณเข้าข่ายประเภทใด ต้องใช้เอกสารอะไรบ้าง
        และเอกสารฉบับใดต้องไปขอจากหน่วยงานอื่น
      </p>
    </div>
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
