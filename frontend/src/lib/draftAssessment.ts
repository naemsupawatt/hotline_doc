/**
 * คำตอบประเมินที่พักของคนที่ยังไม่ได้สมัครสมาชิก — เก็บไว้ในเบราว์เซอร์เท่านั้น
 *
 * **ทำไมไม่เก็บลงฐานข้อมูล** — `/wizard/classify` ตั้งใจออกแบบให้ไม่เขียน DB
 * "จึงไม่มีขยะค้างจากคนที่แค่มาลอง" (ดู `backend/app/api/v1/wizard.py`)
 * ถ้าเปิดตารางรับข้อมูลของคนที่ยังไม่มีบัญชี ก็ต้องมีคนคอยล้าง และจะมีข้อมูล
 * ของคนที่ยังไม่ได้ตกลงอะไรกับระบบค้างอยู่ โดยไม่ได้แลกกับอะไรเลย
 *
 * **เก็บ "คำตอบ" ไม่ใช่ "ผลประเมิน"** — Super Admin แก้เกณฑ์ได้ตลอดเวลา (US-09)
 * ผลที่เก็บไว้เมื่อวานจึงอาจขัดกับกฎของวันนี้ เรียกคืนแล้วต้องยิง `classify`
 * ใหม่เสมอ หลักเดียวกับที่ `WizardView` ทำตอนกดเปิดคำขอ คือส่งคำตอบไปให้
 * เซิร์ฟเวอร์จำแนกใหม่ ไม่ได้ส่งผลจำแนกที่ได้มาแล้วกลับไป
 *
 * **ข้อจำกัดที่ตั้งใจรับไว้** — ผูกกับเบราว์เซอร์เครื่องเดิม ประเมินบนมือถือ
 * แล้วไปสมัครบนคอมพิวเตอร์จะไม่ตามไปด้วย แลกกับการไม่ต้องเก็บข้อมูลคนแปลกหน้า
 */
import type { WizardAnswers } from "@/lib/wizard";

/** คำตอบของ wizard ขั้นที่ 1 เก็บเป็นสตริงเหมือนค่าที่อยู่ในช่องกรอกจริง
    เรียกคืนแล้วหน้าจอจะเหมือนตอนที่ผู้ใช้พิมพ์ค้างไว้ ไม่ใช่ค่าที่แปลงไปแล้ว */
export type Answers = {
  rooms: string;
  guests: string;
  hasRestaurant: boolean;
  authorityId: string;
};

export const EMPTY_ANSWERS: Answers = {
  rooms: "",
  guests: "",
  hasRestaurant: false,
  authorityId: "",
};

/** ใส่เลขรุ่นไว้ในชื่อ เผื่อวันหลังรูปร่างคำตอบเปลี่ยน จะได้ไม่ไปอ่านของเก่าผิดรูป */
const KEY = "hotline.assessment.v1";

/** ความยาวสูงสุดของแต่ละช่อง ต้องตรงกับที่ช่องกรอกใน `WizardView` ตัดไว้
    เพราะค่าที่อ่านกลับมาจะถูกใส่ลงช่องเดิม */
const MAX_ROOMS_DIGITS = 4;
const MAX_GUESTS_DIGITS = 5;
const MAX_AUTHORITY_DIGITS = 9;

/**
 * ตรวจคำตอบก่อนส่งประเมิน — คืนข้อความที่ผู้ใช้อ่านรู้เรื่อง หรือ `null` ถ้าผ่าน
 *
 * อยู่ที่นี่ที่เดียวเพราะใช้สองทาง: ตอนผู้ใช้กดปุ่มประเมิน และตอนเรียกคืน
 * คำตอบเก่าเพื่อประเมินซ้ำให้อัตโนมัติ ถ้าแยกเขียนสองที่ วันหนึ่งจะเพี้ยนกัน
 *
 * หมายเหตุ: นี่คือการตรวจเพื่อให้ผู้ใช้รู้ผลทันที ไม่ได้แทนการตรวจฝั่งเซิร์ฟเวอร์
 */
export function validateAnswers(answers: Answers): string | null {
  const rooms = Number(answers.rooms);
  const guests = Number(answers.guests);

  if (!Number.isInteger(rooms) || rooms < 1) {
    return "กรุณากรอกจำนวนห้องพักเป็นตัวเลขตั้งแต่ 1 ห้องขึ้นไป";
  }
  if (!Number.isInteger(guests) || guests < 1) {
    return "กรุณากรอกจำนวนผู้เข้าพักเป็นตัวเลขตั้งแต่ 1 คนขึ้นไป";
  }
  return null;
}

/** แปลงคำตอบบนหน้าจอเป็นรูปแบบที่ API รับ — เรียกใช้ได้ต่อเมื่อ
    `validateAnswers` ผ่านแล้วเท่านั้น */
export function toWizardAnswers(answers: Answers): WizardAnswers {
  return {
    rooms: Number(answers.rooms),
    guests: Number(answers.guests),
    has_restaurant: answers.hasRestaurant,
    local_authority_id: answers.authorityId ? Number(answers.authorityId) : null,
  };
}

/** ผู้ใช้กรอกอะไรไว้บ้างหรือยัง — ใช้ตัดสินว่าควรเก็บหรือควรลบทิ้ง */
export function hasAnswers(answers: Answers): boolean {
  return (
    answers.rooms !== "" ||
    answers.guests !== "" ||
    answers.hasRestaurant ||
    answers.authorityId !== ""
  );
}

/**
 * เก็บคำตอบไว้ให้ ถ้าฟอร์มว่างเปล่าก็ลบของเดิมทิ้ง
 *
 * `localStorage` ใช้ไม่ได้ในบางสภาพแวดล้อม (โหมดส่วนตัว / ปิดการเก็บข้อมูลเว็บไซต์)
 * และเต็มได้ด้วย ทุกทางเข้าออกจึงต้องกันพังไว้ ฟีเจอร์นี้เป็นความสะดวก
 * ไม่ใช่สิ่งที่ขาดแล้วระบบทำงานไม่ได้
 */
export function saveAssessment(answers: Answers): void {
  if (typeof window === "undefined") return;
  try {
    if (hasAnswers(answers)) {
      window.localStorage.setItem(KEY, JSON.stringify(answers));
    } else {
      window.localStorage.removeItem(KEY);
    }
  } catch {
    // เขียนไม่ได้ก็ปล่อยไป ผลที่ตามมาคือผู้ใช้ต้องกรอกใหม่ถ้าออกจากหน้านี้
  }
}

/**
 * อ่านค่าดิบที่เก็บไว้ คืน `null` ถ้าไม่มีหรืออ่านไม่ได้
 *
 * แยกจากการแปลงค่าเพราะหน้าจออ่านผ่าน `useSyncExternalStore` ซึ่งบังคับว่า
 * snapshot ต้องเทียบเท่ากันได้ทุกครั้งที่อ่าน ถ้าคืนอ็อบเจกต์ที่สร้างใหม่ทุกรอบ
 * React จะเห็นเป็นค่าใหม่เสมอแล้ว render วนไม่จบ สตริงดิบเทียบด้วย === ได้ตรง ๆ
 */
export function readStoredAssessment(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

/**
 * แปลงค่าดิบเป็นคำตอบที่ใช้ได้ คืน `null` ถ้าไม่มีหรือรูปร่างไม่เข้าท่า
 *
 * ค่าที่อยู่ใน storage เชื่อทั้งก้อนไม่ได้ (ผู้ใช้แก้เองได้ หรือเป็นของรุ่นเก่า
 * ที่ยังค้างอยู่) จึงประกอบขึ้นใหม่ทีละช่องพร้อมตัดให้อยู่ในรูปที่ช่องกรอกรับ
 * แทนการ cast ทั้งก้อนแล้วเชื่อว่าถูกต้อง
 */
export function parseAssessment(raw: string | null): Answers | null {
  if (!raw) return null;

  let parsed: Partial<Answers>;
  try {
    parsed = JSON.parse(raw) as Partial<Answers>;
  } catch {
    return null;
  }
  if (typeof parsed !== "object" || parsed === null) return null;

  const digits = (value: unknown, max: number) =>
    typeof value === "string" ? value.replace(/\D/g, "").slice(0, max) : "";

  const answers: Answers = {
    rooms: digits(parsed.rooms, MAX_ROOMS_DIGITS),
    guests: digits(parsed.guests, MAX_GUESTS_DIGITS),
    hasRestaurant: parsed.hasRestaurant === true,
    authorityId: digits(parsed.authorityId, MAX_AUTHORITY_DIGITS),
  };

  // ก้อนที่เหลือแต่ค่าว่างหลังกรองแล้ว ไม่ต่างจากไม่เคยกรอก
  return hasAnswers(answers) ? answers : null;
}

/** ลบทิ้งเมื่อคำตอบชุดนี้ถูกใช้เปิดคำขอไปแล้ว — ข้อมูลย้ายไปอยู่ในคำขอจริงแล้ว
    ถ้าไม่ลบ ครั้งหน้าที่เปิดหน้าประเมินจะเจอตัวเลขของที่พักหลังก่อนค้างอยู่ */
export function clearAssessment(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(KEY);
  } catch {
    // ลบไม่ได้ก็ไม่เป็นไร ผู้ใช้แก้ค่าในฟอร์มทับได้อยู่แล้ว
  }
}
