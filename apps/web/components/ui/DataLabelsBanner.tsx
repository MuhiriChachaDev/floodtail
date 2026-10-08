import Link from "next/link";
import type { DataLabels } from "@/lib/api";

type Props = {
  labels?: DataLabels | null;
  assumptionsVersion?: string | null;
  source: "run" | "demo";
  runId?: string;
  className?: string;
};

function flag(label: string, on: boolean | undefined) {
  if (!on) return null;
  return (
    <span className="rounded-md border border-amber-400/25 bg-amber-400/10 px-2 py-0.5 text-[11px] text-amber-100/90">
      {label}
    </span>
  );
}

/**
 * Honesty strip: synthetic exposure, proxy hazard, assumed RPs, assumptions version.
 * Always shown so demo numbers are never mistaken for observations.
 */
export function DataLabelsBanner({
  labels,
  assumptionsVersion,
  source,
  runId,
  className = "",
}: Props) {
  const notes = labels?.notes?.filter(Boolean) ?? [];
  const dMax = labels?.d_max_m;

  return (
    <div
      className={`rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm ${className}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`chip text-[11px] ${
            source === "run"
              ? "border-risk/40 text-risk"
              : "border-amber-400/30 text-amber-200/80"
          }`}
        >
          {source === "run"
            ? `Live run · ${runId?.slice(0, 12) ?? "—"}`
            : "Demo figures — not a live model run"}
        </span>
        {flag("Synthetic exposure", labels?.synthetic_exposure !== false)}
        {flag("Proxy hazard", labels?.proxy_hazard !== false)}
        {flag("Assumed return periods", labels?.assumed_rp !== false)}
        {dMax != null ? (
          <span className="rounded-md border border-white/10 px-2 py-0.5 text-[11px] text-white/55">
            D_max {dMax} m
          </span>
        ) : null}
        {assumptionsVersion ? (
          <span className="rounded-md border border-white/10 px-2 py-0.5 text-[11px] text-white/55">
            Assumptions {assumptionsVersion}
          </span>
        ) : (
          <span className="rounded-md border border-white/10 px-2 py-0.5 text-[11px] text-white/55">
            Assumptions nairobi-pluvial-v1
          </span>
        )}
        {source !== "run" ? (
          <Link href="/data/start" className="text-accent hover:underline text-xs">
            Start a test run →
          </Link>
        ) : null}
      </div>
      <p className="mt-2 text-xs text-white/50">
        These are prototype / synthetic inputs — not Nairobi flood gauges or real
        claims. Do not treat placeholder or demo numbers as observations.
      </p>
      {notes.length > 0 ? (
        <ul className="mt-2 space-y-0.5 text-[11px] text-white/40">
          {notes.slice(0, 4).map((n) => (
            <li key={n}>• {n}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
