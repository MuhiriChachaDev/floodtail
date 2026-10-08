"use client";

import { useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { FlowSteps } from "@/components/ui/FlowSteps";
import { FloodMap } from "@/components/map/FloodMap";
import { StatCard } from "@/components/ui/StatCard";
import { PrototypeBadge } from "@/components/ui/PrototypeBadge";
import Link from "next/link";

export default function SimulationPage() {
  const [severity, setSeverity] = useState("Severe");
  const [region, setRegion] = useState("Eastern Nairobi");
  const [ran, setRan] = useState(false);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Risk Modelling · Event Simulation"
        title="What could happen?"
        question="Set up a possible flood event, then see which covered properties sit in its path."
      />

      <PrototypeBadge title="Illustrative event UX — not the discrete EP engine">
        FLOODTAIL&apos;s loss model uses five assumed return-period tiers, not a
        click-to-simulate catalogue. For live ground-up / net losses open{" "}
        <Link href="/risk/loss" className="text-accent hover:underline">
          Loss modelling
        </Link>{" "}
        after a portfolio test.
      </PrototypeBadge>

      <FlowSteps
        accent="risk"
        steps={[
          { label: "Event" },
          { label: "Hazard" },
          { label: "Portfolio overlap" },
          { label: "Affected assets" },
        ]}
      />

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="glass space-y-4 rounded-2xl p-5">
          <h2 className="section-title text-base">Event setup</h2>
          <label className="block text-xs text-white/55">
            Event type
            <select className="input-field mt-1.5">
              <option>Historical-style scenario</option>
              <option>What-if scenario</option>
              <option>Design flood (most severe tier)</option>
            </select>
          </label>
          <label className="block text-xs text-white/55">
            Region
            <select
              className="input-field mt-1.5"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
            >
              <option>Eastern Nairobi</option>
              <option>Western Nairobi</option>
              <option>All Nairobi County</option>
            </select>
          </label>
          <label className="block text-xs text-white/55">
            Severity
            <select
              className="input-field mt-1.5"
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
            >
              <option>Common</option>
              <option>Occasional</option>
              <option>Moderate</option>
              <option>Severe</option>
              <option>Extreme</option>
            </select>
          </label>
          <label className="block text-xs text-white/55">
            Rainfall intensity
            <input type="range" min={1} max={5} defaultValue={4} className="mt-2 w-full accent-risk" />
          </label>
          <button
            type="button"
            className="btn-primary w-full !bg-risk !text-night-950 !shadow-glow-teal"
            onClick={() => setRan(true)}
          >
            Run simulation
          </button>
          {ran ? (
            <p className="text-sm text-risk">
              Simulation ready for {region} · {severity}. Affected assets highlighted
              on the map.
            </p>
          ) : null}
        </div>
        <div className="space-y-4">
          <FloodMap mode="hazard" title="Event footprint" />
          {ran ? (
            <div className="grid gap-3 sm:grid-cols-3">
              <StatCard label="Properties hit" value="86" tone="risk" />
              <StatCard label="Share of book" value="14%" tone="risk" />
              <StatCard label="Run ID" value="SIM-1042" tone="neutral" hint="Traceable" />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
