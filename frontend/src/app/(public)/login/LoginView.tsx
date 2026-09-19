"use client";

import { ArrowRight, Lock, Mail, Phone } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Mascot } from "@/components/brand/Mascot";
import { AuthLayout } from "@/components/common/AuthLayout";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError } from "@/lib/api";
import { type AuthUser, hasHome, homeFor, login } from "@/lib/auth";

/** ผูก aria-controls ของปุ่มเข้ากับกล่องคำแนะนำ ให้ screen reader รู้ว่าปุ่มเปิดอะไร */
const PASSWORD_HELP_ID = "forgot-password-help";

export function LoginView() {
  const router = useRouter();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [showPasswordHelp, setShowPasswordHelp] = useState(false);
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
      const signedIn = await login(identifier, password, remember);

      // บทบาทที่ยังไม่มีหน้าปลายทาง ให้ค้างที่หน้าจอ "สำเร็จ" ดีกว่าพาไป 404
      if (hasHome(signedIn.role)) {
        router.push(homeFor(signedIn.role));
        return; // คง pending ไว้จนกว่าจะเปลี่ยนหน้า ผู้ใช้จะได้ไม่กดซ้ำ
      }
      setUser(signedIn);
      setPending(false);
    } catch (err) {
      // NFR Usability: แสดงข้อความที่ผู้ใช้ทั่วไปเข้าใจ ไม่ใช่ error code ดิบ
      setError(
        err instanceof ApiError
          ? err.message
          : "เชื่อมต่อระบบไม่ได้ กรุณาตรวจสอบอินเทอร์เน็ตแล้วลองใหม่อีกครั้ง",
      );
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
              autoComplete="username"
              placeholder="name@example.com หรือ 0812345678"
              hint="ใช้ได้ทั้งอีเมลและเบอร์โทรที่สมัครไว้"
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

              <button
                type="button"
                onClick={() => setShowPasswordHelp((v) => !v)}
                aria-expanded={showPasswordHelp}
                aria-controls={PASSWORD_HELP_ID}
                className="text-sm font-semibold text-brand-600 underline underline-offset-4 hover:text-brand-400"
              >
                ลืมรหัสผ่าน
              </button>
            </div>

            {showPasswordHelp ? <PasswordHelp /> : null}

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

/** คำแนะนำเมื่อลืมรหัสผ่าน

    รอบนี้ยังไม่ทำการตั้งรหัสผ่านใหม่ด้วยตนเอง เพราะไม่อยู่ใน Must Have
    และการส่งลิงก์รีเซ็ตต้องมีระบบอีเมลจริงซึ่งเกินขอบเขต 12 ชั่วโมง
    แต่ปุ่มต้องตอบสนองเสมอ ปุ่มที่กดแล้วเงียบทำให้ผู้ใช้คิดว่าระบบค้าง
    (NFR Usability) จึงบอกช่องทางที่ผู้ใช้ทำได้จริงแทน
*/
function PasswordHelp() {
  return (
    <div
      id={PASSWORD_HELP_ID}
      className="rounded-xl border border-line bg-canvas px-4 py-3 text-sm text-ink"
    >
      <p className="font-semibold">ยังตั้งรหัสผ่านใหม่ด้วยตนเองไม่ได้ในขณะนี้</p>
      <p className="mt-1.5 text-ink-muted">
        กรุณาติดต่อเจ้าหน้าที่องค์กรปกครองส่วนท้องถิ่นในเขตที่พักของคุณ
        เพื่อขอตั้งรหัสผ่านใหม่ โดยเตรียมเลขประจำตัวประชาชนและเบอร์โทรที่ใช้สมัครไว้
      </p>
      <p className="mt-2 flex items-center gap-2 text-ink-muted">
        <Phone className="size-4 shrink-0" aria-hidden />
        ดูเบอร์ติดต่อของแต่ละท้องถิ่นได้จากหน้ารายการหน่วยงาน
      </p>
    </div>
  );
}

/** สถานะหลังเข้าสู่ระบบสำเร็จ สำหรับบทบาทที่ยังไม่มีหน้าปลายทาง

    ผู้ประกอบการถูก redirect ไปหน้าประเมินที่พักแล้ว จอนี้จึงเหลือไว้ให้
    เจ้าหน้าที่ / ส่วนกลาง / ผู้ดูแลระบบ จนกว่าหน้าของแต่ละบทบาทจะเสร็จ
    (เพิ่มบทบาทลง ROLES_WITH_HOME ใน lib/auth.ts เมื่อสร้างหน้าเสร็จ)
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
