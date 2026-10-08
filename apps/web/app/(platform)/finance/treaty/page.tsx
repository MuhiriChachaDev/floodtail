"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { FlowSteps } from "@/components/ui/FlowSteps";
import { StatCard } from "@/components/ui/StatCard";
import { DataLabelsBanner } from "@/components/ui/DataLabelsBanner";
import { formatKes } from "@/lib/format";
import { loadLastTestRun } from "@/lib/run-store";
import {
  referenceLayer,
  resolveEpMetrics,
  type ResolvedEpMetrics,
} from "@/lib/ep-metrics";

export default function TreatyPage() {
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
  const fin = resolved.financial;
  const layer = referenceLayer(fin);
  const isLive = resolved.source === "run" && fin != null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Finance · Risk & Treaty"
        title="How does reinsurance respond?"
        question="Follow modelled ground-up losses through a single-layer XL structure to the net (ceded) view."
      />

      <DataLabelsBanner
        labels={resolved.dataLabels}
        assumptionsVersion={resolved.assumptionsVersion}
        source={resolved.source}
        runId={resolved.runId}
      />

      {!isLive ? (
        <div className="rounded-2xl border border-amber-400/25 bg-amber-400/5 px-4 py-3 text-sm text-amber-100/80">
          No live XL view yet.{" "}
          <Link href="/data/start" className="text-accent hover:underline">
            Run a portfolio test
          </Link>{" "}
          to compute gross → recovery → net from the financial engine.
        </div>
      ) : null}

      {isLive && layer && fin ? (
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

          <div className="overflow-x-auto rounded-2xl border border-white/10">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-white/10 text-xs text-white/50">
                <tr>
                  <th className="px-4 py-3 font-medium">Tier</th>
                  <th className="px-4 py-3 font-medium">RP</th>
                  <th className="px-4 py-3 font-medium">Gross</th>
                  <th className="px-4 py-3 font-medium">Recovery</th>
                  <th className="px-4 py-3 font-medium">Net</th>
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
                    <td className="px-4 py-2.5">{formatKes(row.gross_kes)}</td>
                    <td className="px-4 py-2.5">{formatKes(row.recovery_kes)}</td>
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
              {formatKes(fin.treaty.limit_kes)} ({fin.treaty.status}). This is a
              prototype single layer — not a multi-layer programme.
            </p>
            {(fin.treaty.notes ?? []).slice(0, 3).map((n) => (
              <p key={n} className="mt-1 text-xs text-white/40">
                • {n}
              </p>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
