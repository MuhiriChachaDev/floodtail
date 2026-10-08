import { clsx } from "clsx";
import type { ReactNode } from "react";

type Props = {
  label: string;
  value: string;
  hint?: string;
  status?: string;
  tone?: "data" | "risk" | "finance" | "decide" | "warn" | "neutral";
  icon?: ReactNode;
};

const tones: Record<NonNullable<Props["tone"]>, string> = {
  data: "border-data/30 shadow-glow-blue",
  risk: "border-risk/30 shadow-glow-teal",
  finance: "border-finance/30 shadow-glow-gold",
  decide: "border-decide/30 shadow-glow-purple",
  warn: "border-amber-400/40",
  neutral: "border-white/10",
};

export function StatCard({
  label,
  value,
  hint,
  status,
  tone = "neutral",
  icon,
}: Props) {
  return (
    <div className={clsx("glass rounded-2xl p-4", tones[tone])}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-white/55">
          {label}
        </p>
        {icon}
      </div>
      <p className="mt-2 break-words font-display text-xl font-semibold text-white sm:text-2xl">
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-white/50">{hint}</p> : null}
      {status ? (
        <p className="mt-3 text-[11px] font-semibold uppercase tracking-wider text-risk">
          {status}
        </p>
      ) : null}
    </div>
  );
}
