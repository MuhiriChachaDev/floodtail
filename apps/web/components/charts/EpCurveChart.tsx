"use client";

import { useId, useState } from "react";
import type { EpDisplayPoint } from "@/lib/ep-metrics";
import { formatAepPct } from "@/lib/ep-metrics";
import { formatKes } from "@/lib/format";

type Props = {
  points: EpDisplayPoint[];
  aalKes?: number;
  title?: string;
  subtitle?: string;
};

/**
 * Classic EP curve: loss (Y) vs exceedance probability (X, high→low).
 * SVG — no chart library required for five discrete CAT tiers.
 */
export function EpCurveChart({
  points,
  aalKes,
  title = "Exceedance probability (EP) curve",
  subtitle = "Portfolio loss that is expected to be exceeded at each annual probability.",
}: Props) {
  const gradId = useId().replace(/:/g, "");
  const [hover, setHover] = useState<number | null>(null);

  const sorted = [...points].sort((a, b) => b.aep - a.aep);
  if (sorted.length === 0) {
    return (
      <div className="glass rounded-2xl p-5 text-sm text-white/50">
        No EP curve points available. Run a portfolio test first.
      </div>
    );
  }

  const w = 640;
  const h = 280;
  const pad = { top: 28, right: 24, bottom: 48, left: 64 };
  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;

  const maxLoss = Math.max(...sorted.map((p) => p.loss_kes), aalKes ?? 0, 1);
  const maxAep = Math.max(...sorted.map((p) => p.aep), 0.001);
  const minAep = Math.min(...sorted.map((p) => p.aep), maxAep);

  const xOf = (aep: number) => {
    // Linear in log(AEP) so rare events spread out
    const logMax = Math.log10(maxAep);
    const logMin = Math.log10(Math.max(minAep, 1e-6));
    const t = (Math.log10(Math.max(aep, 1e-6)) - logMax) / (logMin - logMax || 1);
    return pad.left + t * plotW;
  };
  const yOf = (loss: number) =>
    pad.top + plotH - (loss / maxLoss) * plotH;

  const pathD = sorted
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xOf(p.aep)} ${yOf(p.loss_kes)}`)
    .join(" ");

  const areaD = `${pathD} L ${xOf(sorted[sorted.length - 1].aep)} ${pad.top + plotH} L ${xOf(sorted[0].aep)} ${pad.top + plotH} Z`;

  const active = hover !== null ? sorted[hover] : null;
  const aalY = aalKes != null && aalKes > 0 ? yOf(aalKes) : null;

  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="section-title text-base">{title}</h3>
          <p className="mt-1 text-sm text-white/50">{subtitle}</p>
        </div>
        {active ? (
          <div className="rounded-xl border border-accent/30 bg-accent/10 px-3 py-2 text-right text-xs animate-fade-up">
            <p className="font-semibold text-accent">{active.label}</p>
            <p className="text-white/80">{formatKes(active.loss_kes)}</p>
            <p className="text-white/45">
              AEP {formatAepPct(active.aep)} · 1-in-{active.return_period}
            </p>
          </div>
        ) : (
          <p className="text-[11px] text-white/35">Hover a point for detail</p>
        )}
      </div>

      <div className="w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${w} ${h}`}
          className="mx-auto h-auto w-full max-w-full"
          role="img"
          aria-label="Exceedance probability curve"
        >
          <defs>
            <linearGradient id={`ep-fill-${gradId}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#2dd4bf" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#2dd4bf" stopOpacity="0.02" />
            </linearGradient>
          </defs>

          {/* Grid */}
          {[0.25, 0.5, 0.75, 1].map((t) => {
            const y = pad.top + plotH * (1 - t);
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
                  {formatKes(maxLoss * t)}
                </text>
              </g>
            );
          })}

          {/* AAL reference */}
          {aalY != null ? (
            <g>
              <line
                x1={pad.left}
                x2={pad.left + plotW}
                y1={aalY}
                y2={aalY}
                stroke="#f5b942"
                strokeDasharray="5 4"
                strokeOpacity={0.7}
              />
              <text
                x={pad.left + plotW - 4}
                y={aalY - 6}
                textAnchor="end"
                className="fill-finance"
                fontSize={10}
              >
                AAL {formatKes(aalKes!)}
              </text>
            </g>
          ) : null}

          <path d={areaD} fill={`url(#ep-fill-${gradId})`} />
          <path
            d={pathD}
            fill="none"
            stroke="#2dd4bf"
            strokeWidth={2.5}
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {sorted.map((p, i) => {
            const cx = xOf(p.aep);
            const cy = yOf(p.loss_kes);
            const heavy = p.isHeavyRain;
            return (
              <g key={`${p.return_period}-${i}`}>
                <circle
                  cx={cx}
                  cy={cy}
                  r={hover === i ? 8 : 5.5}
                  fill={heavy ? "#f5b942" : "#22d3ee"}
                  stroke="#03070f"
                  strokeWidth={2}
                  className="cursor-pointer transition-all"
                  onMouseEnter={() => setHover(i)}
                  onMouseLeave={() => setHover(null)}
                />
                <text
                  x={cx}
                  y={h - 18}
                  textAnchor="middle"
                  className="fill-white/50"
                  fontSize={10}
                >
                  {formatAepPct(p.aep)}
                </text>
                <text
                  x={cx}
                  y={h - 6}
                  textAnchor="middle"
                  className="fill-white/30"
                  fontSize={9}
                >
                  1/{p.return_period}
                </text>
              </g>
            );
          })}

          <text
            x={pad.left + plotW / 2}
            y={h - 2}
            textAnchor="middle"
            className="fill-white/25"
            fontSize={9}
          >
            Annual exceedance probability → rarer
          </text>
          <text
            x={14}
            y={pad.top + plotH / 2}
            textAnchor="middle"
            transform={`rotate(-90 14 ${pad.top + plotH / 2})`}
            className="fill-white/25"
            fontSize={9}
          >
            Loss (KES)
          </text>
        </svg>
      </div>
    </div>
  );
}
