"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { FloodMap } from "@/components/map/FloodMap";
import { DEMO, EP_CURVE } from "@/lib/demo";
import { formatKes } from "@/lib/format";

export default function AnalyticsPage() {
  const max = Math.max(...EP_CURVE.map((p) => p.loss));

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Risk Modelling · Risk Analytics"
        title="What does the risk mean?"
        question="Move from a single loss figure to the pattern of possible losses across the book."
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard
          label="Expected yearly loss"
          value={formatKes(DEMO.risk.expectedYearlyLoss)}
          hint="Average year"
          tone="risk"
        />
        <StatCard
          label="Rare severe flood"
          value={formatKes(DEMO.risk.severeFloodLoss)}
          hint="Very bad year territory"
          tone="finance"
        />
        <StatCard
          label="Very rare extreme flood"
          value={formatKes(DEMO.risk.rareFloodLoss)}
          hint="Tail of the curve"
          tone="decide"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
        <div className="glass rounded-2xl p-5">
          <h3 className="section-title mb-1 text-base">Loss by flood rarity</h3>
          <p className="mb-5 text-sm text-white/50">
            Higher bars mean larger losses when floods are rarer and more severe.
          </p>
          <div className="flex h-56 items-end gap-3">
            {EP_CURVE.map((p) => (
              <div key={p.label} className="flex flex-1 flex-col items-center gap-2">
                <span className="text-[10px] text-white/45">{formatKes(p.loss)}</span>
                <div
                  className="w-full rounded-t-lg bg-gradient-to-t from-risk/40 to-risk transition hover:to-accent"
                  style={{ height: `${(p.loss / max) * 100}%` }}
                  title={p.rarity}
                />
                <span className="text-center text-[11px] font-medium text-white/80">
                  {p.label}
                </span>
                <span className="text-center text-[10px] text-white/40">{p.rarity}</span>
              </div>
            ))}
          </div>
        </div>
        <FloodMap mode="risk" title="Risk concentration" showTimeline={false} />
      </div>
    </div>
  );
}
