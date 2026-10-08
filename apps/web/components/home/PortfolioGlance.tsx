"use client";

import { AlertTriangle } from "lucide-react";
import { StatCard } from "@/components/ui/StatCard";
import { DEMO } from "@/lib/demo";
import { formatKes } from "@/lib/format";

export function PortfolioGlance() {
  return (
    <div className="glass rounded-2xl p-4 sm:p-5">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="section-title text-base uppercase tracking-[0.12em]">
          Portfolio at a glance
        </h3>
        <span className="chip">{DEMO.freshness.portfolio}</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <StatCard
          label="Value covered"
          value={formatKes(DEMO.portfolio.valueCovered)}
          hint="Total insured value across the demo book"
          status="Computed"
          tone="data"
        />
        <StatCard
          label="Expected yearly loss"
          value={formatKes(DEMO.risk.expectedYearlyLoss)}
          hint="Average loss you might expect in a year"
          status="Computed"
          tone="risk"
        />
        <StatCard
          label="Loss in a very severe flood"
          value={formatKes(DEMO.risk.severeFloodLoss)}
          hint="Average loss in the worst rare events"
          status="Computed"
          tone="finance"
        />
        <StatCard
          label="Properties watched"
          value={String(DEMO.portfolio.activeWatched)}
          hint={`${DEMO.portfolio.properties} in full demo set`}
          status={`+${DEMO.portfolio.pendingReview} pending`}
          tone="warn"
          icon={<AlertTriangle className="h-4 w-4 text-amber-300" />}
        />
      </div>
      <p className="mt-4 text-xs text-white/40">
        Demo figures use a synthetic Nairobi portfolio. They are not real client
        results.
      </p>
    </div>
  );
}
