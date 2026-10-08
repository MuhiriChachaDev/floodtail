"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { FlowSteps } from "@/components/ui/FlowSteps";
import { StatCard } from "@/components/ui/StatCard";
import { DataLabelsBanner } from "@/components/ui/DataLabelsBanner";
import { FloodMap } from "@/components/map/FloodMap";
import { EpCurveChart } from "@/components/charts/EpCurveChart";
import { DepthDamageChart } from "@/components/charts/DepthDamageChart";
import { HeavyRainCallout } from "@/components/charts/HeavyRainCallout";
import { LOSS_CHAIN } from "@/lib/demo";
import { formatKes } from "@/lib/format";
import { resolveDepthDamage, type ResolvedDepthDamage } from "@/lib/depth-damage";
import { loadLastTestRun } from "@/lib/run-store";
import {
  heavyRainLosses,
  resolveEpMetrics,
  type ResolvedEpMetrics,
} from "@/lib/ep-metrics";

export default function LossPage() {
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
  const isLive = resolved.source === "run";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Risk Modelling · Loss Modelling"
        title="What could it cost?"
        question="Turn flood impact into money figures you can follow step by step — including predicted loss if rains were too much."
      />

      <DataLabelsBanner
        labels={resolved.dataLabels}
        assumptionsVersion={resolved.assumptionsVersion}
        source={resolved.source}
        runId={resolved.runId}
      />
      {isLive ? (
        <Link href="/risk/analytics" className="text-xs text-accent hover:underline">
          Full EP analytics →
        </Link>
      ) : null}

      <FlowSteps
        accent="risk"
        steps={LOSS_CHAIN.map((s) => ({
          label: s.step,
          detail: s.value,
        }))}
      />

      <HeavyRainCallout
        severeKes={heavy.severe}
        extremeKes={heavy.extreme}
        locationLabel={resolved.locationLabel}
        source={resolved.source}
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Expected yearly loss"
          value={formatKes(resolved.aalKes)}
          tone="risk"
          status="AAL from EP curve"
        />
        <StatCard
          label="If rains too much"
          value={formatKes(heavy.severe ?? 0)}
          tone="finance"
          hint="Severe · 1-in-100"
        />
        <StatCard
          label="Hazard model"
          value={resolved.hazardModel || "—"}
          hint="Pinned version"
        />
        <StatCard
          label="Vulnerability model"
          value={resolved.vulnModel || "—"}
          hint="Pinned version"
        />
      </div>

      <DepthDamageChart data={depthDamage} />

      <EpCurveChart
        points={resolved.points}
        aalKes={resolved.aalKes}
        title="Loss across the EP curve"
        subtitle="Each point is portfolio loss for a return period — extreme rainfall sits at the right of the curve."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <FloodMap mode="loss" title="Loss intensity map" showTimeline={false} />
        <div className="glass rounded-2xl p-5">
          <h3 className="section-title mb-3 text-base">Where this number came from</h3>
          <ol className="space-y-3 text-sm text-white/70">
            <li>1. Flood depth estimated per property from the hazard model.</li>
            <li>2. Damage share predicted from depth + building type.</li>
            <li>3. Loss = damage share × covered value.</li>
            <li>
              4. Tier losses roll up into the EP curve (common → extreme). Severe
              and extreme answer “if rains were too much.”
            </li>
            <li>5. Results tagged with run ID, model versions, and data labels.</li>
          </ol>
          <p className="mt-4 text-xs text-white/40">
            AI does not invent these figures. The numerical engine calculates them;
            AI only explains.
          </p>
        </div>
      </div>
    </div>
  );
}
