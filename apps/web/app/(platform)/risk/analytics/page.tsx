"use client";

import { useEffect, useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { DataLabelsBanner } from "@/components/ui/DataLabelsBanner";
import { FloodMap } from "@/components/map/FloodMap";
import { EpCurveChart } from "@/components/charts/EpCurveChart";
import { DepthDamageChart } from "@/components/charts/DepthDamageChart";
import { TierLossBars } from "@/components/charts/TierLossBars";
import { EpTable } from "@/components/charts/EpTable";
import { HeavyRainCallout } from "@/components/charts/HeavyRainCallout";
import { formatKes } from "@/lib/format";
import { resolveDepthDamage, type ResolvedDepthDamage } from "@/lib/depth-damage";
import { loadLastTestRun } from "@/lib/run-store";
import {
  heavyRainLosses,
  resolveEpMetrics,
  type ResolvedEpMetrics,
} from "@/lib/ep-metrics";

export default function AnalyticsPage() {
  const [ep, setEp] = useState<ResolvedEpMetrics | null>(null);
  const [dd, setDd] = useState<ResolvedDepthDamage | null>(null);

  useEffect(() => {
    const last = loadLastTestRun();
    setEp(
      resolveEpMetrics(last?.metrics, {
        runId: last?.runId,
        locationLabel: last?.place || last?.portfolio.location_label,
      }),
    );
    setDd(resolveDepthDamage(last?.metrics));
  }, []);

  const resolved =
    ep ??
    resolveEpMetrics(null, { locationLabel: "Nairobi County (demo)" });
  const depthDamage = dd ?? resolveDepthDamage(null);
  const heavy = heavyRainLosses(resolved.points);
  const netAal = resolved.financial?.aal_net_kes;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Risk Modelling · Risk Analytics"
        title="What does the risk mean?"
        question="Move from a single loss figure to the exceedance probability (EP) pattern of possible losses across the book."
      />

      <DataLabelsBanner
        labels={resolved.dataLabels}
        assumptionsVersion={resolved.assumptionsVersion}
        source={resolved.source}
        runId={resolved.runId}
      />
      <p className="text-xs text-white/40">{resolved.locationLabel}</p>

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard
          label="Expected yearly loss (AAL)"
          value={formatKes(resolved.aalKes)}
          hint="Average year across EP tiers"
          tone="risk"
        />
        <StatCard
          label="If rains too much (severe)"
          value={formatKes(heavy.severe ?? 0)}
          hint="1-in-100 · EP curve"
          tone="finance"
        />
        <StatCard
          label="Extreme rainfall loss"
          value={formatKes(heavy.extreme ?? 0)}
          hint="1-in-250 · tail of the curve"
          tone="decide"
        />
      </div>

      <HeavyRainCallout
        severeKes={heavy.severe}
        extremeKes={heavy.extreme}
        locationLabel={resolved.locationLabel}
        source={resolved.source}
      />

      <EpCurveChart points={resolved.points} aalKes={resolved.aalKes} />

      <DepthDamageChart data={depthDamage} />

      <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
        <TierLossBars points={resolved.points} />
        <FloodMap mode="risk" title="Risk concentration" showTimeline={false} />
      </div>

      <EpTable points={resolved.points} aalKes={resolved.aalKes} />

      {netAal != null ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <StatCard
            label="Gross AAL"
            value={formatKes(resolved.aalKes)}
            tone="risk"
            hint="Before XL"
          />
          <StatCard
            label="Net AAL (after XL)"
            value={formatKes(netAal)}
            tone="decide"
            hint="See Finance → Treaty"
          />
        </div>
      ) : null}

      {resolved.capitalBand ? (
        <div className="grid gap-3 sm:grid-cols-3">
          <StatCard
            label="Capital floor"
            value={formatKes(resolved.capitalBand.floor_kes)}
            hint={resolved.capitalBand.floor_basis || "RP100"}
            tone="finance"
          />
          <StatCard
            label="Central (AAL)"
            value={formatKes(resolved.capitalBand.central_kes)}
            hint={resolved.capitalBand.central_basis || "AAL"}
            tone="risk"
          />
          <StatCard
            label="Capital ceiling"
            value={formatKes(resolved.capitalBand.ceiling_kes)}
            hint={resolved.capitalBand.ceiling_basis || "RP250"}
            tone="decide"
          />
        </div>
      ) : null}
    </div>
  );
}
