"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, CalendarDays, IdCard, Lock, Mail, User } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { AuthLayout } from "@/components/common/AuthLayout";
import { Mascot } from "@/components/brand/Mascot";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError } from "@/lib/api";
import { type AuthUser, register as registerAccount } from "@/lib/auth";
import { formatThaiId, normalizeThaiId } from "@/lib/thaiId";
import { type RegisterForm, registerSchema } from "./schema";

export function RegisterView() {
  const [user, setUser] = useState<AuthUser | null>(null);

  return (
    <AuthLayout
      headline={
        <>
          เริ่มต้นใช้งาน
          <br />
          ในไม่กี่ขั้นตอน
        </>
      }
      tagline="สมัครครั้งเดียว ใช้ยื่นคำขอได้ทุกที่พักของคุณ"
    >
      {user ? <DoneStep user={user} /> : <RegisterForm onRegistered={setUser} />}
    </AuthLayout>
  );
}

function RegisterForm({ onRegistered }: { onRegistered: (user: AuthUser) => void }) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    control,
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    // ตรวจตอนออกจากช่อง ไม่ใช่ตอนพิมพ์ทุกตัวอักษร จะได้ไม่ขึ้นข้อความแดงรัว ๆ
    mode: "onBlur",
  });

  async function onSubmit(values: RegisterForm) {
    setServerError(null);
    try {
      onRegistered(
        await registerAccount({
          first_name: values.first_name,
          last_name: values.last_name,
          national_id: normalizeThaiId(values.national_id),
          birth_date: values.birth_date,
          email: values.email,
          password: values.password,
        }),
      );
    } catch (err) {
      setServerError(
        err instanceof ApiError
          ? err.message
          : "เชื่อมต่อระบบไม่ได้ กรุณาตรวจสอบอินเทอร์เน็ตแล้วลองใหม่อีกครั้ง",
      );
    }
  }

  return (
    <>
      <h1 className="text-3xl font-bold text-ink sm:text-4xl">สมัครสมาชิก</h1>
      <p className="mt-2 text-ink-muted">กรอกข้อมูลตามบัตรประชาชนเพื่อใช้ยื่นคำขอ</p>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-8 space-y-5">
        <div className="grid gap-5 sm:grid-cols-2">
          <TextField
            label="ชื่อ"
            icon={User}
            autoComplete="given-name"
            placeholder="สมชาย"
            error={errors.first_name?.message}
            {...register("first_name")}
          />
          <TextField
            label="นามสกุล"
            autoComplete="family-name"
            placeholder="ใจดี"
            error={errors.last_name?.message}
            {...register("last_name")}
          />
        </div>

        {/* จัดรูปแบบขณะพิมพ์ให้อ่านง่าย แต่ส่งเลข 13 หลักล้วนไป API */}
        <Controller
          control={control}
          name="national_id"
          defaultValue=""
          render={({ field }) => (
            <TextField
              label="เลขประจำตัวประชาชน"
              icon={IdCard}
              inputMode="numeric"
              placeholder="1-2345-67890-12-3"
              hint="กรอก 13 หลักตามหน้าบัตร ระบบใส่ขีดให้เอง"
              error={errors.national_id?.message}
              value={formatThaiId(field.value ?? "")}
              onChange={(e) => field.onChange(normalizeThaiId(e.target.value))}
              onBlur={field.onBlur}
            />
          )}
        />

        <Controller
          control={control}
          name="birth_date"
          defaultValue=""
          render={({ field }) => (
            <TextField
              label="วันเดือนปีเกิด"
              icon={CalendarDays}
              type="date"
              max={new Date().toISOString().slice(0, 10)}
              hint={buddhistHint(field.value)}
              error={errors.birth_date?.message}
              {...field}
            />
          )}
        />

        <TextField
          label="อีเมล"
          icon={Mail}
          type="email"
          autoComplete="email"
          placeholder="name@example.com"
          hint="ใช้อีเมลนี้เข้าสู่ระบบและรับการแจ้งเตือนสถานะคำขอ"
          error={errors.email?.message}
          {...register("email")}
        />

        <div className="grid gap-5 sm:grid-cols-2">
          <TextField
            label="รหัสผ่าน"
            icon={Lock}
            revealable
            autoComplete="new-password"
            placeholder="อย่างน้อย 8 ตัวอักษร"
            error={errors.password?.message}
            {...register("password")}
          />
          <TextField
            label="ยืนยันรหัสผ่าน"
            revealable
            autoComplete="new-password"
            placeholder="กรอกรหัสผ่านอีกครั้ง"
            error={errors.confirm_password?.message}
            {...register("confirm_password")}
          />
        </div>

        <p className="rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-700">
          เลขประจำตัวประชาชนใช้เพื่อยืนยันตัวตนกับคำขอเท่านั้น ระบบแสดงผลแบบปิดบังเสมอ
          และไม่เปิดเผยให้ผู้ใช้อื่นเห็น
        </p>

        {serverError ? (
          <p
            role="alert"
            className="rounded-xl bg-danger-bg px-4 py-3 text-sm font-medium text-danger-fg"
          >
            {serverError}
          </p>
        ) : null}

        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "กำลังสมัคร…" : "สมัครสมาชิก"}
          {isSubmitting ? null : <ArrowRight className="size-5" aria-hidden />}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-ink-muted">
        มีบัญชีอยู่แล้ว?{" "}
        <Link
          href="/login"
          className="font-semibold text-brand-600 underline underline-offset-4 hover:text-brand-400"
        >
          เข้าสู่ระบบ
        </Link>
      </p>
    </>
  );
}

/** แสดงปี พ.ศ. กำกับไว้ เพราะช่องวันที่ของเบราว์เซอร์เป็น ค.ศ. */
function buddhistHint(value: string): string | undefined {
  if (!value) return "ปฏิทินของเบราว์เซอร์แสดงเป็น ค.ศ.";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return undefined;
  return `ตรงกับ พ.ศ. ${d.getFullYear() + 543}`;
}

/** ยังไม่ redirect เพราะหน้าปลายทางของผู้ประกอบการยังไม่ถูกสร้าง
    เมื่อสร้างแล้วให้เปลี่ยนเป็น router.push(homeFor(user.role)) */
function DoneStep({ user }: { user: AuthUser }) {
  return (
    <div className="flex flex-col items-center py-6 text-center">
      <Mascot pose="success" size="md" className="w-40" />
      <h1 className="mt-6 text-2xl font-bold text-ink sm:text-3xl">สมัครสมาชิกสำเร็จ</h1>
      <p className="mt-2 text-ink-muted">
        ยินดีต้อนรับ {user.full_name}
        <br />
        เลขบัตรที่บันทึกไว้: <span className="font-mono">{user.national_id_masked}</span>
      </p>
      <p className="mt-6 rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-700">
        ขั้นตอนถัดไปคือประเมินประเภทที่พัก ซึ่งยังอยู่ระหว่างพัฒนา
      </p>
    </div>
  );
}
