"use client";

import type { EpDisplayPoint } from "@/lib/ep-metrics";
import { formatAepPct } from "@/lib/ep-metrics";
import { formatKes } from "@/lib/format";

type Props = {
  points: EpDisplayPoint[];
  aalKes?: number;
  title?: string;
};

export function EpTable({
  points,
  aalKes,
  title = "EP curve table",
}: Props) {
  return (
    <div className="glass overflow-hidden rounded-2xl">
      <div className="border-b border-white/10 px-5 py-4">
        <h3 className="section-title text-base">{title}</h3>
        <p className="mt-1 text-sm text-white/50">
          Deterministic tier losses from the numerical engine — not AI estimates.
        </p>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-left text-sm">
          <thead>
            <tr className="border-b border-white/10 text-[11px] uppercase tracking-wide text-white/40">
              <th className="px-5 py-3 font-medium">Tier</th>
              <th className="px-3 py-3 font-medium">Return period</th>
              <th className="px-3 py-3 font-medium">AEP</th>
              <th className="px-3 py-3 font-medium">Loss</th>
              <th className="px-5 py-3 font-medium">Mean damage</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr
                key={`${p.tier}-${p.return_period}`}
                className={`border-b border-white/5 ${
                  p.isHeavyRain ? "bg-finance/5" : ""
                }`}
              >
                <td className="px-5 py-3">
                  <span className="font-medium text-white/90">{p.label}</span>
                  {p.isHeavyRain ? (
                    <span className="ml-2 text-[10px] uppercase tracking-wide text-finance">
                      Heavy rain
                    </span>
                  ) : null}
                </td>
                <td className="px-3 py-3 text-white/70">1-in-{p.return_period}</td>
                <td className="px-3 py-3 text-white/70">{formatAepPct(p.aep)}</td>
                <td className="px-3 py-3 font-medium text-risk">
                  {formatKes(p.loss_kes, false)}
                </td>
                <td className="px-5 py-3 text-white/55">
                  {p.mean_damage_ratio != null
                    ? `${(p.mean_damage_ratio * 100).toFixed(1)}%`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
          {aalKes != null && aalKes > 0 ? (
            <tfoot>
              <tr className="bg-white/[0.03]">
                <td className="px-5 py-3 font-medium text-white/80" colSpan={3}>
                  Average annual loss (AAL)
                </td>
                <td className="px-3 py-3 font-semibold text-finance">
                  {formatKes(aalKes, false)}
                </td>
                <td className="px-5 py-3 text-white/40">Σ AEP × loss</td>
              </tr>
            </tfoot>
          ) : null}
        </table>
      </div>
    </div>
  );
}
