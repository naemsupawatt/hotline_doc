"use client";

import { AlertTriangle, Coins, FlaskConical, Save, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError } from "@/lib/api";
import {
  type Fee,
  type PreviewResult,
  type Rule,
  listFees,
  listRules,
  previewRules,
  supersedeFee,
  updateRule,
} from "@/lib/admin";
import { thaiDate } from "@/lib/applications";

/**
 * US-09 — หน้าที่พิสูจน์ว่าระบบเป็น config-driven จริง
 *
 * โจทย์ข้อ 4 กำหนดว่า "ทีมต้องออกแบบระบบให้แก้ไขเงื่อนไขและอัตราค่าธรรมเนียม
 * ได้ในภายหลังโดยไม่ต้องแก้โค้ด" หน้านี้คือหลักฐานของข้อนั้น
 */
export function SettingsView() {
  const [rules, setRules] = useState<Rule[] | null>(null);
  const [fees, setFees] = useState<Fee[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listRules(), listFees()])
      .then(([r, f]) => {
        setRules(r);
        setFees(f);
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "โหลดข้อมูลตั้งค่าไม่ได้"),
      );
  }, []);

  if (error) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-ink">เปิดหน้าตั้งค่าไม่ได้</h1>
        <p role="alert" className="mt-2 text-ink-muted">
          {error}
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
      <PageHeader
        eyebrow="ตั้งค่าระบบ"
        title="แก้เกณฑ์ได้เอง ไม่ต้องแก้โปรแกรม"
        description="เงื่อนไขจำแนกประเภทและอัตราค่าธรรมเนียมเก็บอยู่ในฐานข้อมูล แก้ที่นี่แล้วมีผลกับคำขอใหม่ทันที"
      />

      <p className="mt-6 flex items-start gap-2 rounded-xl bg-warn-bg px-4 py-3 text-sm text-ink">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-warn-fg" aria-hidden />
        การแก้เกณฑ์มีผลกับคำขอที่ยื่นเข้ามาหลังจากนี้เท่านั้น
        คำขอที่ตัดสินไปแล้วยังคงผลเดิมไว้ เพราะระบบบันทึกผลจำแนกไว้ตอนเปิดคำขอ
      </p>

      <Playground className="mt-6" />

      <SectionCard
        icon={SlidersHorizontal}
        className="mt-6"
        title="เงื่อนไขจำแนกประเภทที่พัก"
        description="กฎที่ลำดับน้อยกว่าจะถูกตรวจก่อน กฎแรกที่เข้าเงื่อนไขครบทุกข้อเป็นผู้ชนะ"
      >
        <div className="space-y-4">
          {rules?.map((rule) => (
            <RuleEditor
              key={rule.code}
              rule={rule}
              onSaved={(next) =>
                setRules((rows) => rows?.map((r) => (r.code === next.code ? next : r)) ?? null)
              }
            />
          ))}
          {rules === null && <p className="text-ink-muted">กำลังโหลด…</p>}
        </div>
      </SectionCard>

      <SectionCard
        icon={Coins}
        className="mt-6"
        title="อัตราค่าธรรมเนียม"
        description="เปลี่ยนอัตราคือการเพิ่มอัตราใหม่ ไม่ใช่ทับของเดิม อัตราเก่าจึงยังย้อนดูได้เสมอ"
      >
        <FeeTable fees={fees} onChanged={setFees} />
      </SectionCard>
    </main>
  );
}

/* --------------------------------------------------------- ลองจำแนกดูก่อน */

function Playground({ className }: { className?: string }) {
  const [rooms, setRooms] = useState("8");
  const [guests, setGuests] = useState("36");
  const [restaurant, setRestaurant] = useState(false);
  const [result, setResult] = useState<PreviewResult | null>(null);
  const [pending, setPending] = useState(false);

  async function run() {
    setPending(true);
    try {
      setResult(await previewRules(Number(rooms) || 1, Number(guests) || 1, restaurant));
    } finally {
      setPending(false);
    }
  }

  return (
    <SectionCard
      icon={FlaskConical}
      tone="brand"
      className={className}
      title="ลองจำแนกด้วยเกณฑ์ปัจจุบัน"
      description="ทดสอบได้ทันทีหลังแก้เกณฑ์ โดยไม่บันทึกอะไรลงระบบ"
    >
      <div className="grid gap-4 sm:grid-cols-3">
        <TextField
          label="จำนวนห้อง"
          inputMode="numeric"
          value={rooms}
          onChange={(e) => setRooms(e.target.value.replace(/\D/g, "").slice(0, 4))}
        />
        <TextField
          label="จำนวนผู้เข้าพัก"
          inputMode="numeric"
          value={guests}
          onChange={(e) => setGuests(e.target.value.replace(/\D/g, "").slice(0, 5))}
        />
        <label className="flex items-end gap-2.5 pb-3 text-sm text-ink">
          <input
            type="checkbox"
            checked={restaurant}
            onChange={(e) => setRestaurant(e.target.checked)}
            className="size-5 rounded border-line accent-brand-500"
          />
          มีห้องอาหาร
        </label>
      </div>

      <Button variant="outline" className="mt-4" onClick={run} disabled={pending}>
        {pending ? "กำลังทดสอบ…" : "ลองจำแนก"}
      </Button>

      {result && (
        <div className="mt-4 rounded-xl border border-line bg-surface p-4">
          {result.matched ? (
            <>
              <p className="font-semibold text-ink">{result.property_type_name}</p>
              <p className="mt-1 text-sm text-ink-muted">{result.reason}</p>
              <p className="mt-2 text-xs text-ink-muted">
                ตัดสินด้วยเกณฑ์ <span className="font-mono">{result.rule_code}</span>
              </p>
            </>
          ) : (
            <p className="font-medium text-danger-fg">
              ไม่มีเกณฑ์ใดรองรับกรณีนี้ — ผู้ใช้จริงจะติดต่อระบบไม่ได้ กรุณาตรวจสอบเกณฑ์
            </p>
          )}
        </div>
      )}
    </SectionCard>
  );
}

/* ------------------------------------------------------------- แก้กฎรายข้อ */

const LIMIT_FIELDS = [
  { key: "min_rooms", label: "ห้องขั้นต่ำ" },
  { key: "max_rooms", label: "ห้องสูงสุด" },
  { key: "min_guests", label: "ผู้เข้าพักขั้นต่ำ" },
  { key: "max_guests", label: "ผู้เข้าพักสูงสุด" },
] as const;

function RuleEditor({ rule, onSaved }: { rule: Rule; onSaved: (r: Rule) => void }) {
  const [draft, setDraft] = useState(() => toDraft(rule));
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [pending, setPending] = useState(false);

  const dirty = LIMIT_FIELDS.some((f) => draft[f.key] !== toDraft(rule)[f.key]);

  async function save() {
    setError(null);
    setSaved(false);
    setPending(true);
    try {
      const changes: Record<string, number> = {};
      const clear: string[] = [];
      for (const f of LIMIT_FIELDS) {
        const raw = draft[f.key].trim();
        if (raw === "") clear.push(f.key);
        else changes[f.key] = Number(raw);
      }
      const next = await updateRule(rule.code, { ...changes, clear });
      onSaved(next);
      setDraft(toDraft(next));
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "บันทึกไม่สำเร็จ");
    } finally {
      setPending(false);
    }
  }

  return (
    <article className="rounded-xl border border-line bg-surface p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-lg bg-brand-50 px-2 py-1 font-mono text-xs font-bold text-brand-700">
          {rule.code}
        </span>
        <h3 className="font-semibold text-ink">{rule.property_type_name}</h3>
        <span className="text-sm text-ink-muted">ลำดับ {rule.priority}</span>
        {rule.requires_restaurant !== null && (
          <span className="rounded-full bg-info-bg px-2 py-0.5 text-xs text-info-fg">
            {rule.requires_restaurant ? "ต้องมีห้องอาหาร" : "ต้องไม่มีห้องอาหาร"}
          </span>
        )}
        {rule.applications_classified > 0 && (
          <span className="ml-auto text-xs text-ink-muted">
            เคยตัดสินไปแล้ว {rule.applications_classified} คำขอ
          </span>
        )}
      </div>

      <div className="mt-3 grid gap-3 sm:grid-cols-4">
        {LIMIT_FIELDS.map((f) => (
          <TextField
            key={f.key}
            label={f.label}
            inputMode="numeric"
            placeholder="ไม่จำกัด"
            hint={draft[f.key].trim() === "" ? "เว้นว่าง = ไม่จำกัด" : undefined}
            value={draft[f.key]}
            onChange={(e) =>
              setDraft({ ...draft, [f.key]: e.target.value.replace(/\D/g, "").slice(0, 5) })
            }
          />
        ))}
      </div>

      <p className="mt-3 text-sm text-ink-muted">{rule.outcome_message}</p>

      {error && (
        <p role="alert" className="mt-3 rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger-fg">
          {error}
        </p>
      )}
      {saved && !dirty && (
        <p className="mt-3 rounded-lg bg-success-bg px-3 py-2 text-sm text-success-fg">
          บันทึกแล้ว มีผลกับคำขอใหม่ทันที
        </p>
      )}

      <Button size="sm" variant="outline" className="mt-3 w-auto" onClick={save} disabled={pending || !dirty}>
        <Save className="size-4" aria-hidden />
        {pending ? "กำลังบันทึก…" : "บันทึกเกณฑ์นี้"}
      </Button>
    </article>
  );
}

function toDraft(rule: Rule): Record<(typeof LIMIT_FIELDS)[number]["key"], string> {
  return {
    min_rooms: rule.min_rooms?.toString() ?? "",
    max_rooms: rule.max_rooms?.toString() ?? "",
    min_guests: rule.min_guests?.toString() ?? "",
    max_guests: rule.max_guests?.toString() ?? "",
  };
}

/* ------------------------------------------------------ อัตราค่าธรรมเนียม */

function FeeTable({ fees, onChanged }: { fees: Fee[] | null; onChanged: (f: Fee[]) => void }) {
  const [editing, setEditing] = useState<number | null>(null);
  const [amount, setAmount] = useState("");
  const [from, setFrom] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  if (fees === null) return <p className="text-ink-muted">กำลังโหลด…</p>;

  async function save(fee: Fee) {
    setError(null);
    setPending(true);
    try {
      onChanged(
        await supersedeFee(fee.id, {
          amount: Number(amount),
          validity_years: fee.validity_years,
          effective_from: from,
        }),
      );
      setEditing(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "บันทึกไม่สำเร็จ");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-3">
      {fees.map((fee) => (
        <article key={fee.id} className="rounded-xl border border-line bg-surface p-4">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold text-ink">{fee.property_type_name}</h3>
            <span className="text-lg font-bold text-brand-600">
              {fee.amount.toLocaleString("th-TH")} บาท
            </span>
            <span className="text-sm text-ink-muted">ต่อ {fee.validity_years} ปี</span>
            {fee.is_current ? (
              <span className="rounded-full bg-success-bg px-2 py-0.5 text-xs font-medium text-success-fg">
                ใช้อยู่ตอนนี้
              </span>
            ) : (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                {new Date(fee.effective_from) > new Date() ? "รอมีผล" : "ปิดแล้ว"}
              </span>
            )}
          </div>

          <p className="mt-1 text-sm text-ink-muted">
            มีผล {thaiDate(fee.effective_from)}
            {fee.effective_to ? ` ถึง ${thaiDate(fee.effective_to)}` : " เป็นต้นไป"}
            {fee.note ? ` · ${fee.note}` : ""}
          </p>

          {editing === fee.id ? (
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <TextField
                label="อัตราใหม่ (บาท)"
                inputMode="numeric"
                value={amount}
                onChange={(e) => setAmount(e.target.value.replace(/\D/g, "").slice(0, 9))}
              />
              <TextField
                label="เริ่มมีผลวันที่"
                type="date"
                hint="ต้องหลังวันที่อัตราเดิมเริ่มมีผล"
                value={from}
                onChange={(e) => setFrom(e.target.value)}
              />
              <div className="flex items-end gap-2 pb-1">
                <Button size="sm" onClick={() => save(fee)} disabled={pending || !amount || !from}>
                  {pending ? "กำลังบันทึก…" : "บันทึก"}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>
                  ยกเลิก
                </Button>
              </div>
            </div>
          ) : (
            fee.is_current && (
              <Button
                size="sm"
                variant="outline"
                className="mt-3 w-auto"
                onClick={() => {
                  setEditing(fee.id);
                  setAmount(String(fee.amount));
                  setFrom("");
                  setError(null);
                }}
              >
                เปลี่ยนอัตรานี้
              </Button>
            )
          )}
        </article>
      ))}

      {error && (
        <p role="alert" className="rounded-lg bg-danger-bg px-3 py-2 text-sm text-danger-fg">
          {error}
        </p>
      )}
    </div>
  );
}
