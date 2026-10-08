"use client";

import type { EpDisplayPoint } from "@/lib/ep-metrics";
import { formatKes } from "@/lib/format";

type Props = {
  points: EpDisplayPoint[];
  title?: string;
  subtitle?: string;
};

export function TierLossBars({
  points,
  title = "Loss by flood rarity",
  subtitle = "Higher bars mean larger losses when floods are rarer and more severe.",
}: Props) {
  const max = Math.max(...points.map((p) => p.loss_kes), 1);

  return (
    <div className="glass rounded-2xl p-5">
      <h3 className="section-title mb-1 text-base">{title}</h3>
      <p className="mb-5 text-sm text-white/50">{subtitle}</p>
      <div className="flex h-56 items-end gap-3">
        {points.map((p) => {
          const pct = Math.max((p.loss_kes / max) * 100, 4);
          return (
            <div
              key={`${p.tier}-${p.return_period}`}
              className="flex flex-1 flex-col items-center gap-2"
            >
              <span className="text-[10px] text-white/45">
                {formatKes(p.loss_kes)}
              </span>
              <div
                className={`w-full rounded-t-lg transition ${
                  p.isHeavyRain
                    ? "bg-gradient-to-t from-finance/50 to-finance hover:to-accent"
                    : "bg-gradient-to-t from-risk/40 to-risk hover:to-accent"
                }`}
                style={{ height: `${pct}%` }}
                title={p.rarity}
              />
              <span className="text-center text-[11px] font-medium text-white/80">
                {p.label}
              </span>
              <span className="text-center text-[10px] text-white/40">
                1-in-{p.return_period}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
