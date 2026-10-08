"use client";

import Link from "next/link";
import { formatKes } from "@/lib/format";

type Props = {
  severeKes: number | null;
  extremeKes: number | null;
  locationLabel?: string;
  source?: "run" | "demo";
};

/**
 * Plain-language callout: predicted portfolio loss if rains are severe / extreme.
 */
export function HeavyRainCallout({
  severeKes,
  extremeKes,
  locationLabel = "this portfolio",
  source = "run",
}: Props) {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-finance/35 bg-gradient-to-br from-finance/15 via-night-800/80 to-night-900 p-5 shadow-glow-gold animate-fade-up">
      <div
        className="pointer-events-none absolute -right-8 -top-10 h-40 w-40 rounded-full bg-finance/20 blur-3xl"
        aria-hidden
      />
      <p className="text-xs font-semibold uppercase tracking-wider text-finance">
        If rains were too much
      </p>
      <h3 className="mt-2 font-display text-xl font-semibold text-white sm:text-2xl">
        Predicted value loss under heavy rainfall
      </h3>
      <p className="mt-2 max-w-2xl text-sm text-white/60">
        For {locationLabel}, the engine maps flood rarity to portfolio loss.
        Severe (1-in-100) and extreme (1-in-250) points on the EP curve answer:
        what could it cost if rains overwhelm the book?
      </p>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-night-950/50 p-4">
          <p className="text-[11px] uppercase tracking-wide text-white/45">
            Severe flood · 1-in-100
          </p>
          <p className="mt-1 font-display text-2xl font-semibold text-finance">
            {severeKes != null ? formatKes(severeKes) : "—"}
          </p>
          <p className="mt-1 text-xs text-white/40">
            ~1% chance of exceeding this loss in a year
          </p>
        </div>
        <div className="rounded-xl border border-white/10 bg-night-950/50 p-4">
          <p className="text-[11px] uppercase tracking-wide text-white/45">
            Extreme flood · 1-in-250
          </p>
          <p className="mt-1 font-display text-2xl font-semibold text-decide">
            {extremeKes != null ? formatKes(extremeKes) : "—"}
          </p>
          <p className="mt-1 text-xs text-white/40">
            Tail of the EP curve — very rare rainfall
          </p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-white/45">
        <span>
          Source: {source === "run" ? "latest test run metrics" : "demo figures"}
        </span>
        <Link href="/finance#capital" className="text-accent hover:underline">
          Capital view →
        </Link>
      </div>
    </div>
  );
}
