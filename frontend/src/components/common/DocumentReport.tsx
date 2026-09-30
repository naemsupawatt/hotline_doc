/**
 * ชิ้นส่วนที่ใช้ร่วมกันของรายงานเอกสารฝั่งส่วนกลาง
 *
 * มีสองหน้าที่เป็นคู่แฝดกัน มองคนละฝั่งของกระบวนการ:
 *   `central/documents`          ของที่ส่งมาแล้วแต่ค้างที่เจ้าหน้าที่
 *   `central/missing-documents`  ของที่ผู้ยื่นยังไม่ได้ส่งเข้ามา
 *
 * โครงเหมือนกันทั้งคู่ (แถบสรุป + รายการเรียงอันดับ + แท่งเทียบขนาด +
 * การกระจายตัวรายเขต) ต่างกันแค่ "บรรทัดรายละเอียด" ของแต่ละแถว จึงรับเข้ามา
 * เป็น children แทนการทำสองชุด ถ้าแยกกันเขียน วันหนึ่งสองหน้าจะดูคนละระบบ
 */
import type { ReactNode } from "react";

import type { Clock } from "lucide-react";

import type { Bucket } from "@/lib/reports";

export function ReportStat({
  icon: Icon,
  label,
  value,
  alarming = false,
}: {
  icon: typeof Clock;
  label: string;
  value: string;
  alarming?: boolean;
}) {
  return (
    <div className="flex items-center gap-4 rounded-card border border-line bg-surface p-5 shadow-card">
      <span className="grid size-12 shrink-0 place-items-center rounded-full bg-brand-50">
        <Icon className="size-6 text-brand-700" aria-hidden />
      </span>
      <div className="min-w-0">
        <p className="text-sm text-ink-muted">{label}</p>
        <p
          className={`mt-1 text-2xl font-bold tabular-nums ${alarming ? "text-danger-fg" : "text-ink"}`}
        >
          {value}
        </p>
      </div>
    </div>
  );
}

/**
 * หนึ่งฉบับ = หนึ่งแถว พร้อมแท่งเทียบขนาดและการกระจายตัวรายเขต
 *
 * แท่งใช้สีเดียวทั้งชุด ด้วยเหตุผลเดียวกับ BarList ในหน้าภาพรวม — เป็นการวัด
 * ปริมาณของหมวดที่ไม่ได้แข่งกันเชิงตัวตน ถ้าไล่สีรายแท่ง สีจะกลายเป็นข้อมูลปลอม
 * ตัวเลขกำกับทุกแท่ง จึงอ่านได้โดยไม่ต้องพึ่งความยาวแท่งหรือสี
 */
export function RankedDocumentRow({
  rank,
  code,
  name,
  count,
  unit,
  max,
  areas,
  children,
}: {
  rank: number;
  code: string;
  name: string;
  count: number;
  /** หน่วยที่ต่อท้ายตัวเลข เช่น "คำขอ" — ต่างกันได้ตามความหมายของแต่ละรายงาน */
  unit: string;
  /** ค่าสูงสุดของทั้งรายการ ใช้เทียบความยาวแท่ง */
  max: number;
  areas: Bucket[];
  /** บรรทัดรายละเอียดเฉพาะของรายงานนั้น วางไว้หน้าชิปรายเขต */
  children?: ReactNode;
}) {
  return (
    <li>
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-sm font-bold tabular-nums text-ink-muted">{rank}.</span>
        <span className="rounded-md bg-brand-50 px-2 py-0.5 font-mono text-xs font-bold text-brand-700">
          {code}
        </span>
        <span className="min-w-0 flex-1 font-medium break-words text-ink">{name}</span>
        <span className="text-sm font-bold tabular-nums text-ink">
          {count.toLocaleString("th-TH")} {unit}
        </span>
      </div>

      <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-line">
        <div
          className="h-full rounded-full bg-brand-500"
          style={{ width: `${(count / Math.max(max, 1)) * 100}%` }}
        />
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm">
        {children}
        {areas.map((area) => (
          <span key={area.key} className="rounded-full bg-canvas px-2.5 py-1 text-xs text-ink-muted">
            {area.label}{" "}
            <span className="font-semibold tabular-nums text-ink">
              {area.count.toLocaleString("th-TH")}
            </span>
          </span>
        ))}
      </div>
    </li>
  );
}
