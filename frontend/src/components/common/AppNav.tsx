"use client";

import {
  ArrowUpRight,
  Building2,
  ChartNoAxesCombined,
  ClipboardList,
  FileCheck2,
  LogOut,
  Menu,
  Settings2,
  X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useSyncExternalStore } from "react";

import { Logo } from "@/components/brand/Logo";
import { Illustration } from "@/components/brand/Illustration";
import { type AuthUser, logout } from "@/lib/auth";
import { cn } from "@/lib/utils";
import type { UserRole } from "@/types/enums";

/**
 * แถบหัวและเมนูด้านข้าง ใช้ร่วมทุกบทบาท ยุบเป็นเมนูพับบนจอเล็ก
 *
 * เมนูมาจากบทบาทของผู้ใช้ที่ล็อกอินอยู่ ไม่ใช่รายการตายตัว เพราะผู้ใช้แต่ละบทบาท
 * ใช้คนละหน้ากันทั้งหมด การโชว์เมนูที่กดแล้วโดนปฏิเสธจะทำให้ผู้ใช้สับสน
 *
 * ใส่เฉพาะหน้าที่สร้างแล้วจริง ๆ — เมนูที่กดแล้วเจอ 404 แย่กว่าไม่มีเมนู
 */
const LINKS: Record<
  UserRole,
  { href: string; label: string; icon: typeof Building2 }[]
> = {
  operator: [
    { href: "/operator/wizard", label: "ประเมินที่พัก", icon: Building2 },
    { href: "/operator/applications", label: "คำขอของฉัน", icon: FileCheck2 },
  ],
  officer: [{ href: "/officer/queue", label: "คิวคำขอ", icon: ClipboardList }],
  central: [
    {
      href: "/central/overview",
      label: "ภาพรวมทั้งจังหวัด",
      icon: ChartNoAxesCombined,
    },
  ],
  super_admin: [
    { href: "/admin/settings", label: "ตั้งค่าเกณฑ์", icon: Settings2 },
  ],
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
    () =>
      window.localStorage.getItem("hotline.user") ??
      window.sessionStorage.getItem("hotline.user"),
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

  const active = (href: string) =>
    pathname.startsWith(href) ||
    (href === "/officer/queue" &&
      pathname.startsWith("/officer/applications/"));

  return (
    <>
      <a href="#workspace-content" className="skip-link">
        ข้ามไปเนื้อหาหลัก
      </a>
      <header className="sticky top-0 z-40 border-b border-line bg-surface/95 backdrop-blur print:hidden">
        <div className="flex h-20 items-center gap-3 px-4 sm:gap-5 sm:px-6 lg:px-8">
          <Logo
            href={user ? (links[0]?.href ?? "/login") : "/login"}
            variant="wordmark"
            className="w-40 sm:w-48"
          />
          <span className="hidden rounded-lg bg-brand-50 px-3 py-1.5 text-xs font-medium text-brand-700 sm:inline">
            ต้นแบบ · ข้อมูลจำลอง
          </span>
          <div className="ml-auto flex items-center gap-2 sm:gap-4">
            {user ? (
              <>
                <span
                  className="hidden size-10 items-center justify-center rounded-full bg-brand-100 font-bold text-brand-700 sm:flex"
                  aria-hidden
                >
                  {user.full_name.slice(0, 1)}
                </span>
                <div className="hidden max-w-48 sm:block">
                  <p className="truncate text-sm font-semibold">
                    {user.full_name}
                  </p>
                  <p className="text-xs text-ink-muted">
                    {ROLE_LABEL[user.role]}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={signOut}
                  aria-label="ออกจากระบบ"
                  title="ออกจากระบบ"
                  className="grid size-11 place-items-center rounded-xl text-ink-muted transition-colors hover:bg-brand-50 hover:text-brand-700"
                >
                  <LogOut className="size-5" aria-hidden />
                </button>
              </>
            ) : (
              <Link
                href="/login"
                className="rounded-xl border border-line px-4 py-2.5 text-sm font-semibold text-brand-700"
              >
                เข้าสู่ระบบ
              </Link>
            )}
            {links.length > 0 && (
              <button
                type="button"
                onClick={() => setOpenMenu((v) => !v)}
                aria-expanded={openMenu}
                aria-controls="mobile-navigation"
                aria-label={openMenu ? "ปิดเมนู" : "เปิดเมนู"}
                className="grid size-11 place-items-center rounded-xl bg-brand-50 text-brand-700 lg:hidden"
              >
                {openMenu ? (
                  <X className="size-5" />
                ) : (
                  <Menu className="size-5" />
                )}
              </button>
            )}
          </div>
        </div>
        {openMenu && links.length > 0 && (
          <nav
            id="mobile-navigation"
            className="space-y-1 border-t border-line p-3 lg:hidden"
            aria-label="เมนูหลักบนมือถือ"
          >
            {links.map((link) => (
              <NavLink
                key={link.href}
                {...link}
                active={active(link.href)}
                onNavigate={() => setOpenMenu(false)}
              />
            ))}
          </nav>
        )}
      </header>
      <aside className="app-sidebar fixed bottom-0 left-0 top-20 hidden w-56 flex-col overflow-y-auto border-r border-line px-4 py-7 lg:flex print:hidden">
        <p className="mb-4 px-3 text-xs font-semibold tracking-wide text-ink-muted">
          พื้นที่การทำงาน
        </p>
        <nav className="space-y-2" aria-label="เมนูหลัก">
          {links.map((link) => (
            <NavLink key={link.href} {...link} active={active(link.href)} />
          ))}
        </nav>
        <div className="mt-auto pt-10">
          <div className="overflow-hidden rounded-2xl border border-brand-100 bg-surface/70 pt-5 text-center">
            <p className="px-3 text-sm font-semibold leading-relaxed text-navy-700">
              ที่พักที่ดี
              <br />
              เริ่มต้นจากความพร้อม
            </p>
            <p className="mt-2 px-3 text-xs leading-relaxed text-ink-muted">
              เตรียมเอกสารอย่างมั่นใจ
              <br />
              เพื่อการท่องเที่ยวที่ยั่งยืน
            </p>
            <Illustration
              scene="coastal-community"
              sizes="192px"
              className="mt-3"
            />
          </div>
          <p className="mt-5 px-2 text-xs text-ink-muted">
            HoTLinE Doc · จังหวัดภูเก็ต
          </p>
        </div>
      </aside>
    </>
  );
}

function NavLink({
  href,
  label,
  icon: Icon,
  active,
  onNavigate,
}: {
  href: string;
  label: string;
  icon: typeof Building2;
  active: boolean;
  onNavigate?: () => void;
}) {
  return (
    <Link
      href={href}
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={cn(
        "flex min-h-12 items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium transition-colors",
        active
          ? "bg-brand-100/70 text-brand-700"
          : "text-ink-muted hover:bg-brand-50 hover:text-ink",
      )}
    >
      <Icon className="size-5 shrink-0" aria-hidden />
      {label}
      {active && (
        <ArrowUpRight className="ml-auto size-4 shrink-0" aria-hidden />
      )}
    </Link>
  );
}
