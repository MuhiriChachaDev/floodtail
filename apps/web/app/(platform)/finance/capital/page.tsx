"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { DataLabelsBanner } from "@/components/ui/DataLabelsBanner";
import { FloodMap } from "@/components/map/FloodMap";
import { TierLossBars } from "@/components/charts/TierLossBars";
import { formatKes } from "@/lib/format";
import { loadLastTestRun } from "@/lib/run-store";
import {
  heavyRainLosses,
  resolveEpMetrics,
  type ResolvedEpMetrics,
} from "@/lib/ep-metrics";

export default function CapitalPage() {
  const [ep, setEp] = useState<ResolvedEpMetrics | null>(null);

  useEffect(() => {
    const last = loadLastTestRun();
    setEp(
      resolveEpMetrics(last?.metrics, {
        runId: last?.runId,
        locationLabel: last?.place || last?.portfolio.location_label,
      }),
    );
  }, []);

  const resolved =
    ep ??
    resolveEpMetrics(null, { locationLabel: "Nairobi County (demo)" });
  const heavy = heavyRainLosses(resolved.points);
  const band = resolved.capitalBand;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Finance · Capital & Portfolio"
        title="What does this mean for capital?"
        question="Relate flood risk on the book to capacity, concentration, and stress — grounded in the EP curve."
      />

      <DataLabelsBanner
        labels={resolved.dataLabels}
        assumptionsVersion={resolved.assumptionsVersion}
        source={resolved.source}
        runId={resolved.runId}
      />
      <Link href="/risk/analytics" className="text-xs text-accent hover:underline">
        EP analytics →
      </Link>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Portfolio covered value"
          value={formatKes(resolved.totalTivKes)}
          tone="data"
        />
        <StatCard
          label="Modelled yearly loss"
          value={formatKes(resolved.aalKes)}
          tone="risk"
          hint="AAL"
        />
        <StatCard
          label="Capital floor"
          value={formatKes(band?.floor_kes ?? heavy.severe ?? 0)}
          tone="finance"
          hint={band?.floor_basis || "RP100 severe"}
        />
        <StatCard
          label="Capital ceiling"
          value={formatKes(band?.ceiling_kes ?? heavy.extreme ?? 0)}
          tone="decide"
          hint={band?.ceiling_basis || "RP250 extreme"}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <TierLossBars
          points={resolved.points}
          title="EP-driven loss tiers"
          subtitle="Capital guidance uses severe (floor) and extreme (ceiling) points on this curve."
        />
        <FloodMap mode="capital" title="Capital concentration map" showTimeline={false} />
      </div>

      <div className="glass rounded-2xl p-5 text-sm text-white/65">
        Ask: if a severe Nairobi flood hits the densest areas (
        {formatKes(heavy.severe ?? 0)} modelled), does Kenya Re still have room
        to write more business — or should capacity be held back toward the
        ceiling ({formatKes(band?.ceiling_kes ?? heavy.extreme ?? 0)})?
      </div>
    </div>
  );
}
