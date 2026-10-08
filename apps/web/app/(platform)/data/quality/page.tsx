"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { FloodMap } from "@/components/map/FloodMap";
import { Notice } from "@/components/ui/Notice";
import { useLivePortfolioView } from "@/lib/live-view";

export default function DataQualityPage() {
  const view = useLivePortfolioView();
  const checks = view.hasRun
    ? view.qualityChecks
    : [
        { label: "Completeness", value: "Upload a portfolio", ok: false },
        { label: "Duplicates", value: "—", ok: true },
        { label: "Invalid values", value: "—", ok: true },
        { label: "Location gaps", value: "—", ok: true },
        { label: "Coordinates", value: "Waiting", ok: false },
        { label: "Consistency", value: "—", ok: true },
      ];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Data · Quality & Location"
        title="Can we trust the data?"
        question="Where does FLOODTAIL believe these risks are, and how sure are we?"
      />

      <Notice>
        {view.hasRun
          ? `Checking the last upload for ${view.place}. Map columns use that portfolio’s coordinates.`
          : "Icons on the map show building types. Upload a portfolio to drive the map for that place."}
      </Notice>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {checks.map((c) => (
          <StatCard
            key={c.label}
            label={c.label}
            value={c.value}
            status={c.ok ? "Pass" : "Needs attention"}
            tone={c.ok ? "data" : "warn"}
          />
        ))}
      </div>

      <FloodMap
        mode="quality"
        title="Location confidence map"
        showTimeline={false}
      />

      <div className="glass rounded-2xl p-5 text-sm text-white/65">
        <p className="font-medium text-white">What “confidence” means here</p>
        <p className="mt-2">
          High confidence: valid lat/lon on the uploaded rows
          {view.hasRun ? ` for ${view.place}` : ""}. Medium: placed by area name
          only. Low: missing or conflicting location — do not treat those
          properties as precisely sited until confirmed. Geography follows the
          portfolio bbox, not a fixed city.
        </p>
        {view.last?.portfolio.extra?.warnings?.length ? (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-amber-100/80">
            {view.last.portfolio.extra.warnings.slice(0, 5).map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}
