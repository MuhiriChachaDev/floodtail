"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { FloodMap } from "@/components/map/FloodMap";
import { formatKes } from "@/lib/format";
import { useLivePortfolioView } from "@/lib/live-view";
import { COUNTY_EXPOSURE } from "@/lib/demo";

export default function PortfolioPage() {
  const view = useLivePortfolioView();
  const concentration =
    view.concentration.length > 0 ? view.concentration : COUNTY_EXPOSURE;
  const pendingNotes = view.last?.portfolio.extra?.warnings?.length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Data · Portfolio & Exposure"
        title="What does Kenya Re have?"
        question="Where is covered value concentrated, and how much is exposed to flood?"
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Value covered"
          value={formatKes(view.resolved.totalTivKes)}
          tone="data"
          status={view.hasRun ? "From last run" : "Synthetic demo"}
        />
        <StatCard
          label="Active risks"
          value={String(view.resolved.nHouses)}
          tone="data"
        />
        <StatCard
          label="Focus area"
          value={view.place}
          tone="neutral"
        />
        <StatCard
          label="Pending checks"
          value={String(pendingNotes)}
          tone={pendingNotes > 0 ? "warn" : "data"}
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.3fr_1fr]">
        <FloodMap mode="portfolio" title="Portfolio map" showTimeline={false} />
        <div className="glass rounded-2xl p-5">
          <h3 className="section-title mb-4 text-base">
            {view.hasRun ? "Concentration by housing class" : "Concentration by area"}
          </h3>
          <ul className="space-y-3">
            {concentration.map((row) => (
              <li key={row.name}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="capitalize">{row.name}</span>
                  <span className="text-white/55">
                    {row.share}% · {formatKes(row.value)}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-data"
                    style={{ width: `${Math.min(100, row.share)}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-white/40">
            {view.hasRun
              ? `Live book for ${view.place} — map uses this upload’s coordinates.`
              : "Data quality = trust the data. Portfolio view = understand the book."}
          </p>
        </div>
      </div>
    </div>
  );
}
