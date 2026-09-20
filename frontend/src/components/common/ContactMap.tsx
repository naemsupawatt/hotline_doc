"use client";

import { ChevronDown, ExternalLink, Map } from "lucide-react";
import { useState } from "react";

import { mapEmbedUrl } from "@/lib/maps";
import { cn } from "@/lib/utils";

/**
 * แผนที่ + ลิงก์นำทางของสำนักงานที่ต้องไปติดต่อ (M4)
 *
 * เดิมหน้าจอบอกแค่ชื่อสำนักงาน ซึ่งพอสำหรับคนที่รู้จักอยู่แล้ว แต่ผู้ประกอบการ
 * ที่ไม่เคยไปต้องเอาชื่อไปค้นเองแล้วเดาว่าอันไหนใช่ ซึ่งเป็นจุดที่ไปผิดที่ได้ง่าย
 *
 * แผนที่ถูกซ่อนไว้ก่อนและโหลดเมื่อกดเท่านั้น ด้วยสองเหตุผล: หน้าคำขอหนึ่งหน้า
 * มีเอกสารหลายฉบับที่มีจุดติดต่อ ถ้าฝัง iframe ทุกอันตั้งแต่แรกหน้าจะอืด
 * และการสาธิตไม่ควรยิงออกอินเทอร์เน็ตโดยที่ผู้ใช้ไม่ได้ขอ
 *
 * ลิงก์ "เปิดใน Google Maps" อยู่เสมอ ไม่ว่าจะฝังแผนที่ได้หรือไม่
 */
export function ContactMap({
  mapUrl,
  officeName,
  className,
}: {
  mapUrl: string | null;
  officeName: string;
  className?: string;
}) {
  const [open, setOpen] = useState(false);

  if (!mapUrl) return null;
  const embed = mapEmbedUrl(mapUrl);

  return (
    <div className={cn("print:hidden", className)}>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        {embed && (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="inline-flex min-h-9 items-center gap-1.5 text-sm font-semibold text-brand-600 underline underline-offset-4 hover:text-brand-400"
          >
            <Map className="size-4" aria-hidden />
            {open ? "ซ่อนแผนที่" : "ดูแผนที่"}
            <ChevronDown
              className={cn("size-4 transition-transform", open && "rotate-180")}
              aria-hidden
            />
          </button>
        )}

        <a
          href={mapUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex min-h-9 items-center gap-1.5 text-sm font-semibold text-brand-600 underline underline-offset-4 hover:text-brand-400"
        >
          <ExternalLink className="size-4" aria-hidden />
          เปิดใน Google Maps
        </a>
      </div>

      {open && embed && (
        <div className="mt-2 overflow-hidden rounded-xl border border-line">
          <iframe
            src={embed}
            title={`แผนที่ ${officeName}`}
            loading="lazy"
            referrerPolicy="no-referrer-when-downgrade"
            className="h-56 w-full border-0"
          />
        </div>
      )}
    </div>
  );
}
