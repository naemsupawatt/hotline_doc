"use client";

import { ArrowRight, CircleQuestionMark, Globe, Lock, Mail } from "lucide-react";
import { useState } from "react";

import { Logo, PrototypeBadge } from "@/components/brand/Logo";
import { Mascot } from "@/components/brand/Mascot";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError } from "@/lib/api";
import { type AuthUser, login } from "@/lib/auth";

export function LoginView() {
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    // ตรวจฝั่งหน้าเว็บก่อนยิง API เพื่อให้ผู้ใช้รู้ผลทันที
    if (!identifier.trim() || !password) {
      setError("กรุณากรอกอีเมลหรือเบอร์โทรศัพท์ และรหัสผ่านให้ครบก่อนเข้าสู่ระบบ");
      return;
    }

    setPending(true);
    try {
      setUser(await login(identifier, password, remember));
    } catch (err) {
      // NFR Usability: แสดงข้อความที่ผู้ใช้ทั่วไปเข้าใจ ไม่ใช่ error code ดิบ
      setError(
        err instanceof ApiError
          ? err.message
          : "เชื่อมต่อระบบไม่ได้ กรุณาตรวจสอบอินเทอร์เน็ตแล้วลองใหม่อีกครั้ง",
      );
    } finally {
      setPending(false);
    }
  }

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
          <BrandPanel />

          <section className="px-6 py-10 sm:px-10 lg:px-14">
            {user ? (
              <SignedIn user={user} />
            ) : (
              <>
                <h1 className="text-3xl font-bold text-ink sm:text-4xl">ยินดีต้อนรับ</h1>
                <p className="mt-2 text-ink-muted">เข้าสู่ระบบเพื่อจัดการคำขอของคุณ</p>

                <form onSubmit={onSubmit} noValidate className="mt-8 space-y-5">
                  <TextField
                    label="อีเมล หรือ เบอร์โทรศัพท์"
                    icon={Mail}
                    type="text"
                    inputMode="email"
                    autoComplete="username"
                    placeholder="name@example.com"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                  />

                  <TextField
                    label="รหัสผ่าน"
                    icon={Lock}
                    revealable
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />

                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <label className="flex items-center gap-2.5 text-sm text-ink">
                      <input
                        type="checkbox"
                        checked={remember}
                        onChange={(e) => setRemember(e.target.checked)}
                        className="size-5 rounded border-line accent-brand-500"
                      />
                      จดจำการเข้าสู่ระบบ
                    </label>

                    {/* TODO M1: ต่อหน้าขอรหัสผ่านใหม่ */}
                    <button
                      type="button"
                      className="text-sm font-semibold text-brand-600 underline underline-offset-4 hover:text-brand-400"
                    >
                      ลืมรหัสผ่าน
                    </button>
                  </div>

                  {error ? (
                    // role="alert" ให้ screen reader อ่านทันทีที่ข้อความปรากฏ
                    <p
                      role="alert"
                      className="rounded-xl bg-danger-bg px-4 py-3 text-sm font-medium text-danger-fg"
                    >
                      {error}
                    </p>
                  ) : null}

                  <Button type="submit" disabled={pending}>
                    {pending ? "กำลังเข้าสู่ระบบ…" : "เข้าสู่ระบบ"}
                    {pending ? null : <ArrowRight className="size-5" aria-hidden />}
                  </Button>
                </form>

                <p className="mt-6 text-center text-sm text-ink-muted">ยังไม่มีบัญชี?</p>
                {/* TODO M1: ต่อหน้าสมัครสมาชิก */}
                <Button variant="outline" type="button" className="mt-3">
                  สมัครสมาชิก
                </Button>

                <DemoAccounts />
              </>
            )}
          </section>
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
function BrandPanel() {
  return (
    <section className="relative hidden overflow-hidden bg-brand-600 md:block">
      <div className="absolute inset-0 bg-gradient-to-br from-brand-400 via-brand-500 to-brand-700" />
      {/* วงกลมจาง ๆ แทนภาพประกอบลายเส้น ให้พื้นไม่เรียบจนแบน */}
      <div aria-hidden className="absolute -top-16 -left-10 size-72 rounded-full bg-brand-200/20" />
      <div aria-hidden className="absolute top-24 -right-16 size-80 rounded-full bg-brand-100/15" />
      <div aria-hidden className="absolute -bottom-24 left-12 size-96 rounded-full bg-brand-100/10" />

      <div className="relative flex h-full flex-col justify-between p-10 lg:p-12">
        <div>
          <h2 className="text-3xl leading-tight font-bold text-white lg:text-4xl">
            เรื่องที่พัก
            <br />
            จัดการง่ายในที่เดียว
          </h2>
          <p className="mt-4 text-lg text-brand-100">เตรียมเอกสาร ยื่นคำขอ และติดตามสถานะ</p>
        </div>

        <div className="flex justify-center pt-8">
          <Mascot pose="wave" size="lg" className="w-56 drop-shadow-xl lg:w-64" priority />
        </div>
      </div>
    </section>
  );
}

/** สถานะหลังเข้าสู่ระบบสำเร็จ

    ยังไม่ redirect เพราะหน้าปลายทางของแต่ละบทบาท (/operator, /officer, ...)
    ยังไม่ถูกสร้าง — ถ้า push ไปตอนนี้ผู้ใช้จะเจอ 404 ทันทีหลังกดปุ่ม
    เมื่อสร้างหน้าเหล่านั้นแล้วให้เปลี่ยนเป็น router.push(homeFor(user.role))
*/
function SignedIn({ user }: { user: AuthUser }) {
  return (
    <div className="flex flex-col items-center py-6 text-center">
      <Mascot pose="success" size="md" className="w-40" />
      <h1 className="mt-6 text-2xl font-bold text-ink sm:text-3xl">เข้าสู่ระบบสำเร็จ</h1>
      <p className="mt-2 text-ink-muted">
        ยินดีต้อนรับ {user.full_name}
        <br />
        บทบาทของคุณคือ <span className="font-semibold text-brand-600">{user.role}</span>
      </p>
      <p className="mt-6 rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-700">
        หน้าถัดไปของบทบาทนี้ยังอยู่ระหว่างพัฒนา
      </p>
    </div>
  );
}

/** กล่องบัญชีสาธิต — มีเพื่อให้กรรมการกดลองได้ทันทีโดยไม่ต้องถาม
    ต้องเอาออกก่อนนำระบบไปใช้จริง */
function DemoAccounts() {
  const accounts = [
    ["ผู้ประกอบการ", "operator@example.com"],
    ["เจ้าหน้าที่ท้องถิ่น", "officer@example.com"],
    ["ส่วนกลาง", "central@example.com"],
    ["ผู้ดูแลระบบ", "admin@example.com"],
  ];

  return (
    <div className="mt-8 rounded-xl border border-dashed border-line bg-canvas p-4">
      <p className="text-xs font-semibold text-ink">บัญชีสำหรับทดลองใช้ (ข้อมูลจำลอง)</p>
      <dl className="mt-2 space-y-1 text-xs text-ink-muted">
        {accounts.map(([label, email]) => (
          <div key={email} className="flex flex-wrap gap-x-2">
            <dt className="min-w-28">{label}</dt>
            <dd className="font-mono">{email}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-xs text-ink-muted">
        รหัสผ่านทุกบัญชี <span className="font-mono">demo1234</span>
      </p>
    </div>
  );
}
