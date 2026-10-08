import Link from "next/link";
import { Shield } from "lucide-react";
import { CROSS_CUTTING } from "@/lib/nav";

export function Footer() {
  return (
    <footer className="mt-10 border-t border-white/10 bg-night-950/80">
      <div className="page-shell flex flex-col gap-3 py-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-white/40">
            <Shield className="h-3.5 w-3.5" />
            Cross-cutting
          </span>
          {CROSS_CUTTING.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-xs text-white/55 transition hover:text-accent"
            >
              {item.label}
            </Link>
          ))}
        </div>
        <p className="text-xs text-white/35">
          Measured risk. Greater resilience.
        </p>
      </div>
    </footer>
  );
}
