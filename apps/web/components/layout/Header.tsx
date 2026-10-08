"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BarChart3, ChevronDown, Home, LogOut } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { clsx } from "clsx";
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
  const roleRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

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

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-night-950/80 backdrop-blur-xl">
      <div className="page-shell flex h-16 items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-6">
          <Link href="/home" className="flex shrink-0 items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-gradient-to-br from-red-500 to-red-700 font-display text-sm font-bold text-white shadow-lg">
              K
            </span>
            <span className="hidden leading-tight sm:block">
              <span className="block font-display text-sm font-semibold tracking-wide text-white">
                KENYA RE
              </span>
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

        <div className="flex items-center gap-2 sm:gap-3">
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

          <Link href="/data/portfolio" className="btn-ghost !hidden !py-1.5 sm:!inline-flex">
            <BarChart3 className="h-3.5 w-3.5" />
            <span className="hidden xl:inline">Run / View Portfolio</span>
            <span className="xl:hidden">Portfolio</span>
          </Link>

          <div className="relative" ref={userRef}>
            <button
              type="button"
              onClick={() => setUserOpen((v) => !v)}
              className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 py-1 pl-1 pr-3 transition hover:bg-white/10"
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
        </div>
      </div>

      {/* Mobile nav strip */}
      <div className="page-shell flex gap-2 overflow-x-auto pb-3 lg:hidden">
        {NAV_GROUPS.map((g) => (
          <Link
            key={g.id}
            href={g.href}
            className="chip whitespace-nowrap"
          >
            {g.label}
          </Link>
        ))}
      </div>
    </header>
  );
}
