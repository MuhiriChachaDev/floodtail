"use client";

import { useId, useState } from "react";
import {
  HOUSING_CURVE_COLORS,
  housingCurveLabel,
  type ResolvedDepthDamage,
} from "@/lib/depth-damage";

type Props = {
  data: ResolvedDepthDamage;
  title?: string;
  subtitle?: string;
};

function pct(r: number): string {
  return `${(r * 100).toFixed(0)}%`;
}

/**
 * Depth–damage curves by housing class, with portfolio empirical points
 * (mean depth vs mean damage %) as flood severity tiers increase.
 */
export function DepthDamageChart({
  data,
  title = "Depth–damage curve",
  subtitle = "How the share of property value damaged rises as flood depth (and severity) increases.",
}: Props) {
  const gradId = useId().replace(/:/g, "");
  const [hoverCurve, setHoverCurve] = useState<string | null>(null);
  const [hoverPoint, setHoverPoint] = useState<number | null>(null);

  const curveEntries = Object.entries(data.curves);
  const maxDepth = Math.max(
    data.dMaxM,
    ...curveEntries.flatMap(([, pts]) => pts.map((p) => p.depth_m)),
    ...data.byTier.map((p) => p.mean_depth_m),
    1,
  );

  const w = 680;
  const h = 320;
  const pad = { top: 24, right: 20, bottom: 52, left: 52 };
  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;

  const xOf = (depth: number) => pad.left + (depth / maxDepth) * plotW;
  const yOf = (ratio: number) => pad.top + plotH - Math.min(1, Math.max(0, ratio)) * plotH;

  const activeTier =
    hoverPoint !== null ? data.byTier[hoverPoint] : null;

  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="section-title text-base">{title}</h3>
          <p className="mt-1 max-w-2xl text-sm text-white/50">{subtitle}</p>
        </div>
        {activeTier ? (
          <div className="rounded-xl border border-accent/30 bg-accent/10 px-3 py-2 text-right text-xs animate-fade-up">
            <p className="font-semibold capitalize text-accent">
              {activeTier.tier} · 1-in-{activeTier.return_period}
            </p>
            <p className="text-white/80">
              Depth {activeTier.mean_depth_m.toFixed(2)} m → damage{" "}
              {pct(activeTier.mean_damage_ratio)}
            </p>
            <p className="text-white/40">Portfolio mean from this run</p>
          </div>
        ) : (
          <p className="text-[11px] text-white/35">
            Lines = housing priors · dots = this portfolio
          </p>
        )}
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        {curveEntries.map(([housing]) => {
          const color = HOUSING_CURVE_COLORS[housing] || "#94a3b8";
          const on = hoverCurve === null || hoverCurve === housing;
          return (
            <button
              key={housing}
              type="button"
              onMouseEnter={() => setHoverCurve(housing)}
              onMouseLeave={() => setHoverCurve(null)}
              className="chip transition"
              style={{
                borderColor: on ? color : undefined,
                opacity: on ? 1 : 0.35,
              }}
            >
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: color }}
              />
              {housingCurveLabel(housing)}
            </button>
          );
        })}
        {data.byTier.length > 0 ? (
          <span className="chip border-white/25">
            <span className="inline-block h-2 w-2 rounded-full bg-white" />
            Portfolio by flood tier
          </span>
        ) : null}
      </div>

      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${w} ${h}`}
          className="mx-auto h-auto w-full max-w-full"
          role="img"
          aria-label="Depth damage curve"
        >
          <defs>
            <linearGradient id={`dd-fill-${gradId}`} x1="0" y1="1" x2="0" y2="0">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.04" />
              <stop offset="100%" stopColor="#22d3ee" stopOpacity="0.12" />
            </linearGradient>
          </defs>

          {/* Grid + axes labels */}
          {[0, 0.25, 0.5, 0.75, 1].map((t) => {
            const y = yOf(t);
            return (
              <g key={t}>
                <line
                  x1={pad.left}
                  x2={pad.left + plotW}
                  y1={y}
                  y2={y}
                  stroke="rgba(255,255,255,0.06)"
                />
                <text
                  x={pad.left - 8}
                  y={y + 3}
                  textAnchor="end"
                  className="fill-white/35"
                  fontSize={10}
                >
                  {pct(t)}
                </text>
              </g>
            );
          })}
          {[0, 1, 2, 3, 4].filter((d) => d <= maxDepth).map((d) => (
            <g key={d}>
              <line
                x1={xOf(d)}
                x2={xOf(d)}
                y1={pad.top}
                y2={pad.top + plotH}
                stroke="rgba(255,255,255,0.04)"
              />
              <text
                x={xOf(d)}
                y={h - 28}
                textAnchor="middle"
                className="fill-white/40"
                fontSize={10}
              >
                {d} m
              </text>
            </g>
          ))}

          <rect
            x={pad.left}
            y={pad.top}
            width={plotW}
            height={plotH}
            fill={`url(#dd-fill-${gradId})`}
          />

          {/* Prior curves */}
          {curveEntries.map(([housing, pts]) => {
            const color = HOUSING_CURVE_COLORS[housing] || "#94a3b8";
            const dim = hoverCurve !== null && hoverCurve !== housing;
            const path = pts
              .map(
                (p, i) =>
                  `${i === 0 ? "M" : "L"} ${xOf(p.depth_m)} ${yOf(p.damage_ratio)}`,
              )
              .join(" ");
            return (
              <path
                key={housing}
                d={path}
                fill="none"
                stroke={color}
                strokeWidth={hoverCurve === housing ? 3 : 2}
                strokeOpacity={dim ? 0.2 : 0.9}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            );
          })}

          {/* Empirical portfolio path + points */}
          {data.byTier.length > 1 ? (
            <path
              d={data.byTier
                .map(
                  (p, i) =>
                    `${i === 0 ? "M" : "L"} ${xOf(p.mean_depth_m)} ${yOf(p.mean_damage_ratio)}`,
                )
                .join(" ")}
              fill="none"
              stroke="#edf4ff"
              strokeWidth={2}
              strokeDasharray="5 4"
              strokeOpacity={0.85}
            />
          ) : null}

          {data.byTier.map((p, i) => {
            const cx = xOf(p.mean_depth_m);
            const cy = yOf(p.mean_damage_ratio);
            const heavy = p.return_period >= 100;
            return (
              <g key={`${p.tier}-${p.return_period}`}>
                <circle
                  cx={cx}
                  cy={cy}
                  r={hoverPoint === i ? 9 : 6}
                  fill={heavy ? "#f5b942" : "#ffffff"}
                  stroke="#03070f"
                  strokeWidth={2}
                  className="cursor-pointer"
                  onMouseEnter={() => setHoverPoint(i)}
                  onMouseLeave={() => setHoverPoint(null)}
                />
                <text
                  x={cx}
                  y={cy - 12}
                  textAnchor="middle"
                  className="fill-white/70"
                  fontSize={9}
                >
                  {p.tier.slice(0, 3)}
                </text>
              </g>
            );
          })}

          <text
            x={pad.left + plotW / 2}
            y={h - 10}
            textAnchor="middle"
            className="fill-white/30"
            fontSize={10}
          >
            Flood depth (metres) → severity increases
          </text>
          <text
            x={14}
            y={pad.top + plotH / 2}
            textAnchor="middle"
            transform={`rotate(-90 14 ${pad.top + plotH / 2})`}
            className="fill-white/30"
            fontSize={10}
          >
            Damage (% of value)
          </text>
        </svg>
      </div>

      {data.byTier.length > 0 ? (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[480px] text-left text-sm">
            <thead>
              <tr className="border-b border-white/10 text-[11px] uppercase tracking-wide text-white/40">
                <th className="py-2 pr-3 font-medium">Flood tier</th>
                <th className="py-2 pr-3 font-medium">Return period</th>
                <th className="py-2 pr-3 font-medium">Mean depth</th>
                <th className="py-2 pr-3 font-medium">Mean damage</th>
                <th className="py-2 font-medium">P90 damage</th>
              </tr>
            </thead>
            <tbody>
              {data.byTier.map((p) => (
                <tr
                  key={p.tier}
                  className={`border-b border-white/5 ${
                    p.return_period >= 100 ? "bg-finance/5" : ""
                  }`}
                >
                  <td className="py-2 pr-3 capitalize text-white/85">{p.tier}</td>
                  <td className="py-2 pr-3 text-white/60">1-in-{p.return_period}</td>
                  <td className="py-2 pr-3 text-white/70">
                    {p.mean_depth_m.toFixed(2)} m
                  </td>
                  <td className="py-2 pr-3 font-medium text-risk">
                    {pct(p.mean_damage_ratio)}
                  </td>
                  <td className="py-2 text-white/50">
                    {p.p90_damage_ratio != null
                      ? pct(p.p90_damage_ratio)
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {data.byHousing.length > 0 ? (
        <div className="mt-4">
          <p className="mb-2 text-xs uppercase tracking-wide text-white/40">
            By housing class (extreme tier)
          </p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {data.byHousing.map((h) => (
              <div
                key={h.housing_class}
                className="rounded-xl border border-white/10 bg-night-950/40 px-3 py-2"
              >
                <p className="text-xs text-white/55">
                  {housingCurveLabel(h.housing_class)}
                </p>
                <p className="mt-1 text-sm text-white/85">
                  {h.mean_depth_m.toFixed(2)} m → {pct(h.mean_damage_ratio)}
                </p>
                <p className="text-[10px] text-white/35">{h.n} properties</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <p className="mt-4 text-[11px] text-white/35">
        {data.source === "run"
          ? "Portfolio points are mean depth and mean damage ratio from this run’s scored locations."
          : "Showing benchmark prior curves with demo portfolio points — run a portfolio test for live data."}{" "}
        Prior curves are JRC/Huizinga-adapted (not Kenya claims-calibrated).
      </p>
    </div>
  );
}
