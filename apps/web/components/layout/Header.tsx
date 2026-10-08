"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BarChart3, ChevronDown, Home, LogOut, Menu, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { clsx } from "clsx";
import { KenyaReLogo } from "@/components/brand/KenyaReLogo";
import { useAuth, type Role } from "@/lib/auth";
import { NAV_GROUPS } from "@/lib/nav";
import { NavDropdown } from "./NavDropdown";

const ROLES: Role[] = [
  "Underwriter",
  "Risk Analyst",
  "Portfolio Manager",
  "Approver",
];

export function Header() {
  const { user, logout, setRole } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [roleOpen, setRoleOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const roleRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (roleRef.current && !roleRef.current.contains(e.target as Node)) {
        setRoleOpen(false);
      }
      if (userRef.current && !userRef.current.contains(e.target as Node)) {
        setUserOpen(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  useEffect(() => {
    if (!mobileOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [mobileOpen]);

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-night-950/80 backdrop-blur-xl">
      <div className="page-shell flex h-14 items-center justify-between gap-3 sm:h-16 sm:gap-4">
        <div className="flex min-w-0 items-center gap-3 sm:gap-6">
          <Link href="/home" className="flex min-w-0 shrink-0 items-center gap-2 sm:gap-3">
            <KenyaReLogo variant="white" heightClass="h-7 sm:h-9" priority />
            <span className="hidden border-l border-white/15 pl-3 leading-tight sm:block">
              <span className="block text-[10px] uppercase tracking-[0.16em] text-white/45">
                Flood Risk Intelligence
              </span>
            </span>
          </Link>

          <nav className="hidden items-center gap-1 lg:flex">
            <Link
              href="/home"
              className={clsx(
                "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition",
                pathname === "/home"
                  ? "bg-white/10 text-white"
                  : "text-white/65 hover:bg-white/5 hover:text-white",
              )}
            >
              <Home className="h-3.5 w-3.5" />
              Home
            </Link>
            <Link
              href="/about"
              className={clsx(
                "rounded-full px-3 py-1.5 text-sm transition",
                pathname === "/about"
                  ? "bg-white/10 text-white"
                  : "text-white/65 hover:bg-white/5 hover:text-white",
              )}
            >
              About
            </Link>
            {NAV_GROUPS.map((g) => (
              <NavDropdown key={g.id} group={g} />
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-1.5 sm:gap-3">
          <div className="relative hidden md:block" ref={roleRef}>
            <button
              type="button"
              onClick={() => setRoleOpen((v) => !v)}
              className="btn-ghost !py-1.5 !text-xs"
            >
              {user?.role ?? "Underwriter"}
              <ChevronDown className="h-3.5 w-3.5 opacity-60" />
            </button>
            {roleOpen ? (
              <div className="absolute right-0 top-full z-50 mt-2 w-48 animate-slide-in rounded-xl border border-white/10 bg-night-900 p-1 shadow-glass">
                {ROLES.map((role) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => {
                      setRole(role);
                      setRoleOpen(false);
                    }}
                    className={clsx(
                      "block w-full rounded-lg px-3 py-2 text-left text-sm",
                      user?.role === role
                        ? "bg-accent/15 text-accent"
                        : "text-white/80 hover:bg-white/5",
                    )}
                  >
                    {role}
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          <Link
            href="/data/portfolio"
            className="btn-ghost !hidden !py-1.5 sm:!inline-flex"
          >
            <BarChart3 className="h-3.5 w-3.5" />
            <span className="hidden xl:inline">Run / View Portfolio</span>
            <span className="xl:hidden">Portfolio</span>
          </Link>

          <div className="relative" ref={userRef}>
            <button
              type="button"
              onClick={() => setUserOpen((v) => !v)}
              className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 py-1 pl-1 pr-2 sm:pr-3 transition hover:bg-white/10"
              aria-label="Account menu"
            >
              <span className="grid h-8 w-8 place-items-center rounded-full bg-accent/20 text-xs font-semibold text-accent">
                {user?.initials ?? "JD"}
              </span>
              <span className="hidden text-left text-xs leading-tight sm:block">
                <span className="block font-medium text-white">
                  {user?.name ?? "Guest"}
                </span>
                <span className="block text-white/45">{user?.role}</span>
              </span>
            </button>
            {userOpen ? (
              <div className="absolute right-0 top-full z-50 mt-2 w-52 animate-slide-in rounded-xl border border-white/10 bg-night-900 p-1 shadow-glass">
                <p className="px-3 py-2 text-xs text-white/45">{user?.email}</p>
                <div className="border-t border-white/10 md:hidden">
                  <p className="px-3 py-1.5 text-[10px] uppercase tracking-wider text-white/35">
                    Role
                  </p>
                  {ROLES.map((role) => (
                    <button
                      key={role}
                      type="button"
                      onClick={() => {
                        setRole(role);
                        setUserOpen(false);
                      }}
                      className={clsx(
                        "block w-full rounded-lg px-3 py-2 text-left text-sm",
                        user?.role === role
                          ? "bg-accent/15 text-accent"
                          : "text-white/80 hover:bg-white/5",
                      )}
                    >
                      {role}
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => {
                    logout();
                    router.replace("/login");
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-rose-300 hover:bg-white/5"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  Sign out
                </button>
              </div>
            ) : null}
          </div>

          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-white/15 bg-white/5 text-white lg:hidden"
            aria-expanded={mobileOpen}
            aria-controls="mobile-nav"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            onClick={() => setMobileOpen((v) => !v)}
          >
            {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {mobileOpen ? (
        <div
          id="mobile-nav"
          className="max-h-[min(70vh,calc(100dvh-3.5rem))] overflow-y-auto border-t border-white/10 bg-night-950/95 lg:hidden"
        >
          <nav className="page-shell space-y-1 py-3">
            <Link
              href="/home"
              className={clsx(
                "flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm",
                pathname === "/home"
                  ? "bg-white/10 text-white"
                  : "text-white/75 hover:bg-white/5",
              )}
            >
              <Home className="h-4 w-4" />
              Home
            </Link>
            <Link
              href="/about"
              className={clsx(
                "block rounded-xl px-3 py-2.5 text-sm",
                pathname === "/about"
                  ? "bg-white/10 text-white"
                  : "text-white/75 hover:bg-white/5",
              )}
            >
              About
            </Link>
            <Link
              href="/data/portfolio"
              className="flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-white/75 hover:bg-white/5 sm:hidden"
            >
              <BarChart3 className="h-4 w-4" />
              Portfolio
            </Link>

            {NAV_GROUPS.map((g) => (
              <div key={g.id} className="pt-2">
                <p className="px-3 pb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/40">
                  {g.label}
                </p>
                {g.items.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx(
                      "block rounded-xl px-3 py-2.5",
                      pathname === item.href
                        ? "bg-white/10 text-white"
                        : "text-white/75 hover:bg-white/5",
                    )}
                  >
                    <span className="block text-sm font-medium">{item.label}</span>
                    <span className="block text-xs text-white/45">{item.blurb}</span>
                  </Link>
                ))}
              </div>
            ))}
          </nav>
        </div>
      ) : null}
    </header>
  );
}
