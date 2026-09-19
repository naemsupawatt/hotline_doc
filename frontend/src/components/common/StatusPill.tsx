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
  license_issued: { label: "ออกใบอนุญาตแล้ว",   cls: "bg-brand-50 text-brand-700",    dot: "bg-brand-500" },
};

type Props =
  | { kind?: "document"; status: DocumentStatus; className?: string }
  | { kind: "application"; status: ApplicationStatus; className?: string };

export function StatusPill(props: Props) {
  const map = props.kind === "application" ? APP : DOC;
  const s = (map as Record<string, { label: string; cls: string; dot: string }>)[props.status];
  if (!s) return null;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        s.cls,
        props.className,
      )}
    >
      {/* NFR Accessibility: มีจุดสี แต่ก็ต้องมีข้อความกำกับเสมอ ไม่ใช้สีสื่อความหมายลำพัง */}
      <span className={cn("size-1.5 rounded-full", s.dot)} aria-hidden />
      {s.label}
    </span>
  );
}

export function applicationStatusLabel(status: ApplicationStatus): string {
  return APP[status].label;
}
