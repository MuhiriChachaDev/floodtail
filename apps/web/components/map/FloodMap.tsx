"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { clsx } from "clsx";
import { Pause, Play } from "lucide-react";
import portfolio from "@/lib/data/portfolio-sample.json";
import { assetEmoji, classLabel, formatKes } from "@/lib/format";

export type MapMode =
  | "overview"
  | "quality"
  | "portfolio"
  | "hazard"
  | "loss"
  | "risk"
  | "capital"
  | "decision";

type Props = {
  mode?: MapMode;
  className?: string;
  showTimeline?: boolean;
  title?: string;
};

const LeafletMap = dynamic(() => import("./LeafletInner"), {
  ssr: false,
  loading: () => (
    <div className="grid h-full place-items-center text-sm text-white/50">
      Loading map…
    </div>
  ),
});

export function FloodMap({
  mode = "overview",
  className,
  showTimeline = true,
  title = "Flood risk map",
}: Props) {
  const [insuredOnly, setInsuredOnly] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [hour, setHour] = useState(8);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setHour((h) => (h >= 24 ? 0 : h + 1));
    }, 700);
    return () => window.clearInterval(id);
  }, [playing]);

  const points = useMemo(() => {
    const list = portfolio.points.filter((p) => (insuredOnly ? p.insured : true));
    return list.map((p) => {
      const depthBoost = hour / 24;
      const depth = Math.min(3.2, p.hazard_severe * 3.5 * (0.55 + depthBoost));
      return { ...p, depth };
    });
  }, [insuredOnly, hour]);

  const selectedPoint = points.find((p) => p.id === selected) ?? null;

  return (
    <div className={clsx("glass relative overflow-hidden rounded-2xl", className)}>
      <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
        <div>
          <h3 className="section-title text-base uppercase tracking-[0.12em]">
            {title}
          </h3>
          <p className="text-xs text-white/45">
            Nairobi · synthetic demo portfolio ·{" "}
            {mode === "quality"
              ? "showing location confidence"
              : mode === "portfolio"
                ? "showing covered value"
                : mode === "hazard"
                  ? "showing flood conditions"
                  : "showing current flood view"}
          </p>
        </div>
        <span className="chip text-risk">
          <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-risk" />
          Live simulation
        </span>
      </div>

      <div className="map-shell relative h-[380px] sm:h-[460px]">
        <LeafletMap
          mode={mode}
          points={points}
          hotspots={portfolio.hotspots}
          selectedId={selected}
          onSelect={setSelected}
        />

        <div className="pointer-events-none absolute right-3 top-3 z-[500] rounded-xl border border-white/10 bg-night-950/80 p-3 text-xs backdrop-blur">
          <p className="mb-2 font-semibold uppercase tracking-wide text-white/60">
            Flood depth
          </p>
          <div className="mb-1 h-24 w-3 rounded-full bg-gradient-to-b from-sky-200 via-blue-500 to-indigo-950" />
          <div className="mt-1 space-y-1 text-white/50">
            <p>&gt; 3.0 m</p>
            <p>1.5 m</p>
            <p>&lt; 0.5 m</p>
          </div>
        </div>

        <div className="absolute bottom-3 left-3 z-[500] flex gap-2">
          <button
            type="button"
            onClick={() => setInsuredOnly(true)}
            className={clsx(
              "rounded-full px-3 py-1.5 text-xs font-medium backdrop-blur",
              insuredOnly
                ? "bg-accent text-night-950"
                : "border border-white/15 bg-night-950/70 text-white/70",
            )}
          >
            Insured
          </button>
          <button
            type="button"
            onClick={() => setInsuredOnly(false)}
            className={clsx(
              "rounded-full px-3 py-1.5 text-xs font-medium backdrop-blur",
              !insuredOnly
                ? "bg-accent text-night-950"
                : "border border-white/15 bg-night-950/70 text-white/70",
            )}
          >
            All buildings
          </button>
        </div>
      </div>

      {showTimeline ? (
        <div className="flex flex-col gap-3 border-t border-white/10 px-4 py-3 sm:flex-row sm:items-center">
          <button
            type="button"
            onClick={() => setPlaying((p) => !p)}
            className="btn-ghost !rounded-full !px-3 !py-2"
            aria-label={playing ? "Pause rainfall timeline" : "Play rainfall timeline"}
          >
            {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>
          <div className="flex-1">
            <div className="mb-1 flex justify-between text-xs text-white/50">
              <span>Rainfall (next 24h)</span>
              <span>Hour {hour}</span>
            </div>
            <input
              type="range"
              min={0}
              max={24}
              value={hour}
              onChange={(e) => {
                setPlaying(false);
                setHour(Number(e.target.value));
              }}
              className="w-full accent-accent"
            />
          </div>
          <div className="flex flex-wrap gap-3 text-[11px] text-white/55">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-cyan-400" /> Insured
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-orange-400" /> Uninsured
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-rose-400" /> Hotspot
            </span>
          </div>
        </div>
      ) : null}

      {selectedPoint ? (
        <div className="border-t border-white/10 bg-night-900/60 px-4 py-3 text-sm">
          <p className="font-medium text-white">
            {assetEmoji(selectedPoint.asset)} {selectedPoint.id} ·{" "}
            {classLabel(selectedPoint.housing)}
          </p>
          <p className="mt-1 text-white/60">
            Covered value {formatKes(selectedPoint.value_kes)} · Estimated depth{" "}
            {selectedPoint.depth.toFixed(1)} m ·{" "}
            {selectedPoint.synthetic ? "Synthetic demo property" : "Recorded property"}
          </p>
        </div>
      ) : null}
    </div>
  );
}
