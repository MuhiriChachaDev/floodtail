"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { DataLabelsBanner } from "@/components/ui/DataLabelsBanner";
import { formatKes } from "@/lib/format";
import { loadLastTestRun } from "@/lib/run-store";
import {
  resolveEpMetrics,
  type ResolvedEpMetrics,
} from "@/lib/ep-metrics";

export default function PricingPage() {
  const [ep, setEp] = useState<ResolvedEpMetrics | null>(null);
  const [load, setLoad] = useState(1.25);

  useEffect(() => {
    const last = loadLastTestRun();
    const resolved = resolveEpMetrics(last?.metrics, {
      runId: last?.runId,
      locationLabel: last?.place || last?.portfolio.location_label,
    });
    setEp(resolved);
    if (resolved.pricing?.load_factor) {
      setLoad(resolved.pricing.load_factor);
    }
  }, []);

  const resolved =
    ep ??
    resolveEpMetrics(null, { locationLabel: "Nairobi County (demo)" });
  const isLive = resolved.source === "run";
  const aal = resolved.aalKes;
  const technical = useMemo(() => aal * load, [aal, load]);
  const enginePremium = resolved.pricing?.technical_premium_kes;
  const netAal = resolved.financial?.aal_net_kes;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Finance · Pricing"
        title="What price is supported by the risk?"
        question="Combine expected loss (AAL from the live EP curve) and an approved load factor into a technical indication — not a final price."
      />

      <DataLabelsBanner
        labels={resolved.dataLabels}
        assumptionsVersion={resolved.assumptionsVersion}
        source={resolved.source}
        runId={resolved.runId}
      />

      {!isLive ? (
        <div className="rounded-2xl border border-amber-400/25 bg-amber-400/5 px-4 py-3 text-sm text-amber-100/80">
          Showing demo AAL until you{" "}
          <Link href="/data/start" className="text-accent hover:underline">
            run a portfolio test
          </Link>
          . Live pricing uses the same AAL the financial engine produced.
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="glass space-y-4 rounded-2xl p-5">
          <h2 className="section-title text-base">Building blocks</h2>
          <ul className="space-y-2 text-sm text-white/70">
            <li>
              • Expected loss (gross AAL): {formatKes(aal)}
              {isLive ? " · from live EP" : " · demo"}
            </li>
            {netAal != null ? (
              <li>• Net AAL after XL: {formatKes(netAal)}</li>
            ) : null}
            <li>• Catastrophe risk load (adjustable below)</li>
            <li>
              • Formula: technical = AAL × load
              {resolved.pricing?.status
                ? ` · ${resolved.pricing.status}`
                : " · PROTOTYPE"}
            </li>
          </ul>
          <label className="block text-xs text-white/55">
            Risk load × {load.toFixed(2)}
            <input
              type="range"
              min={1}
              max={1.8}
              step={0.05}
              value={load}
              onChange={(e) => setLoad(Number(e.target.value))}
              className="mt-2 w-full accent-finance"
            />
          </label>
          <p className="text-xs text-white/40">
            FLOODTAIL supports pricing. It does not become the final pricing
            authority. A person must still approve.
          </p>
        </div>
        <div className="grid gap-3">
          <StatCard
            label="Technical price indication"
            value={formatKes(technical)}
            tone="finance"
            status="Needs human approval"
            hint="Not a binding quote"
          />
          {enginePremium != null && isLive ? (
            <StatCard
              label="Engine default (at run load)"
              value={formatKes(enginePremium)}
              tone="neutral"
              hint={`Load ×${resolved.pricing?.load_factor ?? "—"} frozen at run time`}
            />
          ) : null}
          <StatCard
            label="Compared to expected loss"
            value={`+${Math.round((load - 1) * 100)}% load`}
            tone="neutral"
          />
        </div>
      </div>
    </div>
  );
}
