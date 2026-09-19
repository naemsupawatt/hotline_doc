"use client";

import { ArrowRight, Lock, Mail } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Mascot } from "@/components/brand/Mascot";
import { AuthLayout } from "@/components/common/AuthLayout";
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
    <AuthLayout
      headline={
        <>
          เรื่องที่พัก
          <br />
          จัดการง่ายในที่เดียว
        </>
      }
      tagline="เตรียมเอกสาร ยื่นคำขอ และติดตามสถานะ"
    >
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
          <Link
            href="/register"
            className="mt-3 inline-flex min-h-12 w-full items-center justify-center rounded-xl border-2 border-brand-500 bg-surface px-5 py-3 text-base font-semibold text-brand-600 hover:bg-brand-50"
          >
            สมัครสมาชิก
          </Link>

          <DemoAccounts />
        </>
      )}
    </AuthLayout>
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
