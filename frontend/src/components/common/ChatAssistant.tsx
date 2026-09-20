"use client";

import { Bot, MessageCircle, Send, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import {
  type ChatChip,
  type ChatContext,
  type ChatReply,
  INTENT_BY_ID,
  answerDocumentReview,
  answerDocumentsFor,
  answerRevision,
  answerStatus,
  fallback,
  greeting,
  routeByKeywords,
  topics,
} from "@/lib/chatbot";
import { getToken } from "@/lib/auth";
import { cn } from "@/lib/utils";

/**
 * ผู้ช่วยตอบคำถามผู้ประกอบการ — ลดคำถามซ้ำที่เจ้าหน้าที่ต้องตอบทางโทรศัพท์
 *
 * ยังไม่ได้ต่อ AI โดยตั้งใจ: เป็นชุดคำถามที่เตรียมไว้ + จับคำสำคัญจากข้อความ
 * ที่พิมพ์เข้ามา ข้อดีคือทีมอธิบายได้ทุกคำตอบว่ามาจากไหน และคำตอบที่เกี่ยวกับ
 * กฎเกณฑ์ดึงจาก API จริงเสมอ (ดูเหตุผลใน lib/chatbot.ts)
 *
 * คอมโพเนนต์นี้รู้แค่ "วิธีคุย" ส่วนคำถาม-คำตอบทั้งหมดอยู่ที่ lib/chatbot.ts
 * ที่เดียว ทีมจึงแก้ข้อความได้โดยไม่ต้องแตะโค้ดหน้าจอ
 */
type Message = {
  id: number;
  from: "bot" | "user";
  text: string;
  reply?: ChatReply;
};

let nextId = 0;

export function ChatAssistant() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  /** สิ่งที่บอทจำระหว่างคุย — อยู่ในหน่วยความจำของหน้าเท่านั้น ไม่ได้บันทึกที่ไหน */
  const context = useRef<ChatContext>({ isLoggedIn: false });
  const expecting = useRef<"rooms" | "guests" | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (open && messages.length === 0) {
      context.current = { isLoggedIn: Boolean(getToken()) };
      push("bot", greeting());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages]);

  function push(from: "bot" | "user", reply: ChatReply | string) {
    const value: ChatReply = typeof reply === "string" ? { text: reply } : reply;
    // อัปเดต "คำถามที่ค้างอยู่" เฉพาะข้อความของบอท ข้อความของผู้ใช้คือคำตอบ ไม่ใช่คำถามใหม่
    if (from === "bot") expecting.current = value.expect ?? null;
    setMessages((prev) => [
      ...prev,
      { id: nextId++, from, text: value.text, reply: from === "bot" ? value : undefined },
    ]);
  }

  /** ห่อทุกคำตอบที่ต้องยิง API ไว้ที่เดียว ผู้ใช้ต้องไม่เจอหน้าค้างหรือ error ดิบ */
  async function answer(run: () => Promise<ChatReply>) {
    setBusy(true);
    try {
      push("bot", await run());
    } catch {
      push(
        "bot",
        "ตอนนี้ดึงข้อมูลจากระบบไม่ได้ กรุณาลองใหม่อีกครั้งในอีกสักครู่ครับ",
      );
    } finally {
      setBusy(false);
    }
  }

  function runIntent(id: string) {
    const intent = INTENT_BY_ID.get(id);
    if (!intent) return;
    void answer(() => Promise.resolve(intent.answer(context.current)));
  }

  /** ปุ่มที่ส่ง value คือ "คำตอบของคำถามที่บอทถามค้างไว้" เช่น เลือกคำขอ หรือมี/ไม่มีห้องอาหาร */
  function handleValue(value: string) {
    const [kind, arg] = value.split(":");

    if (kind === "topics") return push("bot", topics());

    if (kind === "restaurant") {
      context.current.hasRestaurant = arg === "yes";
      const { rooms, guests, hasRestaurant } = context.current;
      if (!rooms || !guests) {
        push("bot", { text: "ขอถามใหม่อีกครั้งครับ ที่พักมีกี่ห้อง (พิมพ์เป็นตัวเลข)", expect: "rooms" });
        return;
      }
      void answer(() => answerDocumentsFor(rooms, guests, Boolean(hasRestaurant)));
      return;
    }
    if (kind === "status_of") return void answer(() => answerStatus(arg));
    if (kind === "documents_review_of") return void answer(() => answerDocumentReview(arg));
    if (kind === "revision_of") return void answer(() => answerRevision(arg));
    if (kind === "documents_of") {
      // ผู้ใช้เลือกคำขอที่มีอยู่ จึงตอบด้วยสถานะเอกสารจริงของใบนั้น
      return void answer(() => answerDocumentReview(arg));
    }
  }

  function onChip(chip: ChatChip) {
    push("user", chip.label);
    if (chip.intent) runIntent(chip.intent);
    else if (chip.value) handleValue(chip.value);
  }

  function onSend() {
    const text = draft.trim();
    if (!text || busy) return;

    // อ่านคำถามที่บอทค้างไว้ก่อนเสมอ แล้วค่อยเคลียร์ ไม่งั้นคำตอบถัดไปจะหลงทาง
    const waiting = expecting.current;
    expecting.current = null;

    push("user", text);
    setDraft("");
    const number = Number(text.replace(/[^\d]/g, ""));
    if (waiting && Number.isFinite(number) && number > 0) {
      if (waiting === "rooms") {
        context.current.rooms = number;
        push("bot", {
          text: `รับทราบครับ ${number} ห้อง แล้วรับผู้เข้าพักได้สูงสุดกี่คน (พิมพ์เป็นตัวเลข)`,
          expect: "guests",
        });
        return;
      }
      context.current.guests = number;
      push("bot", {
        text: `ที่พักมีห้องอาหารหรือสถานที่บริการอาหารหรือไม่ครับ`,
        chips: [
          { label: "มีห้องอาหาร", value: "restaurant:yes" },
          { label: "ไม่มีห้องอาหาร", value: "restaurant:no" },
        ],
      });
      return;
    }

    const intent = routeByKeywords(text);
    if (intent) runIntent(intent.id);
    else push("bot", fallback());
  }

  return (
    <>
      {/* ปุ่มลอย — ซ่อนตอนพิมพ์เอกสารเสมอ */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls="chat-assistant"
        className="no-print fixed right-4 bottom-4 z-40 inline-flex min-h-14 items-center gap-2 rounded-full bg-brand-500 px-5 text-white shadow-lift hover:bg-brand-400 sm:right-6 sm:bottom-6"
      >
        {open ? <X className="size-5" aria-hidden /> : <MessageCircle className="size-5" aria-hidden />}
        <span className="font-semibold">{open ? "ปิด" : "ถามผู้ช่วย"}</span>
      </button>

      {open && (
        <section
          id="chat-assistant"
          aria-label="ผู้ช่วยตอบคำถาม"
          className="no-print fixed inset-x-3 bottom-22 z-40 flex max-h-[70dvh] flex-col overflow-hidden rounded-card border border-line bg-surface shadow-lift sm:inset-x-auto sm:right-6 sm:bottom-24 sm:w-[26rem]"
        >
          <header className="flex items-center gap-2 border-b border-line bg-brand-50 px-4 py-3">
            <Bot className="size-5 text-brand-600" aria-hidden />
            <div className="min-w-0">
              <p className="font-semibold text-ink">ผู้ช่วยตอบคำถาม</p>
              <p className="text-xs text-ink-muted">
                ตอบจากข้อมูลจริงในระบบ · ยังไม่ได้ต่อ AI
              </p>
            </div>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {messages.map((m) => (
              <div key={m.id}>
                <div
                  className={cn(
                    "max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm whitespace-pre-line",
                    m.from === "bot"
                      ? "bg-canvas text-ink"
                      : "ml-auto bg-brand-500 text-white",
                  )}
                >
                  {m.text}
                </div>

                {m.reply?.links && m.reply.links.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {m.reply.links.map((link) => (
                      <Link
                        key={link.href + link.label}
                        href={link.href}
                        onClick={() => setOpen(false)}
                        className="inline-flex min-h-9 items-center rounded-lg bg-brand-50 px-3 text-xs font-semibold text-brand-700 underline underline-offset-4"
                      >
                        {link.label}
                      </Link>
                    ))}
                  </div>
                )}

                {m.reply?.chips && m.reply.chips.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {m.reply.chips.map((chip) => (
                      <button
                        key={chip.label}
                        type="button"
                        disabled={busy}
                        onClick={() => onChip(chip)}
                        className="min-h-9 rounded-full border border-brand-200 px-3 text-xs font-medium text-brand-700 hover:bg-brand-50 disabled:opacity-50"
                      >
                        {chip.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {busy && <p className="text-sm text-ink-muted">กำลังค้นข้อมูลจากระบบ…</p>}
            <div ref={endRef} />
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              onSend();
            }}
            className="flex items-center gap-2 border-t border-line px-3 py-3"
          >
            <label htmlFor="chat-input" className="sr-only">
              พิมพ์คำถามของคุณ
            </label>
            <input
              id="chat-input"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="พิมพ์คำถาม เช่น ต้องใช้เอกสารอะไรบ้าง"
              className="min-h-11 flex-1 rounded-xl border border-line bg-canvas px-3 text-sm"
            />
            <button
              type="submit"
              disabled={busy || !draft.trim()}
              className="grid size-11 shrink-0 place-items-center rounded-xl bg-brand-500 text-white hover:bg-brand-400 disabled:opacity-50"
            >
              <Send className="size-4" aria-hidden />
              <span className="sr-only">ส่งคำถาม</span>
            </button>
          </form>
        </section>
      )}
    </>
  );
}
