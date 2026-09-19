import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

/**
 * ปุ่มมาตรฐานของระบบ — สีทั้งหมดมาจาก token ใน globals.css
 * ห้ามเขียนสีดิบในคอมโพเนนต์ (กฎข้อ 2 ของทีม)
 *
 * ความสูงขั้นต่ำ 48px เพราะ NFR Accessibility กำหนดว่าต้องกดได้จริงบนจอเล็ก
 */
const button = cva(
  "inline-flex w-full items-center justify-center gap-2 rounded-xl px-5 text-base font-semibold " +
    "transition-colors disabled:cursor-not-allowed disabled:opacity-60",
  {
    variants: {
      variant: {
        primary: "bg-brand-500 text-white hover:bg-brand-400",
        outline: "border-2 border-brand-500 bg-surface text-brand-600 hover:bg-brand-50",
        ghost: "text-ink-muted hover:bg-brand-50 hover:text-brand-700",
      },
      size: {
        md: "min-h-12 py-3",
        sm: "min-h-10 py-2 text-sm",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & VariantProps<typeof button>;

export function Button({ className, variant, size, ...props }: Props) {
  return <button className={cn(button({ variant, size }), className)} {...props} />;
}
