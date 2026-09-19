import {
  Building2,
  Check,
  CircleQuestionMark,
  FileCheck2,
  MapPin,
  Route,
} from "lucide-react";

import { Logo, PrototypeBadge } from "@/components/brand/Logo";
import { Mascot } from "@/components/brand/Mascot";

type Props = {
  headline: React.ReactNode;
  tagline: string;
  children: React.ReactNode;
};

export function AuthLayout({ headline, tagline, children }: Props) {
  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex min-h-20 w-full max-w-7xl items-center gap-4 px-5 sm:px-8">
          <Logo variant="wordmark" className="w-40 sm:w-52" />
          <PrototypeBadge className="hidden sm:inline-block" />
          <details className="relative ml-auto text-sm text-ink-muted">
            <summary className="flex min-h-11 list-none items-center gap-2 rounded-xl px-3 hover:bg-brand-50 [&::-webkit-details-marker]:hidden">
              <CircleQuestionMark className="size-5" aria-hidden />
              ช่วยเหลือ
            </summary>
            <div className="absolute right-0 z-50 mt-3 w-64 rounded-2xl border border-line bg-surface p-5 shadow-lift">
              <p className="font-semibold text-ink">เริ่มใช้งานอย่างไร?</p>
              <p className="mt-2 leading-relaxed">
                สมัครสมาชิกหรือเข้าสู่ระบบ
                จากนั้นประเมินที่พักเพื่อดูรายการเอกสารที่ต้องเตรียม
              </p>
              <p className="mt-3 text-xs">
                ทดลองใช้ได้ด้วยบัญชีสาธิตที่หน้าเข้าสู่ระบบ
              </p>
            </div>
          </details>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-8 sm:py-10">
        <div className="grid overflow-hidden rounded-3xl border border-line bg-surface shadow-lift md:grid-cols-[0.95fr_1.05fr]">
          <BrandPanel headline={headline} tagline={tagline} />
          <section className="px-6 py-8 sm:px-10 sm:py-10 lg:px-14">
            {children}
          </section>
        </div>
      </main>

      <footer className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-6 pb-6 text-xs text-ink-muted sm:px-8">
        <span>HoTLinE Doc · เรื่องที่พัก มีคำตอบที่ชัดเจน</span>
        <span>ระบบต้นแบบเพื่อการสาธิต · ใช้ข้อมูลจำลองทั้งหมด</span>
      </footer>
    </div>
  );
}

function BrandPanel({
  headline,
  tagline,
}: {
  headline: React.ReactNode;
  tagline: string;
}) {
  const features = [
    {
      icon: Building2,
      title: "รู้ประเภทที่พัก",
      text: "ประเมินเบื้องต้น เพื่อเริ่มต้นได้ถูกทาง",
    },
    {
      icon: FileCheck2,
      title: "เตรียมเอกสารครบ",
      text: "รู้ว่าต้องใช้อะไร และไปติดต่อที่ไหน",
    },
    {
      icon: Route,
      title: "ติดตามได้ทุกขั้นตอน",
      text: "ดูความคืบหน้าของคำขอในที่เดียว",
    },
  ];
  return (
    <section className="auth-panel relative overflow-hidden border-b border-brand-100 md:border-r md:border-b-0">
      <div
        aria-hidden
        className="auth-orbit absolute -bottom-28 -left-28 size-96"
      />
      <div
        aria-hidden
        className="auth-orbit absolute -bottom-16 -left-16 size-72"
      />
      <div className="relative flex h-full flex-col px-6 py-7 sm:p-10 lg:p-12">
        <p className="mb-5 flex items-center gap-2 text-xs font-semibold text-brand-700">
          <MapPin className="size-4" aria-hidden />
          สำหรับผู้ประกอบการที่พัก จังหวัดภูเก็ต
        </p>
        <h2 className="text-3xl leading-snug font-bold tracking-tight text-navy-900 lg:text-4xl">
          {headline}
        </h2>
        <p className="mt-4 text-sm leading-relaxed text-brand-700 sm:text-base">
          {tagline}
        </p>
        <div className="mt-8 hidden space-y-5 md:block">
          {features.map(({ icon: Icon, title, text }) => (
            <div key={title} className="flex items-start gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-surface/80 text-brand-600">
                <Icon className="size-5" aria-hidden />
              </span>
              <div>
                <p className="text-sm font-semibold text-navy-700">{title}</p>
                <p className="mt-0.5 text-xs text-ink-muted">{text}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="relative mt-auto hidden justify-center pt-8 md:flex">
          <Mascot
            pose="wave"
            size="lg"
            className="relative w-44 lg:w-52"
            priority
          />
          <span className="absolute right-0 bottom-4 flex items-center gap-2 rounded-xl border border-brand-100 bg-surface/95 px-3 py-2.5 text-xs font-medium text-brand-700 shadow-card">
            <Check className="size-4" aria-hidden />
            เริ่มต้นอย่างมั่นใจ
          </span>
        </div>
      </div>
    </section>
  );
}
