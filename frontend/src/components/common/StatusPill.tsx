import { cn } from "@/lib/utils";
import type { ApplicationStatus, DocumentStatus } from "@/types/enums";

/**
 * จุดเดียวในระบบที่แปลงสถานะ -> สี + ข้อความไทย
 * ห้ามเขียน if (status === "approved") ... สีเขียว กระจายในหน้าอื่น
 */
const DOC: Record<DocumentStatus, { label: string; cls: string; dot: string }> = {
  not_uploaded:       { label: "ยังไม่ได้อัปโหลด",  cls: "bg-slate-100 text-slate-600", dot: "bg-slate-400" },
  uploaded:           { label: "อัปโหลดแล้ว รอตรวจ", cls: "bg-info-bg text-info-fg",     dot: "bg-info-fg" },
  system_flagged:     { label: "ระบบตรวจพบปัญหา",   cls: "bg-danger-bg text-danger-fg", dot: "bg-danger-fg" },
  officer_reviewing:  { label: "เจ้าหน้าที่กำลังตรวจ", cls: "bg-review-bg text-review-fg", dot: "bg-review-fg" },
  revision_requested: { label: "เจ้าหน้าที่ขอให้แก้ไข", cls: "bg-warn-bg text-warn-fg",    dot: "bg-warn-fg" },
  approved:           { label: "ผ่านการตรวจ",       cls: "bg-success-bg text-success-fg", dot: "bg-success-fg" },
  not_required:       { label: "ไม่จำเป็นสำหรับกรณีนี้", cls: "bg-white text-ink-muted border border-line", dot: "bg-slate-300" },
};

const APP: Record<ApplicationStatus, { label: string; cls: string; dot: string }> = {
  draft:          { label: "ร่าง",             cls: "bg-slate-100 text-slate-600",   dot: "bg-slate-400" },
  submitted:      { label: "ยื่นแล้ว",          cls: "bg-info-bg text-info-fg",       dot: "bg-info-fg" },
  under_review:   { label: "อยู่ระหว่างตรวจสอบ", cls: "bg-review-bg text-review-fg",   dot: "bg-review-fg" },
  needs_revision: { label: "รอผู้ยื่นแก้ไข",     cls: "bg-warn-bg text-warn-fg",       dot: "bg-warn-fg" },
  approved:       { label: "อนุมัติแล้ว",       cls: "bg-success-bg text-success-fg", dot: "bg-success-fg" },
  rejected:       { label: "ไม่อนุมัติ",        cls: "bg-danger-bg text-danger-fg",   dot: "bg-danger-fg" },
  // "ออกเอกสารแล้ว" ไม่ใช่ "ออกใบอนุญาตแล้ว" เพราะสถานะนี้ครอบทั้งใบอนุญาต
  // และหนังสือรับรองการแจ้ง (license.kind) คำขอที่ไม่เข้าข่ายโรงแรมไม่ได้ใบอนุญาต
  license_issued: { label: "ออกเอกสารแล้ว",     cls: "bg-brand-50 text-brand-700",    dot: "bg-brand-500" },
};

/** md ใช้ตอนป้ายอยู่คู่กับหัวข้อใหญ่ เช่นหัวการ์ดในรายการคำขอ */
const SIZE = {
  sm: { pill: "gap-1.5 px-2.5 py-1 text-xs", dot: "size-1.5" },
  md: { pill: "gap-2 px-3 py-1.5 text-sm", dot: "size-2" },
} as const;

type Props = { size?: keyof typeof SIZE } & (
  | { kind?: "document"; status: DocumentStatus; className?: string }
  | { kind: "application"; status: ApplicationStatus; className?: string }
);

export function StatusPill(props: Props) {
  const map = props.kind === "application" ? APP : DOC;
  const s = (map as Record<string, { label: string; cls: string; dot: string }>)[props.status];
  if (!s) return null;
  const size = SIZE[props.size ?? "sm"];
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-medium",
        size.pill,
        s.cls,
        props.className,
      )}
    >
      {/* NFR Accessibility: มีจุดสี แต่ก็ต้องมีข้อความกำกับเสมอ ไม่ใช้สีสื่อความหมายลำพัง */}
      <span className={cn("rounded-full", size.dot, s.dot)} aria-hidden />
      {s.label}
    </span>
  );
}

export function applicationStatusLabel(status: ApplicationStatus): string {
  return APP[status].label;
}
