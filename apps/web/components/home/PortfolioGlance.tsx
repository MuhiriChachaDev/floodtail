"use client";

import { AlertTriangle } from "lucide-react";
import { StatCard } from "@/components/ui/StatCard";
import { formatKes } from "@/lib/format";
import { heavyRainLosses } from "@/lib/ep-metrics";
import { useLivePortfolioView } from "@/lib/live-view";

export function PortfolioGlance() {
  const view = useLivePortfolioView();
  const heavy = heavyRainLosses(view.resolved.points);
  const watched = view.resolved.nHouses;

  return (
    <div className="glass rounded-2xl p-4 sm:p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="section-title text-base uppercase tracking-[0.12em]">
          Portfolio at a glance
        </h3>
        <span className="chip">{view.freshnessLabel}</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <StatCard
          label="Value covered"
          value={formatKes(view.resolved.totalTivKes)}
          hint={
            view.hasRun
              ? `Total insured value · ${view.place}`
              : "Total insured value across the demo book"
          }
          status={view.hasRun ? "From last run" : "Demo"}
          tone="data"
        />
        <StatCard
          label="Expected yearly loss"
          value={formatKes(view.resolved.aalKes)}
          hint="Average loss you might expect in a year"
          status={view.hasRun ? "Computed" : "Demo"}
          tone="risk"
        />
        <StatCard
          label="Loss in a very severe flood"
          value={formatKes(heavy.severe ?? 0)}
          hint="Modelled severe (≈1-in-100) portfolio loss"
          status={view.hasRun ? "Computed" : "Demo"}
          tone="finance"
        />
        <StatCard
          label="Properties in book"
          value={String(watched)}
          hint={view.hasRun ? view.place : "Demo set"}
          status={view.hasRun ? view.resolved.source : "Demo"}
          tone="warn"
          icon={<AlertTriangle className="h-4 w-4 text-amber-300" />}
        />
      </div>
      <p className="mt-4 text-xs text-white/40">
        {view.hasRun
          ? `Figures follow the last portfolio test for ${view.place}.`
          : "Demo figures until you upload a portfolio on Data → Start."}
      </p>
    </div>
  );
}
