/**
 * จัดกลุ่มเอกสารให้ฉบับย่อยไปอยู่ใต้ฉบับแม่
 *
 * เอกสารบางฉบับเป็น "ช่องแนบที่อยู่ในแบบฟอร์มอีกฉบับ" เช่น หนังสือรับรอง
 * นิติบุคคลที่เป็นช่องหนึ่งในแบบ ร.ร.1 ถ้าแสดงลอยเป็นรายการแยก ผู้ใช้จะไม่รู้ว่า
 * มันสัมพันธ์กับอะไร API จึงส่ง parent_code มาให้ และหน้าจอจัดกลุ่มด้วยฟังก์ชันนี้
 */
import type { RequiredDocument } from "@/lib/wizard";

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
