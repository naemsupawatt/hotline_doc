/**
 * ผู้ช่วยตอบคำถามผู้ประกอบการ — คลังคำถาม-คำตอบของแชทบอท
 *
 * ยังไม่ได้ต่อ AI โดยตั้งใจ: เป็นชุดคำถามที่เตรียมไว้ + การจับคำสำคัญจากข้อความ
 * ที่ผู้ใช้พิมพ์ เพื่อให้เห็นภาพฟีเจอร์ก่อนตัดสินใจว่าจะต่อโมเดลจริงหรือไม่
 *
 * **กฎสำคัญของไฟล์นี้: ห้ามเขียนคำตอบที่เป็น "กฎเกณฑ์" ลงไปตรง ๆ**
 * จำนวนห้อง จำนวนคน ค่าธรรมเนียม รายการเอกสาร ชนิดไฟล์ที่รับ ขนาดไฟล์
 * และ อปท. ทั้งหมดต้องดึงจาก API เสมอ เพราะ Super Admin แก้ค่าเหล่านี้ได้เอง (US-09)
 * ถ้าเขียนตัวเลขไว้ในคำตอบ วันที่กฎเปลี่ยน แชทบอทจะกลายเป็นตัวให้ข้อมูลผิด
 * ซึ่งแย่กว่าไม่มีแชทบอทเลย
 *
 * สิ่งที่เขียนตรง ๆ ได้คือ "วิธีใช้ระบบ" เช่น กดปุ่มไหน ไปหน้าไหนต่อ
 */
import {
  type Application,
  allDocuments,
  getApplication,
  myApplications,
} from "@/lib/applications";
import { applicationStatusLabel } from "@/components/common/StatusPill";
import { APPLICATION_STEPS, applicationProgress } from "@/lib/progress";
import { type RequiredDocument, classify, describeAccepted, listLocalAuthorities } from "@/lib/wizard";
import type { ApplicationStatus, DocumentStatus } from "@/types/enums";

export type ChatLink = { href: string; label: string };

/** ปุ่มคำถามถัดไป — ส่ง intent (ถามหัวข้อนั้น) หรือ value (ตอบคำถามที่บอทถามค้างไว้) */
export type ChatChip = { label: string; intent?: string; value?: string };

export type ChatReply = {
  text: string;
  links?: ChatLink[];
  chips?: ChatChip[];
  /** บอทกำลังรอตัวเลขจากผู้ใช้ — คอมโพเนนต์ใช้ตัดสินว่าข้อความถัดไปคืออะไร */
  expect?: "rooms" | "guests";
};

export type ChatGroup = "process" | "documents" | "status";

export type ChatIntent = {
  id: string;
  group: ChatGroup;
  /** ข้อความบนปุ่ม = คำถามในมุมของผู้ใช้ */
  label: string;
  keywords: string[];
  answer: (ctx: ChatContext) => Promise<ChatReply>;
};

/** สิ่งที่บอทจำไว้ระหว่างบทสนทนา (อยู่ในหน่วยความจำของหน้าเท่านั้น ไม่ได้บันทึกที่ไหน) */
export type ChatContext = {
  isLoggedIn: boolean;
  rooms?: number;
  guests?: number;
  hasRestaurant?: boolean;
};

export const GROUP_LABEL: Record<ChatGroup, string> = {
  process: "ขั้นตอนการขออนุญาต",
  documents: "เอกสารที่ต้องเตรียม",
  status: "คำขอของฉัน",
};

const LOGIN_REQUIRED: ChatReply = {
  text: "ข้อมูลส่วนนี้เป็นของคำขอคุณเอง ต้องเข้าสู่ระบบก่อนถึงจะดูได้ครับ",
  links: [{ href: "/login", label: "เข้าสู่ระบบ" }],
  chips: [
    { label: "ขั้นตอนการขออนุญาตมีอะไรบ้าง", intent: "process_overview" },
    { label: "ต้องเตรียมเอกสารอะไรบ้าง", intent: "documents_checklist" },
  ],
};

// ---------------------------------------------------------------- ตัวช่วยเขียนคำตอบ

function bullet(lines: string[]): string {
  return lines.map((line) => `• ${line}`).join("\n");
}

function docLine(doc: RequiredDocument): string {
  const required = doc.is_mandatory ? "บังคับ" : "ไม่บังคับ";
  const how = doc.is_system_form
    ? "ระบบกรอกให้ เหลือลงลายมือชื่อ"
    : describeAccepted(doc.accepted_mime);
  return `${doc.code} ${doc.name_th} (${required} · ${how})`;
}

/** เอกสารที่ต้องไปขอจากหน่วยงานอื่น พร้อมจุดติดต่อ (M4) */
function externalLine(doc: RequiredDocument): string {
  const cp = doc.contact_point;
  if (!cp) return `${doc.code} ${doc.name_th}`;
  const days = cp.estimated_days ? ` · ใช้เวลาประมาณ ${cp.estimated_days} วัน` : "";
  return `${doc.code} ${doc.name_th} — ติดต่อ ${cp.office_name}${days}`;
}

const DOC_PROBLEM: DocumentStatus[] = ["revision_requested", "system_flagged"];

function summarizeDocuments(app: Application): string {
  const docs = allDocuments(app);
  const done = docs.filter((d) => d.status === "approved").length;
  const problems = docs.filter((d) => DOC_PROBLEM.includes(d.status as DocumentStatus));
  const waiting = docs.filter((d) => d.status === "uploaded" || d.status === "officer_reviewing");

  const lines = [
    `ตรวจผ่านแล้ว ${done} จาก ${docs.length} ฉบับ`,
    waiting.length > 0 ? `รอเจ้าหน้าที่ตรวจอีก ${waiting.length} ฉบับ` : null,
    problems.length > 0 ? `ต้องแก้ไข ${problems.length} ฉบับ` : null,
  ].filter(Boolean) as string[];

  return bullet(lines);
}

async function pickApplication(ctx: ChatContext, intent: string): Promise<ChatReply | null> {
  if (!ctx.isLoggedIn) return LOGIN_REQUIRED;

  const rows = await myApplications();
  if (rows.length === 0) {
    return {
      text: "ยังไม่มีคำขอในบัญชีนี้ครับ เริ่มจากประเมินที่พักก่อน ระบบจะบอกว่าเข้าข่ายประเภทใดและต้องใช้เอกสารอะไรบ้าง",
      links: [{ href: "/operator/wizard", label: "เริ่มประเมินที่พัก" }],
    };
  }
  if (rows.length > 1) {
    return {
      text: "คุณมีหลายคำขอ ต้องการดูใบไหนครับ",
      chips: rows.map((r) => ({
        label: `${r.application_no} · ${r.property_name}`,
        value: `${intent}:${r.application_no}`,
      })),
    };
  }
  return null; // มีใบเดียว ผู้เรียกจะไปดึงรายละเอียดต่อเอง
}

async function onlyApplicationNo(): Promise<string> {
  const rows = await myApplications();
  return rows[0].application_no;
}

// ---------------------------------------------------------------- คำตอบที่ใช้ซ้ำหลายที่

/** ใช้ทั้งตอนถามเรื่องสถานะ และตอนเลือกคำขอจากปุ่ม */
export async function answerStatus(applicationNo: string): Promise<ChatReply> {
  const app = await getApplication(applicationNo);
  const progress = applicationProgress(app.status as ApplicationStatus);
  const step =
    progress.stepIndex >= APPLICATION_STEPS.length
      ? "ครบทุกขั้นตอนแล้ว"
      : `ขั้นที่ ${progress.stepIndex + 1} จาก ${APPLICATION_STEPS.length} — ${APPLICATION_STEPS[progress.stepIndex]}`;

  const text = [
    `คำขอ ${app.application_no} (${app.property.name})`,
    bullet([
      `สถานะ: ${applicationStatusLabel(app.status as ApplicationStatus)}`,
      `ความคืบหน้า: ${step}`,
      `ตอนนี้: ${progress.actorLabel} · อยู่ในขั้นนี้มา ${app.days_waiting} วัน`,
      `สิ่งที่ต้องเกิดต่อไป: ${progress.nextAction}`,
    ]),
  ].join("\n");

  return {
    text,
    links: [
      { href: `/operator/applications/${app.application_no}`, label: "เปิดหน้าคำขอ" },
      ...(app.license_no
        ? [
            {
              href: `/operator/applications/${app.application_no}/license`,
              label: "พิมพ์เอกสารที่ได้รับ",
            },
          ]
        : []),
    ],
    chips: [
      { label: "เจ้าหน้าที่ตรวจเอกสารถึงไหนแล้ว", intent: "status_documents" },
      { label: "มีเอกสารที่ต้องแก้ไขไหม", intent: "status_revision" },
    ],
  };
}

export async function answerDocumentReview(applicationNo: string): Promise<ChatReply> {
  const app = await getApplication(applicationNo);
  const docs = allDocuments(app);
  const notUploaded = docs.filter((d) => d.status === "not_uploaded");

  const text = [
    `เอกสารของคำขอ ${app.application_no} ตอนนี้`,
    summarizeDocuments(app),
    notUploaded.length > 0
      ? `\nยังไม่ได้ส่ง ${notUploaded.length} ฉบับ:\n${bullet(notUploaded.map((d) => `${d.code} ${d.name_th}`))}`
      : "",
  ]
    .filter(Boolean)
    .join("\n");

  return {
    text,
    links: [{ href: `/operator/applications/${app.application_no}`, label: "ไปที่หน้าอัปโหลด" }],
    chips: [{ label: "มีเอกสารที่ต้องแก้ไขไหม", intent: "status_revision" }],
  };
}

export async function answerRevision(applicationNo: string): Promise<ChatReply> {
  const app = await getApplication(applicationNo);
  const problems = allDocuments(app).filter((d) =>
    DOC_PROBLEM.includes(d.status as DocumentStatus),
  );

  if (app.status !== "needs_revision" && problems.length === 0) {
    return {
      text: "ตอนนี้ยังไม่มีเอกสารที่เจ้าหน้าที่ขอให้แก้ไขครับ ถ้ามีเมื่อไร สถานะคำขอจะเปลี่ยนเป็น “รอผู้ยื่นแก้ไข” และเอกสารฉบับนั้นจะขึ้นสีส้มในหน้าคำขอ",
      chips: [{ label: "คำขอของฉันอยู่ขั้นตอนไหน", intent: "status_where" }],
    };
  }

  const text = [
    `คำขอ ${app.application_no} ถูกส่งกลับให้แก้ไขครับ`,
    app.decision_reason ? `\nเหตุผลจากเจ้าหน้าที่: ${app.decision_reason}` : "",
    problems.length > 0
      ? `\nเอกสารที่ต้องแก้:\n${bullet(problems.map((d) => `${d.code} ${d.name_th}`))}`
      : "",
    "\nวิธีแก้: เปิดหน้าคำขอ กดแนบไฟล์ใหม่ที่เอกสารฉบับนั้น ระบบจะเก็บเป็นรุ่นใหม่โดยไม่ลบไฟล์เดิม แล้วกดยื่นอีกครั้ง เรื่องจะกลับเข้าคิวเจ้าหน้าที่ทันที",
  ]
    .filter(Boolean)
    .join("\n");

  return {
    text,
    links: [{ href: `/operator/applications/${app.application_no}`, label: "ไปแก้ไขเอกสาร" }],
  };
}

/** รายการเอกสารจริงจากกฎในฐานข้อมูล ไม่ใช่รายการที่เขียนไว้ในแชทบอท */
export async function answerDocumentsFor(
  rooms: number,
  guests: number,
  hasRestaurant: boolean,
): Promise<ChatReply> {
  const result = await classify({ rooms, guests, has_restaurant: hasRestaurant, local_authority_id: null });

  if (result.is_out_of_scope) {
    return {
      text: `${result.outcome_message}\n\n${result.reason}`,
      chips: [{ label: "ยื่นที่หน่วยงานไหน", intent: "process_where" }],
    };
  }

  const { self_service: own, external, max_upload_mb: maxMb } = result.documents;
  const fee = result.fee
    ? `\nค่าธรรมเนียม ${result.fee.amount.toLocaleString("th-TH")} บาท ต่อ ${result.fee.validity_years} ปี`
    : "\nกรณีนี้ไม่มีค่าธรรมเนียม";

  const text = [
    `ที่พัก ${rooms} ห้อง รับผู้เข้าพัก ${guests} คน ${hasRestaurant ? "มีห้องอาหาร" : "ไม่มีห้องอาหาร"} เข้าข่าย “${result.property_type_name}”`,
    result.reason,
    fee,
    `\nเอกสารที่ทำเองได้ ${own.length} ฉบับ:\n${bullet(own.map(docLine))}`,
    external.length > 0
      ? `\nเอกสารที่ต้องขอจากหน่วยงานอื่น ${external.length} ฉบับ:\n${bullet(external.map(externalLine))}`
      : "",
    // จุดติดต่อผูกกับ อปท. จึงยังไม่มีจนกว่าจะรู้ว่าที่พักอยู่เขตไหน (M4)
    result.documents.needs_local_authority
      ? "\n(ที่อยู่ เวลาทำการ และระยะเวลาของแต่ละหน่วยงาน จะแสดงเมื่อเลือกพื้นที่ที่ที่พักตั้งอยู่แล้ว)"
      : "",
    `\nไฟล์ที่แนบได้: ตามที่ระบุในวงเล็บของแต่ละฉบับ ขนาดไม่เกิน ${maxMb} MB ต่อไฟล์ ถ้ารูปใหญ่เกินให้ถ่ายใหม่ด้วยความละเอียดต่ำลง`,
  ]
    .filter(Boolean)
    .join("\n");

  return {
    text,
    links: [{ href: "/operator/wizard", label: "เริ่มยื่นคำขอจากผลนี้" }],
    chips: [
      { label: "ไฟล์แบบไหนที่แนบได้บ้าง", intent: "documents_file_types" },
      { label: "ขั้นตอนการขออนุญาตมีอะไรบ้าง", intent: "process_overview" },
    ],
  };
}

// ---------------------------------------------------------------- คลังคำถาม

export const INTENTS: ChatIntent[] = [
  // ---------- กระบวนการและขั้นตอน ----------
  {
    id: "process_overview",
    group: "process",
    label: "ขั้นตอนการขออนุญาตมีอะไรบ้าง",
    keywords: ["ขั้นตอน", "ต้องทำอย่างไร", "ทำยังไง", "เริ่มยังไง", "กระบวนการ", "ขอใบอนุญาต"],
    answer: async () => ({
      text: [
        `การขออนุญาตในระบบนี้มี ${APPLICATION_STEPS.length} ขั้น`,
        bullet([
          `${APPLICATION_STEPS[0]} — ประเมินที่พักเพื่อรู้ประเภท แล้วแนบเอกสารให้ครบ พร้อมลงลายมือชื่อในแบบฟอร์มที่ระบบกรอกให้`,
          `${APPLICATION_STEPS[1]} — กดยื่น ระบบส่งเรื่องให้ อปท. ที่ที่พักตั้งอยู่โดยอัตโนมัติ`,
          `${APPLICATION_STEPS[2]} — เจ้าหน้าที่ตรวจทีละฉบับ ถ้ามีจุดต้องแก้จะส่งกลับมาพร้อมเหตุผล`,
          `${APPLICATION_STEPS[3]} — อนุมัติแล้วเจ้าหน้าที่ลงนามออกเอกสาร คุณพิมพ์ได้จากระบบเลย`,
        ]),
        "\nระหว่างทางดูได้ตลอดว่าเรื่องอยู่ขั้นไหนและรอมากี่วันแล้ว",
      ].join("\n"),
      links: [{ href: "/operator/wizard", label: "เริ่มประเมินที่พัก" }],
      chips: [
        { label: "ยื่นที่หน่วยงานไหน", intent: "process_where" },
        { label: "ต้องเตรียมเอกสารอะไรบ้าง", intent: "documents_checklist" },
      ],
    }),
  },
  {
    id: "process_where",
    group: "process",
    label: "ยื่นที่หน่วยงานไหน",
    keywords: ["ยื่นที่ไหน", "หน่วยงาน", "อปท", "เทศบาล", "อบต", "ที่ไหน", "สำนักงาน"],
    answer: async () => {
      const authorities = await listLocalAuthorities();
      return {
        text: [
          "ยื่นผ่านระบบนี้ได้เลยครับ ไม่ต้องเดินทางไปยื่นเอกสารเอง",
          `เมื่อกดยื่น ระบบจะส่งเรื่องให้องค์กรปกครองส่วนท้องถิ่นที่ที่พักของคุณตั้งอยู่ ซึ่งในจังหวัดภูเก็ตมีทั้งหมด ${authorities.length} แห่ง คุณเลือกจากรายการตอนเปิดคำขอ`,
          "\nมีเฉพาะเอกสารบางฉบับที่ต้องไปขอจากหน่วยงานอื่นมาก่อน เช่น ใบอนุญาตก่อสร้างอาคาร ระบบจะบอกชื่อหน่วยงาน ที่อยู่ และระยะเวลาโดยประมาณให้ในรายการเอกสาร",
        ].join("\n"),
        chips: [
          { label: "ต้องเตรียมเอกสารอะไรบ้าง", intent: "documents_checklist" },
          { label: "ขั้นตอนการขออนุญาตมีอะไรบ้าง", intent: "process_overview" },
        ],
      };
    },
  },
  {
    id: "process_duration",
    group: "process",
    label: "ใช้เวลานานไหม",
    keywords: ["นานไหม", "กี่วัน", "ระยะเวลา", "เร็ว", "ช้า", "รอนาน"],
    answer: async () => ({
      text: [
        "ขั้นที่ใช้เวลานานที่สุดมักไม่ใช่ขั้นตอนในระบบ แต่เป็นเอกสารที่ต้องไปขอจากหน่วยงานอื่นก่อน ระบบจึงบอกระยะเวลาโดยประมาณของเอกสารแต่ละฉบับไว้ให้วางแผนล่วงหน้า",
        "\nส่วนหลังจากกดยื่นแล้ว ระบบจะแสดงตลอดว่าเรื่องอยู่ขั้นไหน ใครกำลังถือเรื่อง และค้างอยู่กี่วันแล้ว ถ้าค้างนานผิดปกติจะเห็นได้ทันทีจากจำนวนวัน",
      ].join("\n"),
      chips: [
        { label: "คำขอของฉันอยู่ขั้นตอนไหน", intent: "status_where" },
        { label: "ต้องเตรียมเอกสารอะไรบ้าง", intent: "documents_checklist" },
      ],
    }),
  },
  {
    id: "process_signature",
    group: "process",
    label: "ต้องเซ็นเอกสารตรงไหน",
    keywords: ["เซ็น", "ลายเซ็น", "ลายมือชื่อ", "เซ็นชื่อ"],
    answer: async () => ({
      text: [
        "แบบฟอร์มราชการที่ต้องใช้ ระบบกรอกให้จากข้อมูลที่คุณกรอกไว้แล้ว เหลือแค่ลงลายมือชื่อ",
        "เปิดหน้าคำขอ กดปุ่ม “เปิดแบบฟอร์ม” ที่เอกสารแบบฟอร์ม แล้วเซ็นด้วยเมาส์หรือนิ้วได้เลย ถ้าถนัดเซ็นบนกระดาษ ให้กดพิมพ์แบบฟอร์มออกไปเซ็นแล้วถ่ายรูปมาอัปโหลดแทนได้",
        "\nต้องลงลายมือชื่อก่อนจึงจะกดยื่นคำขอได้ เพราะลายมือชื่อคือสิ่งที่ทำให้เอกสารมีผล",
      ].join("\n"),
      chips: [{ label: "คำขอของฉันอยู่ขั้นตอนไหน", intent: "status_where" }],
    }),
  },

  // ---------- เอกสาร ----------
  {
    id: "documents_checklist",
    group: "documents",
    label: "ต้องเตรียมเอกสารอะไรบ้าง",
    keywords: ["เอกสาร", "เตรียมอะไร", "ใช้อะไรบ้าง", "เช็คลิสต์", "checklist"],
    answer: async (ctx) => {
      if (ctx.isLoggedIn) {
        const rows = await myApplications();
        if (rows.length > 0) {
          return {
            text: "รายการเอกสารต่างกันตามประเภทที่พักครับ ดูของคำขอที่มีอยู่ หรือให้ผมประเมินจากขนาดที่พักใหม่ก็ได้",
            chips: [
              ...rows.map((r) => ({
                label: `เอกสารของ ${r.application_no}`,
                value: `documents_of:${r.application_no}`,
              })),
              { label: "ประเมินจากขนาดที่พัก", intent: "documents_by_size" },
            ],
          };
        }
      }
      return {
        text: "รายการเอกสารต่างกันตามประเภทที่พัก ซึ่งดูจากจำนวนห้องพัก จำนวนผู้เข้าพัก และการมีห้องอาหาร\n\nที่พักของคุณมีกี่ห้องครับ (พิมพ์เป็นตัวเลข)",
        expect: "rooms",
      };
    },
  },
  {
    id: "documents_by_size",
    group: "documents",
    label: "ประเมินเอกสารจากขนาดที่พัก",
    keywords: ["กี่ห้อง", "ขนาดที่พัก", "ประเมิน", "จำนวนห้อง"],
    answer: async () => ({
      text: "ได้ครับ ที่พักของคุณมีกี่ห้อง (พิมพ์เป็นตัวเลข)",
      expect: "rooms",
    }),
  },
  {
    id: "documents_file_types",
    group: "documents",
    label: "ไฟล์แบบไหนที่แนบได้บ้าง",
    keywords: ["ไฟล์", "pdf", "รูป", "ถ่ายรูป", "สแกน", "ขนาดไฟล์", "นามสกุล", "jpg", "png"],
    answer: async (ctx) => {
      // ชนิดไฟล์ที่รับกำหนดเป็นรายเอกสารในฐานข้อมูล จึงต้องอ่านจากรายการจริง
      let docs: RequiredDocument[] = [];
      let maxMb: number | null = null;

      if (ctx.isLoggedIn) {
        const rows = await myApplications();
        if (rows.length > 0) {
          const app = await getApplication(rows[0].application_no);
          docs = allDocuments(app);
          maxMb = app.documents.max_upload_mb;
        }
      }

      const detail =
        docs.length > 0
          ? `\nของคำขอ ${docs.length} ฉบับที่คุณมี:\n${bullet(
              docs.map((d) =>
                d.is_system_form
                  ? `${d.code} ${d.name_th} — ระบบกรอกให้ ใช้เฉพาะรูปลายมือชื่อ`
                  : `${d.code} ${d.name_th} — ${describeAccepted(d.accepted_mime)}`,
              ),
            )}`
          : "\nบางฉบับรับเฉพาะไฟล์ PDF บางฉบับรับรูปถ่าย JPG/PNG ระบบจะเขียนกำกับไว้ที่เอกสารแต่ละฉบับ และจะเตือนทันทีถ้าเลือกไฟล์ผิดชนิด";

      const size = maxMb ? `ขนาดไม่เกิน ${maxMb} MB ต่อไฟล์` : "ขนาดไฟล์มีเพดานที่ระบบกำหนดไว้";

      return {
        text: [
          `ชนิดไฟล์ที่รับกำหนดไว้เป็นรายเอกสาร ไม่ได้ใช้กฎเดียวกันทั้งหมด ${size}`,
          detail,
          "\nอัปโหลดฉบับเดิมซ้ำได้ ระบบจะเก็บเป็นรุ่นใหม่โดยไม่ลบไฟล์เดิม เจ้าหน้าที่จึงย้อนดูได้ว่าเคยตรวจไฟล์ไหน",
        ].join("\n"),
        chips: [{ label: "ต้องเตรียมเอกสารอะไรบ้าง", intent: "documents_checklist" }],
      };
    },
  },
  {
    id: "documents_external",
    group: "documents",
    label: "เอกสารที่ต้องไปขอจากหน่วยงานอื่น",
    keywords: ["ขอจากหน่วยงาน", "ใบอนุญาตก่อสร้าง", "อ.1", "อ.5", "ไปขอที่ไหน", "กองช่าง"],
    answer: async (ctx) => {
      if (ctx.isLoggedIn) {
        const rows = await myApplications();
        if (rows.length > 0) {
          const app = await getApplication(rows[0].application_no);
          const external = app.documents.external;
          if (external.length > 0) {
            return {
              text: [
                `คำขอ ${app.application_no} มีเอกสารที่ต้องขอจากหน่วยงานอื่น ${external.length} ฉบับ`,
                bullet(external.map(externalLine)),
                "\nแนะนำให้เริ่มจากฉบับที่ใช้เวลานานที่สุดก่อน ระหว่างรอก็เตรียมเอกสารฉบับอื่นไปพร้อมกันได้",
              ].join("\n"),
              links: [
                { href: `/operator/applications/${app.application_no}`, label: "ดูรายการเอกสาร" },
              ],
            };
          }
        }
      }
      return {
        text: "เอกสารกลุ่มนี้คือฉบับที่ออกโดยหน่วยงานอื่น เช่น ใบอนุญาตเกี่ยวกับอาคาร ระบบจะบอกชื่อหน่วยงาน ที่อยู่ เวลาทำการ ระยะเวลาโดยประมาณ และเอกสารที่ต้องเตรียมไปด้วย เมื่อคุณประเมินที่พักแล้ว",
        links: [{ href: "/operator/wizard", label: "ประเมินที่พักเพื่อดูรายการ" }],
      };
    },
  },

  // ---------- สถานะคำขอ ----------
  {
    id: "status_where",
    group: "status",
    label: "คำขอของฉันอยู่ขั้นตอนไหน",
    keywords: ["สถานะ", "ถึงไหน", "ขั้นตอนไหน", "คำขอของฉัน", "ติดตาม", "อนุมัติหรือยัง"],
    answer: async (ctx) => {
      const pick = await pickApplication(ctx, "status_of");
      if (pick) return pick;
      return answerStatus(await onlyApplicationNo());
    },
  },
  {
    id: "status_documents",
    group: "status",
    label: "เจ้าหน้าที่ตรวจเอกสารถึงไหนแล้ว",
    keywords: ["ตรวจแล้วหรือยัง", "ตรวจถึงไหน", "เจ้าหน้าที่ตรวจ", "ผ่านหรือยัง"],
    answer: async (ctx) => {
      const pick = await pickApplication(ctx, "documents_review_of");
      if (pick) return pick;
      return answerDocumentReview(await onlyApplicationNo());
    },
  },
  {
    id: "status_revision",
    group: "status",
    label: "มีเอกสารที่ต้องแก้ไขไหม",
    keywords: ["แก้ไข", "ตีกลับ", "ส่งกลับ", "ไม่ผ่าน", "ต้องแก้", "เพิ่มเติม"],
    answer: async (ctx) => {
      const pick = await pickApplication(ctx, "revision_of");
      if (pick) return pick;
      return answerRevision(await onlyApplicationNo());
    },
  },
  {
    id: "status_result",
    group: "status",
    label: "อนุมัติแล้วต้องทำอะไรต่อ",
    keywords: ["อนุมัติแล้ว", "ได้ใบอนุญาต", "พิมพ์ใบอนุญาต", "หนังสือรับรอง", "เอกสารสิทธิ์"],
    answer: async (ctx) => {
      if (!ctx.isLoggedIn) return LOGIN_REQUIRED;
      const rows = await myApplications();
      const issued = rows.find((r) => r.status === "license_issued");
      if (!issued) {
        return {
          text: "ยังไม่มีคำขอที่ออกเอกสารแล้วครับ เมื่อเจ้าหน้าที่อนุมัติและลงนามออกเอกสาร ระบบจะขึ้นปุ่มพิมพ์ให้ที่หน้าคำขอทันที",
          chips: [{ label: "คำขอของฉันอยู่ขั้นตอนไหน", intent: "status_where" }],
        };
      }
      return {
        text: `คำขอ ${issued.application_no} ออกเอกสารเรียบร้อยแล้ว เปิดหน้าเอกสารแล้วกดพิมพ์ หรือเลือกบันทึกเป็น PDF เก็บไว้ได้เลย เอกสารมีเลขอ้างอิงสำหรับตรวจสอบย้อนกลับและลายมือชื่อเจ้าหน้าที่ผู้ออกเอกสารอยู่บนหน้ากระดาษ`,
        links: [
          {
            href: `/operator/applications/${issued.application_no}/license`,
            label: "เปิดเอกสารเพื่อพิมพ์",
          },
        ],
      };
    },
  },
];

export const INTENT_BY_ID = new Map(INTENTS.map((i) => [i.id, i]));

/** รายการคำถามทั้งหมด แยกตามสามกลุ่ม — ใช้เมื่อผู้ใช้อยากเห็นว่าถามอะไรได้บ้าง */
export function topics(): ChatReply {
  const groups = (Object.keys(GROUP_LABEL) as ChatGroup[]).map(
    (g) => `${GROUP_LABEL[g]} (${INTENTS.filter((i) => i.group === g).length} คำถาม)`,
  );
  return {
    text: `ตอนนี้ผมตอบได้ ${INTENTS.length} คำถามใน 3 กลุ่ม\n${bullet(groups)}\n\nเลือกได้เลยครับ`,
    chips: INTENTS.map((i) => ({ label: i.label, intent: i.id })),
  };
}

/** ข้อความต้อนรับ — ตั้งใจให้เห็นสามกลุ่มคำถามตั้งแต่เปิด */
export function greeting(): ChatReply {
  return {
    text: "สวัสดีครับ ผมเป็นผู้ช่วยตอบคำถามเรื่องการขออนุญาตที่พัก ถามเป็นข้อความได้เลย หรือเลือกจากคำถามที่พบบ่อยด้านล่างครับ",
    chips: [
      { label: "ขั้นตอนการขออนุญาตมีอะไรบ้าง", intent: "process_overview" },
      { label: "ต้องเตรียมเอกสารอะไรบ้าง", intent: "documents_checklist" },
      { label: "คำขอของฉันอยู่ขั้นตอนไหน", intent: "status_where" },
      { label: "ดูคำถามทั้งหมด", value: "topics" },
    ],
  };
}

/**
 * จับคำสำคัญจากข้อความที่ผู้ใช้พิมพ์
 *
 * ตั้งใจให้เป็นการนับคำตรง ๆ ไม่ใช่โมเดลภาษา เพื่อให้ทีมอธิบายได้ว่าคำตอบ
 * มาจากไหนทุกครั้ง และเพิ่มคำถามใหม่ได้โดยไม่ต้องเทรนอะไร
 */
export function routeByKeywords(text: string): ChatIntent | null {
  const q = text.toLocaleLowerCase("th-TH");
  let best: { intent: ChatIntent; score: number } | null = null;

  for (const intent of INTENTS) {
    const score = intent.keywords.filter((k) => q.includes(k)).length;
    if (score > 0 && (!best || score > best.score)) best = { intent, score };
  }
  return best?.intent ?? null;
}

/** ตอบเมื่อจับคำไม่ได้ — ต้องไม่เดา และต้องพาผู้ใช้ไปต่อได้เสมอ */
export function fallback(): ChatReply {
  return {
    text: "ขอโทษครับ ผมยังตอบคำถามนี้ไม่ได้ ลองเลือกจากหัวข้อด้านล่าง หรือถ้าเป็นเรื่องเฉพาะของคำขอใบนั้นจริง ๆ ติดต่อเจ้าหน้าที่ อปท. ที่รับเรื่องได้เลยครับ",
    chips: INTENTS.filter((i) =>
      ["process_overview", "documents_checklist", "status_where", "documents_file_types"].includes(
        i.id,
      ),
    ).map((i) => ({ label: i.label, intent: i.id })),
  };
}
