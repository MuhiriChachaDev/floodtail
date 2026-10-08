"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { FlowSteps } from "@/components/ui/FlowSteps";
import { StatCard } from "@/components/ui/StatCard";
import { DataLabelsBanner } from "@/components/ui/DataLabelsBanner";
import { FloodMap } from "@/components/map/FloodMap";
import { TierLossBars } from "@/components/charts/TierLossBars";
import { formatKes } from "@/lib/format";
import { loadLastTestRun } from "@/lib/run-store";
import {
  heavyRainLosses,
  referenceLayer,
  resolveEpMetrics,
  type ResolvedEpMetrics,
} from "@/lib/ep-metrics";

export default function FinancePage() {
  const [ep, setEp] = useState<ResolvedEpMetrics | null>(null);
  const [load, setLoad] = useState(1.25);

  useEffect(() => {
    const reload = () => {
      const last = loadLastTestRun();
      const resolved = resolveEpMetrics(last?.metrics, {
        runId: last?.runId,
        locationLabel: last?.place || last?.portfolio.location_label,
      });
      setEp(resolved);
      if (resolved.pricing?.load_factor) {
        setLoad(resolved.pricing.load_factor);
      }
    };
    reload();
    const onStorage = (e: StorageEvent) => {
      if (e.key === "floodtail.lastTestRun.v1") reload();
    };
    const onRun = () => reload();
    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", onRun);
    window.addEventListener("floodtail:last-run", onRun);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", onRun);
      window.removeEventListener("floodtail:last-run", onRun);
    };
  }, []);

  const resolved =
    ep ??
    resolveEpMetrics(null, { locationLabel: "Demo portfolio" });
  const fin = resolved.financial;
  const layer = referenceLayer(fin);
  const isLive = resolved.source === "run";
  const hasTreaty = isLive && layer != null && fin != null;
  const aal = resolved.aalKes;
  const technical = useMemo(() => aal * load, [aal, load]);
  const enginePremium = resolved.pricing?.technical_premium_kes;
  const netAal = resolved.financial?.aal_net_kes;
  const heavy = heavyRainLosses(resolved.points);
  const band = resolved.capitalBand;

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="Finance"
        title="Treaty, pricing, and capital in one place"
        question="See how reinsurance responds, what price the risk supports, and what that means for capacity — from the same EP run."
      />

      <DataLabelsBanner
        labels={resolved.dataLabels}
        assumptionsVersion={resolved.assumptionsVersion}
        source={resolved.source}
        runId={resolved.runId}
      />

      {!isLive ? (
        <div className="rounded-2xl border border-amber-400/25 bg-amber-400/5 px-4 py-3 text-sm text-amber-100/80">
          Showing demo figures until you{" "}
          <Link href="/data/start" className="text-accent hover:underline">
            run a portfolio test
          </Link>
          . Live treaty, pricing, and capital use the same financial engine output.
        </div>
      ) : null}

      {/* Risk & Treaty */}
      <section id="treaty" className="space-y-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-finance">
            Risk &amp; Treaty
          </p>
          <h2 className="mt-1 font-display text-xl font-semibold text-white">
            How does reinsurance respond?
          </h2>
          <p className="mt-1 text-sm text-white/55">
            Follow modelled ground-up losses through a single-layer XL structure
            to the net (ceded) view.
          </p>
        </div>

        {hasTreaty && layer && fin ? (
          <>
            <FlowSteps
              accent="finance"
              steps={[
                { label: "Gross loss", detail: formatKes(layer.gross_kes) },
                {
                  label: "Retention",
                  detail: formatKes(fin.treaty.retention_kes),
                },
                {
                  label: "Attachment",
                  detail: formatKes(fin.treaty.attachment_kes),
                },
                { label: "Limit", detail: formatKes(fin.treaty.limit_kes) },
                { label: "Recovery", detail: formatKes(layer.recovery_kes) },
                { label: "Net Kenya Re", detail: formatKes(layer.net_kes) },
              ]}
            />

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                label={`Gross · ${layer.tier} (1-in-${layer.return_period})`}
                value={formatKes(layer.gross_kes)}
                tone="finance"
              />
              <StatCard
                label="XL recovery"
                value={formatKes(layer.recovery_kes)}
                tone="risk"
                hint={`Limit ${formatKes(fin.treaty.limit_kes)}`}
              />
              <StatCard
                label="Net Kenya Re view"
                value={formatKes(layer.net_kes)}
                tone="decide"
              />
              <StatCard
                label="Treaty"
                value={fin.treaty.name}
                hint={`${fin.treaty.status ?? "PROTOTYPE"} · single-layer XL`}
              />
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <StatCard
                label="Gross AAL"
                value={formatKes(fin.aal_gross_kes)}
                tone="risk"
              />
              <StatCard
                label="Ceded AAL"
                value={formatKes(fin.aal_ceded_kes)}
                tone="finance"
              />
              <StatCard
                label="Net AAL"
                value={formatKes(fin.aal_net_kes)}
                tone="decide"
              />
            </div>

            <div className="-mx-1 overflow-x-auto rounded-2xl border border-white/10 sm:mx-0">
              <table className="w-full min-w-[520px] text-left text-sm">
                <thead className="border-b border-white/10 text-xs text-white/50">
                  <tr>
                    <th className="px-3 py-3 font-medium sm:px-4">Tier</th>
                    <th className="px-3 py-3 font-medium sm:px-4">RP</th>
                    <th className="px-3 py-3 font-medium sm:px-4">Gross</th>
                    <th className="px-3 py-3 font-medium sm:px-4">Recovery</th>
                    <th className="px-3 py-3 font-medium sm:px-4">Net</th>
                  </tr>
                </thead>
                <tbody>
                  {fin.layered_by_tier.map((row) => (
                    <tr
                      key={row.tier}
                      className="border-b border-white/5 text-white/75"
                    >
                      <td className="px-4 py-2.5 capitalize">{row.tier}</td>
                      <td className="px-4 py-2.5">1-in-{row.return_period}</td>
                      <td className="px-4 py-2.5">
                        {formatKes(row.gross_kes)}
                      </td>
                      <td className="px-4 py-2.5">
                        {formatKes(row.recovery_kes)}
                      </td>
                      <td className="px-4 py-2.5 font-medium text-white">
                        {formatKes(row.net_kes)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="glass rounded-2xl p-5 text-sm text-white/65">
              <p className="font-medium text-white">How the XL works</p>
              <p className="mt-2">
                recovery = min(limit, max(0, gross − attachment)); net = gross −
                recovery. Attachment defaults to{" "}
                {formatKes(fin.treaty.attachment_kes)} and limit to{" "}
                {formatKes(fin.treaty.limit_kes)} ({fin.treaty.status}). This is
                a prototype single layer — not a multi-layer programme.
              </p>
              {(fin.treaty.notes ?? []).slice(0, 3).map((n) => (
                <p key={n} className="mt-1 text-xs text-white/40">
                  • {n}
                </p>
              ))}
            </div>
          </>
        ) : (
          <p className="text-sm text-white/50">
            Run a portfolio test to compute gross → recovery → net from the
            financial engine.
          </p>
        )}
      </section>

      {/* Pricing */}
      <section id="pricing" className="space-y-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-finance">
            Pricing
          </p>
          <h2 className="mt-1 font-display text-xl font-semibold text-white">
            What price is supported by the risk?
          </h2>
          <p className="mt-1 text-sm text-white/55">
            Combine expected loss (AAL from the live EP curve) and an approved
            load factor into a technical indication — not a final price.
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="glass space-y-4 rounded-2xl p-5">
            <h3 className="section-title text-base">Building blocks</h3>
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
      </section>

      {/* Capital & Portfolio */}
      <section id="capital" className="space-y-5">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-finance">
            Capital &amp; Portfolio
          </p>
          <h2 className="mt-1 font-display text-xl font-semibold text-white">
            What does this mean for capital?
          </h2>
          <p className="mt-1 text-sm text-white/55">
            Relate flood risk on the book to capacity, concentration, and stress
            — grounded in the EP curve.
          </p>
        </div>

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
          <FloodMap
            mode="capital"
            title="Capital concentration map"
            showTimeline={false}
          />
        </div>

        <div className="glass rounded-2xl p-5 text-sm text-white/65">
          Ask: if a severe flood hits the densest areas of{" "}
          {resolved.locationLabel} ({formatKes(heavy.severe ?? 0)} modelled),
          does Kenya Re still have room to write more business — or should
          capacity be held back toward the ceiling (
          {formatKes(band?.ceiling_kes ?? heavy.extreme ?? 0)})?
        </div>
      </section>
    </div>
  );
}
