/**
 * M7 — แปลงสถานะคำขอเป็น "ไปถึงขั้นไหนแล้ว / ลูกบอลอยู่ในมือใคร / ต้องเกิดอะไรต่อ"
 *
 * ที่เดียวของระบบที่ทำ mapping นี้ เช่นเดียวกับที่ StatusPill.tsx เป็นที่เดียว
 * ของ สถานะ -> สี/ข้อความ คีย์ทุกตัวต้องตรงกับ ApplicationStatus ใน
 * backend/app/models/enums.py (Record<ApplicationStatus, ...> บังคับให้ครบอยู่แล้ว)
 *
 * แนวคิด "ลูกบอลอยู่ในมือใคร" ยืมมาจากแท็บคิวของเจ้าหน้าที่
 * (frontend/src/app/(officer)/README.md) แต่มองจากฝั่งผู้ยื่น
 */
import type { ApplicationStatus } from "@/types/enums";

/**
 * 4 ขั้นของเส้นทางคำขอ ตั้งแต่เริ่มร่างจนได้เอกสารในมือ
 *
 * ขั้นสุดท้ายเรียกว่า "ได้รับเอกสาร" เฉย ๆ ไม่ใช่ "ออกใบอนุญาต" เพราะปลายทาง
 * มีสองแบบตามผลจำแนก (ใบอนุญาต หรือหนังสือรับรองการแจ้ง) และไม่ใช้คำว่า
 * "เอกสารสิทธิ์" เพราะชนกับชื่อเอกสาร A03 เอกสารสิทธิ์ที่ดิน ที่ผู้ยื่นต้องแนบ
 * คนละอย่างกันคนละทิศ ถ้าใช้คำเดียวกันผู้ใช้จะสับสนว่าต้องเตรียมอะไร
 */
export const APPLICATION_STEPS = [
  "จัดเตรียมเอกสาร",
  "ยื่นคำขอ",
  "เจ้าหน้าที่ตรวจสอบ",
  "ได้รับเอกสาร",
] as const;

/**
 * โทนของแถบความคืบหน้า — คอมโพเนนต์แปลงเป็นคลาสสีอีกที ที่นี่ไม่รู้จักสี
 *
 * waiting = รอฝ่ายอื่น, action = ผู้ยื่นทำต่อได้เลย, attention = ผู้ยื่นถูกตีกลับ
 */
export type ProgressTone = "action" | "waiting" | "attention" | "done" | "stopped";

/** ใครต้องลงมือต่อ ผู้ยื่นต้องแยกออกทันทีว่า "รอเขา" หรือ "รอเรา" */
export type ProgressActor = "operator" | "officer" | "none";

export type ApplicationProgress = {
  /** ดัชนีขั้นปัจจุบัน เริ่มที่ 0 และเท่ากับ APPLICATION_STEPS.length เมื่อครบทุกขั้น */
  stepIndex: number;
  actor: ProgressActor;
  /** ข้อความบนป้ายผู้รับผิดชอบ อ่านแล้วรู้ทันทีว่าต้องรอหรือต้องทำเอง */
  actorLabel: string;
  /** สิ่งที่ต้องเกิดขึ้นต่อไป เขียนเป็นภาษาคน ไม่ใช่ชื่อสถานะ (NFR Usability) */
  nextAction: string;
  tone: ProgressTone;
  /** true = เส้นทางจบลงกลางคัน (ไม่อนุมัติ) แถบจึงไม่เดินต่อ */
  halted: boolean;
};

const PROGRESS: Record<ApplicationStatus, ApplicationProgress> = {
  draft: {
    stepIndex: 0,
    actor: "operator",
    actorLabel: "รอคุณดำเนินการ",
    nextAction: "แนบเอกสารให้ครบทุกฉบับ แล้วกดยื่นคำขอ",
    tone: "action",
    halted: false,
  },
  submitted: {
    stepIndex: 1,
    actor: "officer",
    actorLabel: "อยู่ที่เจ้าหน้าที่",
    nextAction: "รอเจ้าหน้าที่ท้องถิ่นรับเรื่องและเริ่มตรวจเอกสาร",
    tone: "waiting",
    halted: false,
  },
  under_review: {
    stepIndex: 2,
    actor: "officer",
    actorLabel: "อยู่ที่เจ้าหน้าที่",
    nextAction: "เจ้าหน้าที่กำลังตรวจเอกสารทีละฉบับ รอผลการตรวจ",
    tone: "waiting",
    halted: false,
  },
  needs_revision: {
    stepIndex: 2,
    actor: "operator",
    actorLabel: "รอคุณแก้ไข",
    nextAction: "แก้ไขหรือส่งเอกสารเพิ่มตามที่เจ้าหน้าที่แจ้งไว้ แล้วยื่นกลับ",
    tone: "attention",
    halted: false,
  },
  approved: {
    stepIndex: 3,
    actor: "officer",
    actorLabel: "อยู่ที่เจ้าหน้าที่",
    nextAction: "อนุมัติแล้ว รอเจ้าหน้าที่ลงนามออกเอกสารให้",
    tone: "waiting",
    halted: false,
  },
  license_issued: {
    stepIndex: APPLICATION_STEPS.length,
    actor: "none",
    actorLabel: "เสร็จสิ้นทุกขั้นตอน",
    nextAction: "เปิดดูและสั่งพิมพ์เอกสารได้เลย",
    tone: "done",
    halted: false,
  },
  rejected: {
    stepIndex: 2,
    actor: "none",
    actorLabel: "ไม่มีขั้นตอนต่อ",
    nextAction: "คำขอไม่ผ่าน เปิดดูเหตุผลจากเจ้าหน้าที่ในหน้ารายละเอียด",
    tone: "stopped",
    halted: true,
  },
};

export function applicationProgress(status: ApplicationStatus): ApplicationProgress {
  return PROGRESS[status];
}
