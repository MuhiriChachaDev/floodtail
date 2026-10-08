"use client";

import { useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { FloodMap } from "@/components/map/FloodMap";
import { clsx } from "clsx";
import { formatKes } from "@/lib/format";

const OPTIONS = [
  {
    id: "current",
    name: "Current position",
    exposure: 63_635_075_000,
    yearly: 128_870_000,
    capital: 410_000_000,
    note: "Keep the book as-is.",
  },
  {
    id: "a",
    name: "Option A — tighten Eastlands",
    exposure: 58_200_000_000,
    yearly: 102_000_000,
    capital: 360_000_000,
    note: "Reduce new writings in high-flood areas.",
  },
  {
    id: "b",
    name: "Option B — buy more cover",
    exposure: 63_635_075_000,
    yearly: 128_870_000,
    capital: 320_000_000,
    note: "Keep exposure; strengthen reinsurance recovery.",
  },
  {
    id: "c",
    name: "Option C — grow carefully",
    exposure: 70_100_000_000,
    yearly: 141_000_000,
    capital: 455_000_000,
    note: "Grow outside the densest flood pockets.",
  },
];

export default function DecisionLabPage() {
  const [selected, setSelected] = useState("a");
  const opt = OPTIONS.find((o) => o.id === selected)!;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Decisions · Decision Lab"
        title="Explore before you decide"
        question="Compare options side by side — exposure, loss, and capital impact — without committing yet."
      />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {OPTIONS.map((o) => (
          <button
            key={o.id}
            type="button"
            onClick={() => setSelected(o.id)}
            className={clsx(
              "rounded-2xl border p-4 text-left transition",
              selected === o.id
                ? "border-decide/50 bg-decide-soft shadow-glow-purple"
                : "border-white/10 bg-night-800/50 hover:border-white/25",
            )}
          >
            <p className="font-medium text-white">{o.name}</p>
            <p className="mt-2 text-xs text-white/55">{o.note}</p>
          </button>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="glass grid grid-cols-3 gap-3 rounded-2xl p-5">
          <div>
            <p className="text-xs text-white/45">Covered value</p>
            <p className="mt-1 font-display text-lg text-white">
              {formatKes(opt.exposure)}
            </p>
          </div>
          <div>
            <p className="text-xs text-white/45">Expected yearly loss</p>
            <p className="mt-1 font-display text-lg text-white">
              {formatKes(opt.yearly)}
            </p>
          </div>
          <div>
            <p className="text-xs text-white/45">Capital view</p>
            <p className="mt-1 font-display text-lg text-white">
              {formatKes(opt.capital)}
            </p>
          </div>
        </div>
        <FloodMap mode="decision" title="Option footprint" showTimeline={false} />
      </div>
    </div>
  );
}
