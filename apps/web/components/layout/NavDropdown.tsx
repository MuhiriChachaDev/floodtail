"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { clsx } from "clsx";
import type { NavGroup } from "@/lib/nav";

const colorMap: Record<NavGroup["color"], string> = {
  data: "text-data",
  risk: "text-risk",
  finance: "text-finance",
  decide: "text-decide",
  accent: "text-accent",
};

const borderMap: Record<NavGroup["color"], string> = {
  data: "hover:border-data/40",
  risk: "hover:border-risk/40",
  finance: "hover:border-finance/40",
  decide: "hover:border-decide/40",
  accent: "hover:border-accent/40",
};

export function NavDropdown({ group }: { group: NavGroup }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const pathname = usePathname();
  const active = pathname.startsWith(`/${group.id}`);

  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={clsx(
          "inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-sm transition",
          active || open
            ? "bg-white/10 text-white"
            : "text-white/65 hover:bg-white/5 hover:text-white",
        )}
      >
        <span className={clsx("font-medium", colorMap[group.color])}>
          {group.label}
        </span>
        <ChevronDown
          className={clsx(
            "h-3.5 w-3.5 opacity-60 transition",
            open && "rotate-180",
          )}
        />
      </button>
      {open ? (
        <div className="absolute left-0 top-full z-50 mt-2 w-72 animate-slide-in rounded-2xl border border-white/10 bg-night-900/95 p-2 shadow-glass backdrop-blur-xl">
          {group.items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              className={clsx(
                "block rounded-xl border border-transparent px-3 py-2.5 transition",
                borderMap[group.color],
                pathname === item.href
                  ? "bg-white/10"
                  : "hover:bg-white/5",
              )}
            >
              <span className="block text-sm font-medium text-white">
                {item.label}
              </span>
              <span className="block text-xs text-white/45">{item.blurb}</span>
            </Link>
          ))}
        </div>
      ) : null}
    </div>
  );
}
