"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { FloodMap } from "@/components/map/FloodMap";
import { Notice } from "@/components/ui/Notice";

const CHECKS = [
  { label: "Completeness", value: "98%", ok: true },
  { label: "Duplicates", value: "0 found", ok: true },
  { label: "Invalid values", value: "2 fields", ok: false },
  { label: "Location gaps", value: "3 properties", ok: false },
  { label: "Geocoding", value: "597 / 600", ok: true },
  { label: "Consistency", value: "Good", ok: true },
];

export default function DataQualityPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Data · Quality & Location"
        title="Can we trust the data?"
        question="Where does FLOODTAIL believe these risks are, and how sure are we?"
      />

      <Notice>
        Icons on the map show building types. Dimmer markers need a second look —
        the location or details are less certain.
      </Notice>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {CHECKS.map((c) => (
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
          High confidence: coordinates match the address and sit inside Nairobi.
          Medium: placed by area name only. Low: missing or conflicting location —
          do not treat those properties as precisely sited until confirmed.
        </p>
      </div>
    </div>
  );
}
