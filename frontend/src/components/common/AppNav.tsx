"use client";

import { LogOut, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useSyncExternalStore } from "react";

import { Logo } from "@/components/brand/Logo";
import { type AuthUser, logout } from "@/lib/auth";
import { cn } from "@/lib/utils";
import type { UserRole } from "@/types/enums";

/**
 * แถบนำทางด้านบน ใช้ร่วมทุกบทบาท
 *
 * เมนูมาจากบทบาทของผู้ใช้ที่ล็อกอินอยู่ ไม่ใช่รายการตายตัว เพราะผู้ใช้แต่ละบทบาท
 * ใช้คนละหน้ากันทั้งหมด การโชว์เมนูที่กดแล้วโดนปฏิเสธจะทำให้ผู้ใช้สับสน
 *
 * ใส่เฉพาะหน้าที่สร้างแล้วจริง ๆ — เมนูที่กดแล้วเจอ 404 แย่กว่าไม่มีเมนู
 */
const LINKS: Record<UserRole, { href: string; label: string }[]> = {
  operator: [
    { href: "/operator/wizard", label: "ประเมินที่พัก" },
    { href: "/operator/applications", label: "คำขอของฉัน" },
  ],
  officer: [{ href: "/officer/queue", label: "คิวคำขอ" }],
  central: [{ href: "/central/overview", label: "ภาพรวมทั้งจังหวัด" }],
  super_admin: [],
};

const ROLE_LABEL: Record<UserRole, string> = {
  operator: "ผู้ประกอบการ",
  officer: "เจ้าหน้าที่ท้องถิ่น",
  central: "หน่วยงานส่วนกลาง",
  super_admin: "ผู้ดูแลระบบ",
};

/** อ่านผู้ใช้จาก storage แบบที่ปลอดภัยกับ SSR และตามทันเมื่อล็อกอินในแท็บอื่น */
function subscribe(onChange: () => void) {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function useCurrentUser(): AuthUser | null {
  const raw = useSyncExternalStore(
    subscribe,
    () => window.localStorage.getItem("hotline.user") ?? window.sessionStorage.getItem("hotline.user"),
    () => null,
  );
  return raw ? (JSON.parse(raw) as AuthUser) : null;
}

export function AppNav() {
  const user = useCurrentUser();
  const pathname = usePathname();
  const router = useRouter();
  const [openMenu, setOpenMenu] = useState(false);

  const links = user ? LINKS[user.role] : [];

  function signOut() {
    logout();
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur print:hidden">
      <div className="mx-auto flex w-full max-w-6xl items-center gap-4 px-4 py-3 sm:px-6">
        <Link href={user ? links[0]?.href ?? "/login" : "/login"} className="shrink-0">
          <Logo className="h-9 w-auto" />
        </Link>

        <span className="hidden rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700 sm:inline">
          ต้นแบบ · ข้อมูลจำลอง
        </span>

        <nav className="ml-auto hidden items-center gap-1 md:flex" aria-label="เมนูหลัก">
          {links.map((link) => (
            <NavLink key={link.href} {...link} active={pathname.startsWith(link.href)} />
          ))}
        </nav>

        {user ? (
          <div className="ml-auto flex items-center gap-3 md:ml-0">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-ink">{user.full_name}</p>
              <p className="text-xs text-ink-muted">{ROLE_LABEL[user.role]}</p>
            </div>
            <button
              type="button"
              onClick={signOut}
              aria-label="ออกจากระบบ"
              className="inline-flex size-10 items-center justify-center rounded-xl text-ink-muted hover:bg-brand-50 hover:text-brand-700"
            >
              <LogOut className="size-5" aria-hidden />
            </button>
            {links.length > 0 && (
              <button
                type="button"
                onClick={() => setOpenMenu((v) => !v)}
                aria-expanded={openMenu}
                aria-label="เปิดเมนู"
                className="inline-flex size-10 items-center justify-center rounded-xl text-ink-muted hover:bg-brand-50 md:hidden"
              >
                {openMenu ? <X className="size-5" /> : <Menu className="size-5" />}
              </button>
            )}
          </div>
        ) : (
          <Link
            href="/login"
            className="ml-auto inline-flex min-h-10 items-center rounded-xl border-2 border-brand-500 px-4 font-semibold text-brand-600 hover:bg-brand-50"
          >
            เข้าสู่ระบบ
          </Link>
        )}
      </div>

      {openMenu && links.length > 0 && (
        <nav className="border-t border-line px-4 py-2 md:hidden" aria-label="เมนูหลัก">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              onClick={() => setOpenMenu(false)}
              className={cn(
                "block rounded-xl px-3 py-3 font-medium",
                pathname.startsWith(link.href)
                  ? "bg-brand-50 text-brand-700"
                  : "text-ink hover:bg-brand-50",
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}

function NavLink({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "rounded-xl px-3 py-2 text-sm font-semibold transition-colors",
        active ? "bg-brand-50 text-brand-700" : "text-ink-muted hover:bg-brand-50 hover:text-ink",
      )}
    >
      {label}
    </Link>
  );
}
