"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { FloodMap } from "@/components/map/FloodMap";
import { formatKes } from "@/lib/format";
import { DEMO } from "@/lib/demo";

export default function CapitalPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Finance · Capital & Portfolio"
        title="What does this mean for capital?"
        question="Relate flood risk on the book to capacity, concentration, and stress."
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Portfolio covered value"
          value={formatKes(DEMO.portfolio.valueCovered)}
          tone="data"
        />
        <StatCard
          label="Modelled yearly loss"
          value={formatKes(DEMO.risk.expectedYearlyLoss)}
          tone="risk"
        />
        <StatCard
          label="Illustrative capital need"
          value={formatKes(410_000_000)}
          tone="finance"
          hint="Demo only"
        />
        <StatCard label="Stress view" value="Elevated" tone="warn" />
      </div>

      <FloodMap mode="capital" title="Capital concentration map" showTimeline={false} />

      <div className="glass rounded-2xl p-5 text-sm text-white/65">
        Ask: if a severe Nairobi flood hits the densest areas, does Kenya Re still
        have room to write more business — or should capacity be held back?
      </div>
    </div>
  );
}
