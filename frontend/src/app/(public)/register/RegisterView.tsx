"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, IdCard, Lock, Mail, Phone, User } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { AuthLayout } from "@/components/common/AuthLayout";
import { Mascot } from "@/components/brand/Mascot";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { ApiError } from "@/lib/api";
import { type AuthUser, homeFor, register as registerAccount } from "@/lib/auth";
import { PHONE_MAX_DIGITS, formatPhone, normalizePhone } from "@/lib/phone";
import { THAI_ID_DIGITS, formatThaiId, normalizeThaiId } from "@/lib/thaiId";
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
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    control,
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    // "onTouched" = ยังไม่เตือนระหว่างพิมพ์ครั้งแรก แต่พอเคยออกจากช่องแล้ว
    // จะตรวจใหม่ทุกครั้งที่พิมพ์ ข้อความเตือนจึงหายทันทีที่ผู้ใช้แก้ถูก
    //
    // ห้ามเปลี่ยนกลับเป็น "onBlur" — โหมดนั้นข้ามการตรวจตอน change เสมอ
    // (ดู skipValidation ของ react-hook-form) ทำให้ผู้ใช้แก้ถูกแล้วยังเห็น
    // ข้อความเดิมค้างอยู่จนกว่าจะคลิกออกจากช่องอีกรอบ
    mode: "onTouched",
  });

  async function onSubmit(values: RegisterForm) {
    setServerError(null);
    try {
      const created = await registerAccount({
        first_name: values.first_name,
        last_name: values.last_name,
        national_id: normalizeThaiId(values.national_id),
        phone: normalizePhone(values.phone),
        email: values.email,
        password: values.password,
      });

      // สมัครใหม่เป็นผู้ประกอบการเสมอ พาไปเริ่มประเมินที่พักต่อได้ทันที
      // ไม่ต้องผ่านหน้าจอ "สำเร็จ" ที่ไม่มีอะไรให้ทำต่อ
      onRegistered(created);
      router.push(homeFor(created.role));
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

        {/* ไม่แทรกขีดระหว่างพิมพ์ — ดู readback() ว่าทำไม */}
        <Controller
          control={control}
          name="national_id"
          defaultValue=""
          render={({ field }) => (
            <TextField
              label="เลขประจำตัวประชาชน"
              icon={IdCard}
              inputMode="numeric"
              maxLength={THAI_ID_DIGITS}
              placeholder="กรอกตัวเลข 13 หลัก"
              hint={readback(
                field.value,
                THAI_ID_DIGITS,
                formatThaiId,
                "ทวนกับหน้าบัตร",
                "กรอก 13 หลักตามหน้าบัตร ไม่ต้องใส่ขีด",
              )}
              error={errors.national_id?.message}
              value={field.value ?? ""}
              onChange={(e) =>
                field.onChange(normalizeThaiId(e.target.value).slice(0, THAI_ID_DIGITS))
              }
              onBlur={field.onBlur}
            />
          )}
        />

        <Controller
          control={control}
          name="phone"
          defaultValue=""
          render={({ field }) => (
            <TextField
              label="หมายเลขโทรศัพท์"
              icon={Phone}
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              maxLength={PHONE_MAX_DIGITS}
              placeholder="0812345678"
              hint={readback(
                field.value,
                PHONE_MAX_DIGITS,
                formatPhone,
                "เบอร์ที่เจ้าหน้าที่จะใช้ติดต่อกลับ",
                "ใช้เข้าสู่ระบบได้เหมือนอีเมล และเป็นเบอร์ที่เจ้าหน้าที่ใช้ติดต่อกลับ",
              )}
              error={errors.phone?.message}
              value={field.value ?? ""}
              onChange={(e) =>
                field.onChange(normalizePhone(e.target.value).slice(0, PHONE_MAX_DIGITS))
              }
              onBlur={field.onBlur}
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

/**
 * ข้อความใต้ช่องกรอก: พอกรอกครบก็แบ่งกลุ่มตัวเลขให้ทวนกับหน้าบัตรได้ง่าย
 *
 * เป็นการช่วยอ่านเท่านั้น ค่าที่ส่งไปบันทึกเป็นตัวเลขล้วนเสมอ ไม่มีขีด
 * (ดู core/thai_id.py และ core/phone.py ฝั่งเซิร์ฟเวอร์ที่ normalize ซ้ำอีกชั้น)
 *
 * ทำไมไม่ใส่ขีดให้ในช่องกรอกเลยระหว่างพิมพ์:
 * ช่องกรอกแบบ controlled ที่จัดรูปแบบไปด้วยจะทำให้ตัวเลขสลับตำแหน่ง
 * ทุกครั้งที่โปรแกรมแทรกขีดใหม่ เพราะ React คืนเคอร์เซอร์ไปที่ออฟเซ็ตเดิม
 * ซึ่งตอนนี้มีขีดมาแทรกอยู่ข้างหน้าแล้ว ตัวถัดไปจึงถูกพิมพ์ผิดตำแหน่ง
 * อาการที่เจอคือกรอกครบ 13 หลักแต่ระบบบอกว่าเลขบัตรไม่ถูกต้อง
 *
 * แก้ให้ถูกต้องต้องจัดการเคอร์เซอร์เอง ซึ่งไม่คุ้มกับเวลาที่มี
 * จึงให้ช่องกรอกรับตัวเลขล้วน แล้วย้ายการแสดงแบบมีขีดมาไว้บรรทัดนี้แทน
 */
function readback(
  value: string | undefined,
  digits: number,
  format: (v: string) => string,
  label: string,
  fallback: string,
): string {
  const v = value ?? "";
  return v.length === digits ? `${label}: ${format(v)}` : fallback;
}

/** จอคั่นสั้น ๆ ระหว่างรอ router.push ไปหน้าประเมินที่พัก

    ยังต้องมีอยู่ เพราะ router.push ไม่ได้เปลี่ยนหน้าทันที
    ถ้าไม่มีอะไรคั่น ผู้ใช้จะเห็นฟอร์มเปล่าวูบหนึ่งแล้วค่อยเด้ง */
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
        กำลังพาไปยังหน้าประเมินประเภทที่พัก…
      </p>
    </div>
  );
}
