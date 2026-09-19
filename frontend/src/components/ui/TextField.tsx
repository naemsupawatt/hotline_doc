"use client";

import { Eye, EyeOff, type LucideIcon } from "lucide-react";
import { useId, useState } from "react";

import { cn } from "@/lib/utils";

type Props = Omit<React.InputHTMLAttributes<HTMLInputElement>, "id"> & {
  label: string;
  icon?: LucideIcon;
  /** ข้อความผิดพลาดที่ผู้ใช้ทั่วไปเข้าใจ — NFR Usability */
  error?: string;
  /** แสดงปุ่มลูกตาเปิด/ปิดการมองเห็นรหัสผ่าน */
  revealable?: boolean;
};

export function TextField({
  label,
  icon: Icon,
  error,
  revealable,
  className,
  type = "text",
  ...props
}: Props) {
  const id = useId();
  const errorId = `${id}-error`;
  const [revealed, setRevealed] = useState(false);
  const inputType = revealable ? (revealed ? "text" : "password") : type;

  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block text-sm font-semibold text-ink">
        {label}
      </label>

      <div className="relative">
        {Icon ? (
          <Icon
            aria-hidden
            className="pointer-events-none absolute top-1/2 left-4 size-5 -translate-y-1/2 text-ink-muted"
          />
        ) : null}

        <input
          id={id}
          type={inputType}
          // ต้องมี aria-describedby ไม่งั้น screen reader อ่านข้อความผิดพลาดไม่เจอ
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          className={cn(
            "min-h-12 w-full rounded-xl border bg-canvas py-3 text-base text-ink",
            "placeholder:text-ink-muted/70",
            Icon ? "pl-12" : "pl-4",
            revealable ? "pr-12" : "pr-4",
            error ? "border-danger-fg" : "border-line",
            className,
          )}
          {...props}
        />

        {revealable ? (
          <button
            type="button"
            onClick={() => setRevealed((v) => !v)}
            // มาสคอต/ไอคอนต้องไม่สื่อความหมายลำพัง ปุ่มนี้จึงต้องมีชื่อกำกับเสมอ
            aria-label={revealed ? "ซ่อนรหัสผ่าน" : "แสดงรหัสผ่าน"}
            className="absolute top-1/2 right-3 -translate-y-1/2 rounded-lg p-1.5 text-ink-muted hover:text-brand-600"
          >
            {revealed ? <EyeOff className="size-5" /> : <Eye className="size-5" />}
          </button>
        ) : null}
      </div>

      {error ? (
        <p id={errorId} className="text-sm font-medium text-danger-fg">
          {error}
        </p>
      ) : null}
    </div>
  );
}
