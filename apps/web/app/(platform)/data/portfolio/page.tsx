"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { FloodMap } from "@/components/map/FloodMap";
import { COUNTY_EXPOSURE, DEMO } from "@/lib/demo";
import { formatKes } from "@/lib/format";

export default function PortfolioPage() {
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
          value={formatKes(DEMO.portfolio.valueCovered)}
          tone="data"
          status="Synthetic demo"
        />
        <StatCard
          label="Active risks"
          value={String(DEMO.portfolio.properties)}
          tone="data"
        />
        <StatCard label="Focus area" value="Nairobi County" tone="neutral" />
        <StatCard
          label="Pending checks"
          value={String(DEMO.portfolio.pendingReview)}
          tone="warn"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.3fr_1fr]">
        <FloodMap mode="portfolio" title="Portfolio map" showTimeline={false} />
        <div className="glass rounded-2xl p-5">
          <h3 className="section-title mb-4 text-base">Concentration by area</h3>
          <ul className="space-y-3">
            {COUNTY_EXPOSURE.map((row) => (
              <li key={row.name}>
                <div className="mb-1 flex justify-between text-sm">
                  <span>{row.name}</span>
                  <span className="text-white/55">
                    {row.share}% · {formatKes(row.value)}
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-data"
                    style={{ width: `${row.share}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-xs text-white/40">
            Data quality = trust the data. Portfolio view = understand the book.
          </p>
        </div>
      </div>
    </div>
  );
}
