import { Building2, FileCheck2, Upload } from "lucide-react";

import { Logo, PrototypeBadge } from "@/components/brand/Logo";
import { Mascot } from "@/components/brand/Mascot";
import { AiNotice } from "@/components/common/AiNotice";
import { DocRow } from "@/components/common/DocRow";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { StatusPill } from "@/components/common/StatusPill";
import { Stepper } from "@/components/common/Stepper";
import type { DocumentStatus } from "@/types/enums";

/**
 * หน้าตรวจสอบระบบดีไซน์ (ชั่วคราว)
 *
 * หน้านี้มีไว้ยืนยันว่า token / ฟอนต์ / โลโก้ / มาสคอต / คอมโพเนนต์กลาง
 * ทำงานครบ  เมื่อเริ่มทำหน้าจริงแล้วให้แทนที่ด้วยหน้าแรกของผู้ประกอบการ
 */
const ALL_DOC_STATUS: DocumentStatus[] = [
  "not_uploaded",
  "uploaded",
  "system_flagged",
  "officer_reviewing",
  "revision_requested",
  "approved",
  "not_required",
];

export default function ScaffoldCheckPage() {
  return (
    <main className="mx-auto max-w-6xl space-y-8 px-4 py-10">
      <div className="flex flex-wrap items-center gap-3">
        <Logo variant="lockup" href="" className="w-[260px]" />
        <PrototypeBadge />
      </div>

      <PageHeader
        eyebrow="00 / ตรวจสอบโครงสร้าง"
        title="โครงโปรเจกต์พร้อมใช้งานแล้ว"
        description="หน้านี้เป็นหน้าชั่วคราวสำหรับยืนยันว่าดีไซน์โทเคน ฟอนต์ไทย โลโก้ มาสคอต และคอมโพเนนต์กลางทำงานครบถ้วน"
        aside={<Mascot pose="wave" size="md" priority className="w-28" />}
      />

      <Stepper
        steps={[
          { label: "ข้อมูลที่พัก" },
          { label: "บริการ", note: "อยู่ในขั้นนี้" },
          { label: "ผลประเมิน" },
        ]}
        current={1}
      />

      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <SectionCard
          icon={FileCheck2}
          tone="brand"
          title="ทำเองได้เลย"
          description="เตรียมและอัปโหลดเอกสารด้วยตัวเอง ผ่านระบบ HoTLinE Doc"
        >
          <div className="space-y-2">
            <DocRow
              code="A01"
              title="แบบคำขอ ร.ร.1"
              description="ระบบจะสร้างแบบคำขอให้โดยอัตโนมัติจากข้อมูลที่กรอก"
              status="approved"
              required
            />
            <DocRow
              code="A02"
              title="สำเนาบัตรประชาชน"
              description="ถ่ายด้วยมือถือได้"
              status="revision_requested"
              required
            />
            <DocRow code="A06" title="แผนที่สังเขป + พิกัด" status="not_uploaded" />
          </div>
        </SectionCard>

        <div className="space-y-5">
          <SectionCard
            icon={Building2}
            tone="info"
            title="ต้องไปขอก่อน"
            description="ติดต่อหน่วยงานที่เกี่ยวข้อง เพื่อขอเอกสารจากหน่วยงานภายนอก"
          >
            <DocRow
              code="B01"
              title="ใบอนุญาตก่อสร้าง อ.1"
              description="กองช่าง อปท. ในพื้นที่"
              leadTime="30 – 45 วัน"
            />
          </SectionCard>

          <SectionCard icon={Upload} title="ตัวอย่างการแจ้งเตือนจาก AI">
            <AiNotice
              level="error"
              title="ภาพเบลอ กรุณาถ่ายใหม่"
              description="ผลตรวจเบื้องต้น ไม่ใช่ผลอนุมัติ"
              thumbnail={<Mascot pose="inspect" size="sm" className="w-12" />}
            />
          </SectionCard>
        </div>
      </div>

      <SectionCard title="สถานะเอกสารทั้ง 7 แบบ" description="สีทั้งหมดกำหนดไว้ที่ StatusPill ที่เดียว">
        <div className="flex flex-wrap gap-2">
          {ALL_DOC_STATUS.map((s) => (
            <StatusPill key={s} status={s} />
          ))}
        </div>
      </SectionCard>

      <SectionCard title="มาสคอตทั้ง 6 ท่า" description="เรียกผ่าน <Mascot pose=... /> ไม่ต้องจำชื่อไฟล์">
        <div className="flex flex-wrap items-end gap-6">
          {(["wave", "upload", "inspect", "waiting", "success", "support"] as const).map((p) => (
            <figure key={p} className="text-center">
              <Mascot pose={p} size="sm" className="w-20" />
              <figcaption className="mt-1 text-xs text-ink-muted">{p}</figcaption>
            </figure>
          ))}
        </div>
      </SectionCard>

      <footer className="border-t border-line pt-4 text-sm text-ink-muted">
        เกณฑ์ ค่าใช้จ่าย และระยะเวลาเป็นข้อมูลต้นแบบ ต้องยืนยันก่อนใช้งานจริง
      </footer>
    </main>
  );
}
