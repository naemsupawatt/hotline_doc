"use client";

import {
  Building2,
  Clock,
  Landmark,
  MapPin,
  PencilLine,
  Upload,
  Users,
  UtensilsCrossed,
} from "lucide-react";
import { useEffect, useState } from "react";

import { Mascot } from "@/components/brand/Mascot";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { StatusPill } from "@/components/common/StatusPill";
import { ApiError } from "@/lib/api";
import { type Application, getApplication, labelForKind } from "@/lib/applications";
import { type RequiredDocument, describeAccepted } from "@/lib/wizard";
import type { ApplicationStatus } from "@/types/enums";

export function ApplicationView({ applicationNo }: { applicationNo: string }) {
  const [application, setApplication] = useState<Application | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getApplication(applicationNo)
      .then(setApplication)
      .catch((err) =>
        setError(
          err instanceof ApiError ? err.message : "เปิดคำขอไม่ได้ กรุณาลองใหม่อีกครั้ง",
        ),
      );
  }, [applicationNo]);

  if (error) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center">
        <Mascot pose="support" size="md" className="mx-auto w-40" />
        <h1 className="mt-6 text-2xl font-bold text-ink">เปิดคำขอนี้ไม่ได้</h1>
        <p role="alert" className="mt-2 text-ink-muted">
          {error}
        </p>
      </main>
    );
  }

  if (!application) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center text-ink-muted">
        กำลังโหลดคำขอ…
      </main>
    );
  }

  const { property, documents } = application;

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      <PageHeader
        eyebrow={`เลขที่คำขอ ${application.application_no}`}
        title={property.name}
        description={property.address.full_address}
        aside={
          <div className="text-right">
            <StatusPill kind="application" status={application.status as ApplicationStatus} />
            <p className="mt-1.5 flex items-center justify-end gap-1 text-sm text-ink-muted">
              <Clock className="size-3.5" aria-hidden />
              อยู่ในขั้นนี้ {application.days_waiting} วัน
            </p>
          </div>
        }
      />

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <SectionCard
          icon={Building2}
          title="ข้อมูลที่พัก"
          description="ใช้ประกอบแบบหนังสือแจ้งสถานที่พักที่ไม่เป็นโรงแรม"
          className="lg:col-span-2"
        >
          <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
            <Fact icon={Building2} label="จำนวนห้องพัก" value={`${property.room_count} ห้อง`} />
            <Fact icon={Users} label="รับผู้เข้าพักได้" value={`${property.max_guests} คน`} />
            <Fact
              icon={UtensilsCrossed}
              label="ห้องอาหาร"
              value={property.has_restaurant ? "มี" : "ไม่มี"}
            />
            <Fact
              icon={PencilLine}
              label="ลักษณะที่พัก"
              value={
                property.accommodation_kind === "other"
                  ? (property.accommodation_kind_other ?? "อื่น ๆ")
                  : labelForKind(property.accommodation_kind)
              }
            />
            <Fact
              icon={MapPin}
              label="พื้นที่ตั้ง"
              value={property.local_authority_name}
              className="sm:col-span-2"
            />
          </dl>
        </SectionCard>

        <div className="rounded-card border border-line bg-brand-50/40 p-5">
          <p className="text-sm font-semibold text-ink">ผลการจำแนกประเภท</p>
          <p className="mt-1 text-xl font-bold text-ink">{application.property_type_name}</p>
          <p className="mt-2 text-sm text-ink-muted">{application.reason}</p>

          {application.fee && (
            <p className="mt-3 text-sm text-ink">
              ค่าธรรมเนียม{" "}
              <span className="font-bold text-brand-600">
                {application.fee.amount.toLocaleString("th-TH")} บาท
              </span>{" "}
              ต่อ {application.fee.validity_years} ปี
            </p>
          )}

          {application.matched_rule_code && (
            <p className="mt-3 text-xs text-ink-muted">
              ตัดสินด้วยเกณฑ์รหัส{" "}
              <span className="font-mono">{application.matched_rule_code}</span> ณ วันที่เปิดคำขอ
            </p>
          )}
        </div>
      </div>

      <h2 className="mt-10 text-xl font-bold text-ink">เอกสารของคำขอนี้</h2>
      <p className="mt-1 text-ink-muted">
        ต้องครบทุกฉบับที่ระบุว่าบังคับ จึงจะยื่นคำขอได้
      </p>

      <div className="mt-5 grid gap-6 lg:grid-cols-2">
        <SectionCard
          icon={PencilLine}
          tone="brand"
          title="ทำเองได้เลย"
          description="เตรียมและอัปโหลดเอกสารด้วยตัวเอง"
        >
          <div className="space-y-3">
            {documents.self_service.map((doc) => (
              <DocumentRow key={doc.code} doc={doc} />
            ))}
          </div>
        </SectionCard>

        <SectionCard
          icon={Landmark}
          tone="info"
          title="ต้องไปขอก่อน"
          description="ติดต่อหน่วยงานที่เกี่ยวข้อง แล้วนำฉบับที่ลงนามแล้วมาอัปโหลด"
        >
          <div className="space-y-3">
            {documents.external.map((doc) => (
              <DocumentRow key={doc.code} doc={doc} />
            ))}
          </div>
        </SectionCard>
      </div>
    </main>
  );
}

function Fact({
  icon: Icon,
  label,
  value,
  className,
}: {
  icon: typeof Building2;
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <dt className="flex items-center gap-1.5 text-sm text-ink-muted">
        <Icon className="size-3.5 shrink-0" aria-hidden />
        {label}
      </dt>
      <dd className="mt-0.5 font-medium text-ink">{value}</dd>
    </div>
  );
}

function DocumentRow({ doc }: { doc: RequiredDocument }) {
  return (
    <article className="rounded-xl border border-line bg-surface p-3">
      <div className="flex items-start gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-brand-50 text-sm font-bold text-brand-700">
          {doc.code}
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-medium text-ink">{doc.name_th}</h3>
            {doc.is_mandatory && (
              <span className="rounded-full bg-danger-bg px-2 py-0.5 text-xs font-medium text-danger-fg">
                บังคับ
              </span>
            )}
            {/* ยังไม่มีการอัปโหลดในระบบ ทุกฉบับจึงเป็น "ยังไม่ได้อัปโหลด" */}
            <StatusPill status="not_uploaded" />
          </div>

          <p className="mt-1 flex items-center gap-1.5 text-sm text-ink-muted">
            {doc.is_system_form ? (
              <PencilLine className="size-3.5 shrink-0" aria-hidden />
            ) : (
              <Upload className="size-3.5 shrink-0" aria-hidden />
            )}
            {doc.is_system_form
              ? "ระบบสร้างเอกสารให้จากข้อมูลที่กรอก"
              : describeAccepted(doc.accepted_mime)}
          </p>

          {doc.contact_point && (
            <p className="mt-1.5 flex items-start gap-1.5 text-sm text-ink-muted">
              <MapPin className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              ไปติดต่อที่ {doc.contact_point.office_name}
              {doc.contact_point.estimated_days
                ? ` · ใช้เวลาประมาณ ${doc.contact_point.estimated_days} วัน`
                : ""}
            </p>
          )}
        </div>
      </div>
    </article>
  );
}
