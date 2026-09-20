"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { BadgeCheck, IdCard, KeyRound, Mail, Phone, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { Mascot } from "@/components/brand/Mascot";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { Button } from "@/components/ui/Button";
import { TextField } from "@/components/ui/TextField";
import { type Profile, changePassword, getProfile, updateProfile } from "@/lib/account";
import { ApiError } from "@/lib/api";
import { thaiDate } from "@/lib/applications";
import { PHONE_MAX_DIGITS, formatPhone, normalizePhone } from "@/lib/phone";
import type { UserRole } from "@/types/enums";

import { type PasswordForm, type ProfileForm, passwordSchema, profileSchema } from "./schema";

/**
 * M1 — บัญชีของฉัน: ดูข้อมูลที่ระบบเก็บไว้ แก้สิ่งที่แก้ได้ และเปลี่ยนรหัสผ่าน
 *
 * หน้าเดียวใช้ได้ทุกบทบาท เพราะข้อมูลบัญชีเป็นชุดเดียวกันหมด
 * สิ่งที่แก้ไม่ได้ (เลขบัตร บทบาท) แสดงไว้ด้วยพร้อมเหตุผล ไม่ซ่อนทิ้ง —
 * ผู้ใช้ควรเห็นว่าระบบเก็บอะไรของเขาไว้บ้าง ไม่ใช่เห็นเฉพาะช่องที่กรอกได้
 */
const ROLE_LABEL: Record<UserRole, string> = {
  operator: "ผู้ประกอบการ",
  officer: "เจ้าหน้าที่ท้องถิ่น",
  central: "หน่วยงานส่วนกลาง",
  super_admin: "ผู้ดูแลระบบ",
};

export function AccountView() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    getProfile()
      .then(setProfile)
      .catch((err) =>
        setLoadError(
          err instanceof ApiError ? err.message : "เปิดข้อมูลบัญชีไม่ได้ กรุณาลองใหม่อีกครั้ง",
        ),
      );
  }, []);

  if (loadError) {
    return (
      <main className="mx-auto w-full max-w-2xl px-4 py-16 text-center">
        <Mascot pose="support" size="md" className="mx-auto w-40" />
        <h1 className="mt-6 text-2xl font-bold text-ink">เปิดข้อมูลบัญชีไม่ได้</h1>
        <p role="alert" className="mt-2 text-ink-muted">
          {loadError}
        </p>
      </main>
    );
  }

  if (!profile) {
    return (
      <main className="mx-auto w-full max-w-3xl px-4 py-16 text-center text-ink-muted">
        กำลังโหลดข้อมูลบัญชี…
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-3xl space-y-6 px-4 py-8 sm:py-10">
      <PageHeader
        eyebrow="บัญชีของฉัน"
        title="ข้อมูลของคุณในระบบเป็นแบบนี้"
        description="แก้ชื่อ อีเมล และเบอร์โทรศัพท์ได้เอง อีเมลกับเบอร์โทรใช้เข้าสู่ระบบและรับการแจ้งเตือนผลพิจารณา"
      />

      <ProfileCard profile={profile} onSaved={setProfile} />
      <IdentityCard profile={profile} />
      <PasswordCard />
    </main>
  );
}

/* ------------------------------------------------- ข้อมูลที่แก้ได้ */

function ProfileCard({
  profile,
  onSaved,
}: {
  profile: Profile;
  onSaved: (p: Profile) => void;
}) {
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
    reset,
  } = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      first_name: profile.first_name,
      last_name: profile.last_name,
      email: profile.email ?? "",
      phone: profile.phone ?? "",
    },
  });

  async function save(values: ProfileForm) {
    setError(null);
    setSaved(false);
    try {
      const updated = await updateProfile(values);
      onSaved(updated);
      // reset ด้วยค่าที่เซิร์ฟเวอร์ตอบกลับ ไม่ใช่ค่าที่พิมพ์ เพราะเบอร์โทรถูก
      // ตัดขีดออกฝั่งเซิร์ฟเวอร์ ถ้าใช้ค่าที่พิมพ์ ช่องจะไม่ตรงกับที่บันทึกจริง
      reset({
        first_name: updated.first_name,
        last_name: updated.last_name,
        email: updated.email ?? "",
        phone: updated.phone ?? "",
      });
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "บันทึกไม่สำเร็จ กรุณาลองใหม่อีกครั้ง");
    }
  }

  return (
    <SectionCard
      icon={UserRound}
      title="ข้อมูลผู้ใช้"
      description="ชื่อที่แสดงในระบบ และช่องทางที่ใช้เข้าสู่ระบบกับรับการแจ้งเตือน"
    >
      <form onSubmit={handleSubmit(save)} className="space-y-4" noValidate>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label="ชื่อ"
            icon={UserRound}
            autoComplete="given-name"
            error={errors.first_name?.message}
            {...register("first_name")}
          />
          <TextField
            label="นามสกุล"
            autoComplete="family-name"
            error={errors.last_name?.message}
            {...register("last_name")}
          />
        </div>

        <TextField
          label="อีเมล"
          icon={Mail}
          type="email"
          autoComplete="email"
          hint="ใช้เข้าสู่ระบบ และเป็นที่อยู่ที่ระบบส่งอีเมลแจ้งผลการพิจารณาไปให้"
          error={errors.email?.message}
          {...register("email")}
        />

        {/* ไม่แทรกขีดระหว่างพิมพ์ เพราะเคอร์เซอร์จะกระโดดจนตัวเลขสลับ */}
        <Controller
          control={control}
          name="phone"
          render={({ field }) => (
            <TextField
              label="หมายเลขโทรศัพท์"
              icon={Phone}
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              maxLength={PHONE_MAX_DIGITS}
              placeholder="0812345678"
              hint={
                normalizePhone(field.value).length === PHONE_MAX_DIGITS
                  ? `ทวนอีกครั้ง: ${formatPhone(field.value)}`
                  : "ใช้เข้าสู่ระบบได้เหมือนอีเมล และเป็นเบอร์ที่เจ้าหน้าที่ใช้ติดต่อกลับ"
              }
              error={errors.phone?.message}
              value={field.value ?? ""}
              onChange={(e) =>
                field.onChange(normalizePhone(e.target.value).slice(0, PHONE_MAX_DIGITS))
              }
              onBlur={field.onBlur}
            />
          )}
        />

        {error && (
          <p role="alert" className="rounded-xl bg-danger-bg px-4 py-3 text-sm text-danger-fg">
            {error}
          </p>
        )}
        {saved && !isDirty && (
          <p role="status" className="rounded-xl bg-success-bg px-4 py-3 text-sm text-ink">
            บันทึกข้อมูลบัญชีแล้ว
          </p>
        )}

        <Button type="submit" disabled={isSubmitting || !isDirty}>
          {isSubmitting ? "กำลังบันทึก…" : "บันทึกข้อมูล"}
        </Button>
      </form>
    </SectionCard>
  );
}

/* ------------------------------------------------- ข้อมูลที่แก้ไม่ได้ */

function IdentityCard({ profile }: { profile: Profile }) {
  const rows: { label: string; value: string; note?: string }[] = [
    {
      label: "เลขประจำตัวประชาชน",
      value: profile.national_id_masked ?? "ไม่ได้บันทึกไว้",
      note: "แก้เองไม่ได้ เพราะหนึ่งเลขบัตรผูกได้กับบัญชีเดียว หากผูกผิด กรุณาติดต่อเจ้าหน้าที่",
    },
    {
      label: "บทบาทในระบบ",
      value: ROLE_LABEL[profile.role],
      note: "กำหนดโดยผู้ดูแลระบบ เป็นตัวบอกว่าเห็นและทำอะไรได้บ้าง",
    },
    { label: "เปิดบัญชีเมื่อ", value: thaiDate(profile.created_at) },
  ];

  if (profile.local_authorities.length > 0) {
    rows.splice(2, 0, {
      label: "เขตที่รับผิดชอบ",
      value: profile.local_authorities.join(" · "),
      note: "เห็นและดำเนินการได้เฉพาะคำขอในเขตนี้ คำขอของเขตอื่นระบบจะปฏิเสธและบันทึกไว้",
    });
  }

  return (
    <SectionCard
      icon={IdCard}
      title="ข้อมูลยืนยันตัวตน"
      description="ส่วนนี้แก้เองไม่ได้ แสดงไว้ให้เห็นว่าระบบเก็บอะไรของคุณไว้บ้าง"
      tone="info"
    >
      <dl className="divide-y divide-line">
        {rows.map((row) => (
          <div key={row.label} className="flex flex-wrap gap-x-6 gap-y-1 py-3 first:pt-0 last:pb-0">
            <dt className="w-44 shrink-0 text-sm text-ink-muted">{row.label}</dt>
            <dd className="min-w-0 flex-1">
              <p className="font-medium text-ink">{row.value}</p>
              {row.note && <p className="mt-0.5 text-sm text-ink-muted">{row.note}</p>}
            </dd>
          </div>
        ))}
      </dl>
    </SectionCard>
  );
}

/* ------------------------------------------------- เปลี่ยนรหัสผ่าน */

function PasswordCard() {
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  async function save(values: PasswordForm) {
    setError(null);
    setDone(false);
    try {
      await changePassword(values.current_password, values.new_password);
      reset();
      setDone(true);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "เปลี่ยนรหัสผ่านไม่สำเร็จ กรุณาลองใหม่อีกครั้ง",
      );
    }
  }

  return (
    <SectionCard
      icon={KeyRound}
      title="เปลี่ยนรหัสผ่าน"
      description="ต้องกรอกรหัสผ่านเดิมด้วยทุกครั้ง เพื่อยืนยันว่าเป็นเจ้าของบัญชีจริง"
    >
      <form onSubmit={handleSubmit(save)} className="space-y-4" noValidate>
        <TextField
          label="รหัสผ่านเดิม"
          icon={KeyRound}
          revealable
          autoComplete="current-password"
          error={errors.current_password?.message}
          {...register("current_password")}
        />
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            label="รหัสผ่านใหม่"
            revealable
            autoComplete="new-password"
            hint="อย่างน้อย 8 ตัวอักษร"
            error={errors.new_password?.message}
            {...register("new_password")}
          />
          <TextField
            label="รหัสผ่านใหม่อีกครั้ง"
            revealable
            autoComplete="new-password"
            error={errors.confirm_password?.message}
            {...register("confirm_password")}
          />
        </div>

        {error && (
          <p role="alert" className="rounded-xl bg-danger-bg px-4 py-3 text-sm text-danger-fg">
            {error}
          </p>
        )}
        {done && (
          <p
            role="status"
            className="flex items-center gap-2 rounded-xl bg-success-bg px-4 py-3 text-sm text-ink"
          >
            <BadgeCheck className="size-4 shrink-0" aria-hidden />
            เปลี่ยนรหัสผ่านแล้ว ครั้งต่อไปให้เข้าสู่ระบบด้วยรหัสใหม่
          </p>
        )}

        <Button type="submit" variant="outline" disabled={isSubmitting}>
          {isSubmitting ? "กำลังเปลี่ยน…" : "เปลี่ยนรหัสผ่าน"}
        </Button>
      </form>
    </SectionCard>
  );
}
