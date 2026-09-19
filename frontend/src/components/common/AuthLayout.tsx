import { CircleQuestionMark, Globe } from "lucide-react";

import { Logo, PrototypeBadge } from "@/components/brand/Logo";
import { Mascot } from "@/components/brand/Mascot";

type Props = {
  /** หัวข้อบนแผงซ้าย — เปลี่ยนตามหน้า */
  headline: React.ReactNode;
  tagline: string;
  children: React.ReactNode;
};

/**
 * โครงหน้าสำหรับหน้าที่ยังไม่ได้เข้าสู่ระบบ (เข้าสู่ระบบ / สมัครสมาชิก / ยืนยันตัวตน)
 *
 * แยกออกมาเพราะทั้งสามหน้าใช้ header + แผงซ้าย + footer ชุดเดียวกัน
 * ถ้าปล่อยให้ก๊อปไว้ทุกหน้า พอแก้ลิงก์ footer ทีเดียวจะต้องไล่แก้หลายที่
 */
export function AuthLayout({ headline, tagline, children }: Props) {
  return (
    <div className="flex min-h-dvh flex-col bg-canvas">
      <header className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-3 px-4 py-5 sm:px-6">
        <Logo variant="lockup" className="w-[200px] sm:w-[240px]" />
        <PrototypeBadge className="hidden sm:inline-block" />

        <div className="ml-auto flex items-center gap-1 text-sm text-ink-muted sm:gap-3">
          {/* TODO: ต่อหน้าศูนย์ช่วยเหลือเมื่อมีหน้านั้นแล้ว */}
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 hover:text-brand-600"
          >
            <CircleQuestionMark className="size-5" aria-hidden />
            ช่วยเหลือ
          </button>
          <span aria-hidden className="h-5 w-px bg-line" />
          {/* TODO C4: สลับภาษาไทย/อังกฤษเมื่อทำ i18n แล้ว */}
          <button
            type="button"
            className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 hover:text-brand-600"
          >
            <Globe className="size-5" aria-hidden />
            TH
          </button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-10 sm:px-6">
        <div className="grid overflow-hidden rounded-3xl border border-line bg-surface shadow-sm md:grid-cols-2">
          <BrandPanel headline={headline} tagline={tagline} />
          <section className="px-6 py-10 sm:px-10 lg:px-14">{children}</section>
        </div>
      </main>

      <footer className="mx-auto w-full max-w-6xl px-4 pb-8 sm:px-6">
        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-sm text-ink-muted">
          {/* TODO: ต่อหน้านโยบาย/เงื่อนไขเมื่อมีหน้านั้นแล้ว */}
          <button type="button" className="hover:text-brand-600">
            นโยบายความเป็นส่วนตัว
          </button>
          <span aria-hidden className="h-4 w-px bg-line" />
          <button type="button" className="hover:text-brand-600">
            เงื่อนไขการใช้งาน
          </button>
        </div>
        <p className="mt-3 text-center text-xs text-ink-muted">
          ระบบต้นแบบเพื่อการสาธิต ข้อมูลทั้งหมดเป็นข้อมูลจำลอง ไม่ใช่ข้อมูลของบุคคลจริง
        </p>
      </footer>
    </div>
  );
}

/** แผงซ้าย — พื้นไล่สีแบรนด์ + มาสคอตท่า wave (ท่าต้อนรับตาม decisions.md ข้อ 8) */
function BrandPanel({ headline, tagline }: { headline: React.ReactNode; tagline: string }) {
  return (
    <section className="relative hidden overflow-hidden bg-brand-600 md:block">
      <div className="absolute inset-0 bg-gradient-to-br from-brand-400 via-brand-500 to-brand-700" />
      {/* วงกลมจาง ๆ แทนภาพประกอบลายเส้น ให้พื้นไม่เรียบจนแบน */}
      <div aria-hidden className="absolute -top-16 -left-10 size-72 rounded-full bg-brand-200/20" />
      <div aria-hidden className="absolute top-24 -right-16 size-80 rounded-full bg-brand-100/15" />
      <div aria-hidden className="absolute -bottom-24 left-12 size-96 rounded-full bg-brand-100/10" />

      <div className="relative flex h-full flex-col justify-between p-10 lg:p-12">
        <div>
          <h2 className="text-3xl leading-tight font-bold text-white lg:text-4xl">{headline}</h2>
          <p className="mt-4 text-lg text-brand-100">{tagline}</p>
        </div>

        <div className="flex justify-center pt-8">
          <Mascot pose="wave" size="lg" className="w-56 drop-shadow-xl lg:w-64" priority />
        </div>
      </div>
    </section>
  );
}
