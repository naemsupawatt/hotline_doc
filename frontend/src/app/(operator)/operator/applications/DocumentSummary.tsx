/**
 * รายการเอกสารแบบย่อ สำหรับกางดูในหน้า "คำขอของฉัน"
 *
 * ต่างจาก `DocumentRow` ในหน้ารายละเอียดตรงที่อันนี้ **อ่านอย่างเดียว**
 * ไม่มีปุ่มอัปโหลดหรือเปิดไฟล์ เพราะคำถามของคนที่กางดูจากหน้ารายการคือ
 * "ฉบับไหนส่งแล้ว ฉบับไหนยังค้าง และค้างมานานแค่ไหน" ไม่ใช่ "ขอส่งไฟล์เดี๋ยวนี้"
 * ถ้าจะลงมือทำจริงมีปุ่มพาไปหน้ารายละเอียดอยู่แล้ว
 *
 * ป้ายสถานะยังใช้ `StatusPill` ที่เดียวเหมือนเดิม ไฟล์นี้ไม่รู้จักสีของสถานะ
 */
import { CalendarCheck, Clock } from "lucide-react";

import { StatusPill } from "@/components/common/StatusPill";
import { thaiDate } from "@/lib/applications";
import { documentTiming, groupByParent } from "@/lib/documents";
import { cn } from "@/lib/utils";
import type { RequiredDocument } from "@/lib/wizard";
import type { DocumentStatus } from "@/types/enums";

/** สรุปหัวแผง — ตอบคำถามแรกของคนที่กางดูโดยไม่ต้องไล่อ่านทีละแถว */
function summarize(docs: RequiredDocument[]) {
  // เอกสารที่ไม่จำเป็นสำหรับกรณีนี้ ไม่ควรถูกนับเป็นตัวหารให้ดูเหมือนยังขาด
  const counted = docs.filter((doc) => doc.status !== "not_required");
  const timings = counted.map((doc) => documentTiming(doc));

  const sent = timings.filter((t) => t.sentAt !== null).length;
  const waitingDays = timings
    .map((t) => t.daysAwaiting)
    .filter((days): days is number => days !== null);

  return {
    total: counted.length,
    sent,
    missingMandatory: counted.filter(
      (doc, i) => doc.is_mandatory && timings[i].sentAt === null,
    ).length,
    longestWait: waitingDays.length > 0 ? Math.max(...waitingDays) : null,
  };
}

export function DocumentSummary({ docs }: { docs: RequiredDocument[] }) {
  const groups = groupByParent(docs);
  const { total, sent, missingMandatory, longestWait } = summarize(docs);

  if (total === 0) {
    return (
      <p className="px-4 pb-4 text-sm text-ink-muted sm:px-5">
        คำขอนี้ยังไม่มีรายการเอกสารที่ต้องเตรียม
      </p>
    );
  }

  return (
    <div className="px-4 pb-4 sm:px-5 sm:pb-5">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-xl bg-canvas px-4 py-3 text-sm">
        <span className="font-semibold text-ink">
          ส่งแล้ว {sent.toLocaleString("th-TH")} จาก {total.toLocaleString("th-TH")} ฉบับ
        </span>
        {missingMandatory > 0 && (
          <span className="font-semibold text-warn-fg">
            ยังขาดเอกสารบังคับ {missingMandatory.toLocaleString("th-TH")} ฉบับ
          </span>
        )}
        {longestWait !== null && (
          <span className="text-ink-muted">
            รอเจ้าหน้าที่ตรวจนานสุด {longestWait.toLocaleString("th-TH")} วัน
          </span>
        )}
      </div>

      <ul className="mt-3 space-y-2">
        {groups.map(({ parent, children }) => (
          <li key={parent.code}>
            <DocumentLine doc={parent} />
            {children.length > 0 && (
              /* ฉบับย่อยคือช่องแนบที่อยู่ในแบบฟอร์มของฉบับแม่ ต้องแสดงซ้อนเข้าไป
                 ไม่ใช่ลอยเป็นรายการแยก ไม่งั้นผู้ใช้ไม่รู้ว่ามันสัมพันธ์กับอะไร */
              <ul className="mt-2 space-y-2 border-l-2 border-line pl-3 sm:pl-4">
                {children.map((child) => (
                  <li key={child.code}>
                    <DocumentLine doc={child} nested />
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function DocumentLine({ doc, nested = false }: { doc: RequiredDocument; nested?: boolean }) {
  const { sentAt, daysAwaiting } = documentTiming(doc);

  return (
    <div
      className={cn(
        "flex flex-wrap items-start gap-x-3 gap-y-1.5 rounded-xl border border-line bg-surface px-3 py-2.5",
        nested && "bg-canvas",
      )}
    >
      <span className="rounded-md bg-brand-50 px-2 py-0.5 font-mono text-xs font-bold text-brand-700">
        {doc.code}
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="font-medium break-words text-ink">{doc.name_th}</span>
          {doc.is_mandatory && (
            <span className="rounded-full bg-danger-bg px-2 py-0.5 text-xs font-medium text-danger-fg">
              บังคับ
            </span>
          )}
        </div>

        {/* บรรทัดเวลา ไม่พูดซ้ำกับป้ายสถานะ บอกเฉพาะ "เมื่อไร" กับ "กี่วันแล้ว" */}
        <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-sm text-ink-muted">
          {sentAt === null ? (
            <span>ยังไม่ได้ส่ง</span>
          ) : (
            <span className="flex items-center gap-1.5">
              <CalendarCheck className="size-3.5 shrink-0" aria-hidden />
              ส่งเมื่อ {thaiDate(sentAt)}
            </span>
          )}
          {daysAwaiting !== null && (
            <span className="flex items-center gap-1.5">
              <Clock className="size-3.5 shrink-0" aria-hidden />
              {daysAwaiting === 0
                ? "ส่งวันนี้ รอเจ้าหน้าที่ตรวจ"
                : `รอตรวจมาแล้ว ${daysAwaiting.toLocaleString("th-TH")} วัน`}
            </span>
          )}
        </p>
      </div>

      <StatusPill status={doc.status as DocumentStatus} />
    </div>
  );
}
