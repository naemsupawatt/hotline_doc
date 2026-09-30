/**
 * จัดกลุ่มเอกสารให้ฉบับย่อยไปอยู่ใต้ฉบับแม่
 *
 * เอกสารบางฉบับเป็น "ช่องแนบที่อยู่ในแบบฟอร์มอีกฉบับ" เช่น หนังสือรับรอง
 * นิติบุคคลที่เป็นช่องหนึ่งในแบบ ร.ร.1 ถ้าแสดงลอยเป็นรายการแยก ผู้ใช้จะไม่รู้ว่า
 * มันสัมพันธ์กับอะไร API จึงส่ง parent_code มาให้ และหน้าจอจัดกลุ่มด้วยฟังก์ชันนี้
 */
import { daysSince } from "@/lib/applications";
import type { RequiredDocument } from "@/lib/wizard";
import type { DocumentStatus } from "@/types/enums";

export type DocumentGroup = {
  parent: RequiredDocument;
  children: RequiredDocument[];
};

export function groupByParent(docs: RequiredDocument[]): DocumentGroup[] {
  const groups = new Map<string, DocumentGroup>();
  const orphans: DocumentGroup[] = [];

  // รอบแรกเก็บฉบับแม่ก่อน เพราะฉบับย่อยอ้างถึงรหัสของแม่
  for (const doc of docs) {
    if (!doc.parent_code) groups.set(doc.code, { parent: doc, children: [] });
  }

  for (const doc of docs) {
    if (!doc.parent_code) continue;
    const group = groups.get(doc.parent_code);
    // ถ้าหาแม่ไม่เจอ (เช่น แม่ไม่ได้อยู่ในรายการของประเภทนี้) ให้แสดงเป็นรายการปกติ
    // ดีกว่าซ่อนหายไปเฉย ๆ
    if (group) group.children.push(doc);
    else orphans.push({ parent: doc, children: [] });
  }

  return [...groups.values(), ...orphans];
}

/**
 * สถานะที่ "ลูกบอลอยู่ในมือเจ้าหน้าที่" สำหรับเอกสารรายฉบับ
 *
 * แนวคิดเดียวกับ `actor` ใน `lib/progress.ts` แต่ระดับเอกสาร ไม่ใช่ระดับคำขอ
 * อยู่คนละที่กันเพราะตอบคนละคำถาม: `progress.ts` ตอบว่าคำขอทั้งใบค้างที่ใคร
 * ส่วนชุดนี้ตอบว่าเอกสารฉบับนี้กำลังรอเจ้าหน้าที่ตรวจอยู่หรือเปล่า
 *
 * ใช้ตัดสินแค่ว่า "ควรนับวันที่รอให้ดูไหม" — ผู้ยื่นอยากรู้ว่ารอมานานแค่ไหน
 * เฉพาะตอนที่ตัวเองทำอะไรต่อไม่ได้แล้ว ถ้าเป็นคิวของตัวเองการนับวันไม่ช่วยอะไร
 * ส่วนสถานะ -> สี/ข้อความ ยังเป็นหน้าที่ของ `StatusPill.tsx` ที่เดียวเหมือนเดิม
 */
const AWAITING_OFFICER: ReadonlySet<DocumentStatus> = new Set<DocumentStatus>([
  "uploaded",
  "officer_reviewing",
]);

export type DocumentTiming = {
  /** เวลาที่ส่งไฟล์รุ่นล่าสุดของเอกสารฉบับนี้ — `null` เมื่อยังไม่เคยส่ง */
  sentAt: string | null;
  /** รอเจ้าหน้าที่ตรวจมากี่วันแล้ว — `null` เมื่อยังไม่ส่ง หรือลูกบอลไม่ได้อยู่ที่เจ้าหน้าที่ */
  daysAwaiting: number | null;
};

/**
 * "ส่งเมื่อไร และรอมากี่วันแล้ว" ของเอกสารหนึ่งฉบับ
 *
 * เอกสารฉบับเดียวแนบได้หลายไฟล์ (ภาพหลายมุม = คนละ slot) จึงยึดไฟล์ที่ใหม่ที่สุด
 * เป็นวันที่ส่ง เพราะผู้ใช้นับจากครั้งล่าสุดที่ตัวเองส่งของเข้าไป
 */
export function documentTiming(doc: RequiredDocument): DocumentTiming {
  let sentAt: string | null = null;
  for (const file of doc.files) {
    if (sentAt === null || Date.parse(file.uploaded_at) > Date.parse(sentAt)) {
      sentAt = file.uploaded_at;
    }
  }

  if (sentAt === null) return { sentAt: null, daysAwaiting: null };

  return {
    sentAt,
    daysAwaiting: AWAITING_OFFICER.has(doc.status as DocumentStatus) ? daysSince(sentAt) : null,
  };
}
