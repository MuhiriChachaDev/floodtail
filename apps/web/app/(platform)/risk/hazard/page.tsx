"use client";

import { useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { FloodMap } from "@/components/map/FloodMap";
import { PrototypeBadge } from "@/components/ui/PrototypeBadge";
import { clsx } from "clsx";

const LAYERS = [
  { id: "extent", label: "Flood extent" },
  { id: "depth", label: "Flood depth" },
  { id: "rain", label: "Rainfall" },
  { id: "assets", label: "Portfolio assets" },
] as const;

export default function HazardPage() {
  const [source, setSource] = useState<"observed" | "modelled">("modelled");
  const [layers, setLayers] = useState<string[]>(["extent", "depth", "assets"]);

  function toggle(id: string) {
    setLayers((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Risk Modelling · Flood Hazard"
        title="Where is the flood?"
        question="See physical flood conditions together with the properties Kenya Re covers."
      />

      <PrototypeBadge title="Map UX shell — not live hazard tiles from the API">
        Separate <strong className="text-white">observed</strong> from{" "}
        <strong className="text-white">modelled</strong> information. This screen
        is illustrative; portfolio loss and EP come from a test run on{" "}
        <strong className="text-white">Loss</strong> /{" "}
        <strong className="text-white">Analytics</strong>, not from this map.
      </PrototypeBadge>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setSource("observed")}
          className={clsx(
            "rounded-full px-4 py-2 text-sm",
            source === "observed"
              ? "bg-risk text-night-950"
              : "border border-white/15 text-white/70",
          )}
        >
          Observed
        </button>
        <button
          type="button"
          onClick={() => setSource("modelled")}
          className={clsx(
            "rounded-full px-4 py-2 text-sm",
            source === "modelled"
              ? "bg-risk text-night-950"
              : "border border-white/15 text-white/70",
          )}
        >
          Modelled
        </button>
        {LAYERS.map((l) => (
          <button
            key={l.id}
            type="button"
            onClick={() => toggle(l.id)}
            className={clsx(
              "rounded-full px-3 py-2 text-xs",
              layers.includes(l.id)
                ? "border border-risk/40 bg-risk-soft text-risk"
                : "border border-white/10 text-white/45",
            )}
          >
            {l.label}
          </button>
        ))}
      </div>

      <FloodMap mode="hazard" title={`${source === "observed" ? "Observed" : "Modelled"} flood workspace`} />

      <div className="grid gap-4 md:grid-cols-3">
        {[
          ["Rainfall", "Rising east of the CBD", "Last observation 42 min ago"],
          ["Rivers / drainage", "Proxy distance to streams", "Starter-kit terrain signal"],
          ["Satellite / terrain", "Depression & slope cues", "Not a full hydrology model"],
        ].map(([t, d, f]) => (
          <div key={t} className="glass rounded-2xl p-4">
            <p className="text-sm font-semibold text-risk">{t}</p>
            <p className="mt-1 text-sm text-white/70">{d}</p>
            <p className="mt-2 text-xs text-white/40">{f}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
