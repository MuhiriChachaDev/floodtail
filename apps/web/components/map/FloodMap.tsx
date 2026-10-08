"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { clsx } from "clsx";
import { Pause, Play } from "lucide-react";
import samplePortfolio from "@/lib/data/portfolio-sample.json";
import { fetchPortfolioProperties, fetchRunProperties } from "@/lib/api";
import {
  loadLastTestRun,
  patchLastTestRunMapPoints,
} from "@/lib/run-store";
import {
  centerFromBbox,
  floodRiskScore,
  propertyRowToPoint,
  RISK_COLORS,
  tryHydrateDemoSamplePoints,
  type PortfolioPoint,
} from "@/lib/map-portfolio";
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

const Map3D = dynamic(() => import("./MapLibre3DInner"), {
  ssr: false,
  loading: () => (
    <div className="grid h-full place-items-center text-sm text-white/50">
      Loading 3D portfolio map…
    </div>
  ),
});

type LiveMeta = {
  place: string;
  runId: string;
  nRows: number;
  synthetic: boolean;
  source: "run" | "portfolio" | "cache";
};

function sampleAsPoints(): PortfolioPoint[] {
  return samplePortfolio.points.map((p) => ({
    ...p,
    depth: Math.min(3.2, p.hazard_severe * 3.5 * 0.75),
    loss_kes: p.value_kes * p.hazard_severe * 0.35,
  }));
}

function mapRows(rows: unknown[] | undefined): PortfolioPoint[] {
  if (!rows?.length) return [];
  return rows
    .map((row) => propertyRowToPoint(row as Parameters<typeof propertyRowToPoint>[0]))
    .filter((p): p is PortfolioPoint => p != null);
}

export function FloodMap({
  mode = "overview",
  className,
  showTimeline = true,
  title = "Flood risk map",
}: Props) {
  const [insuredOnly, setInsuredOnly] = useState(true);
  const [basemap, setBasemap] = useState<"streets" | "satellite">("streets");
  const [playing, setPlaying] = useState(false);
  const [hour, setHour] = useState(8);
  const [selected, setSelected] = useState<string | null>(null);
  const [livePoints, setLivePoints] = useState<PortfolioPoint[] | null>(null);
  const [liveMeta, setLiveMeta] = useState<LiveMeta | null>(null);
  const [fallbackCenter, setFallbackCenter] = useState<[number, number] | null>(
    null,
  );
  const [loadState, setLoadState] = useState<
    "idle" | "loading" | "live" | "cache" | "demo" | "missing"
  >("idle");
  const liveRunIdRef = useRef<string | null>(null);

  const applyLive = useCallback(
    (
      mapped: PortfolioPoint[],
      last: NonNullable<ReturnType<typeof loadLastTestRun>>,
      source: LiveMeta["source"],
    ) => {
      liveRunIdRef.current = last.runId;
      setLivePoints(mapped);
      setLiveMeta({
        place: last.place || last.portfolio.location_label || "Uploaded portfolio",
        runId: last.runId,
        nRows: mapped.length,
        synthetic: Boolean(last.portfolio.synthetic),
        source,
      });
      setFallbackCenter(centerFromBbox(last.portfolio.ingest_stats?.bbox));
      setLoadState(source === "cache" ? "cache" : "live");
      setSelected(null);
      // Persist so the next visit (or API restart) keeps this geography.
      patchLastTestRunMapPoints(mapped);
    },
    [],
  );

  const reloadLive = useCallback(async () => {
    const last = loadLastTestRun();
    if (!last?.runId) {
      liveRunIdRef.current = null;
      setLivePoints(null);
      setLiveMeta(null);
      setFallbackCenter(null);
      setLoadState("demo");
      return;
    }

    const place =
      last.place || last.portfolio.location_label || "Uploaded portfolio";
    const bboxCenter = centerFromBbox(last.portfolio.ingest_stats?.bbox);
    setFallbackCenter(bboxCenter);

    // Drop previous city's columns immediately when a new upload lands.
    if (liveRunIdRef.current && liveRunIdRef.current !== last.runId) {
      setLivePoints([]);
      setLiveMeta({
        place,
        runId: last.runId,
        nRows: 0,
        synthetic: Boolean(last.portfolio.synthetic),
        source: "cache",
      });
    }
    liveRunIdRef.current = last.runId;
    setLoadState("loading");

    // 1) Fresh scored rows from the last run
    const runPayload = await fetchRunProperties(last.runId, { limit: 600 });
    // Ignore stale responses if a newer upload landed while we were fetching.
    if (liveRunIdRef.current !== last.runId) return;
    const fromRun = mapRows(runPayload?.properties);
    if (fromRun.length) {
      applyLive(fromRun, last, "run");
      return;
    }

    // 2) Portfolio exposure rows (lat/lon/TIV) if run props expired in memory
    if (last.portfolio?.id) {
      const portPayload = await fetchPortfolioProperties(last.portfolio.id, {
        limit: 600,
      });
      if (liveRunIdRef.current !== last.runId) return;
      const fromPort = mapRows(portPayload?.properties);
      if (fromPort.length) {
        applyLive(fromPort, last, "portfolio");
        return;
      }
    }

    // 3) Coordinates cached with the last test run in localStorage
    if (last.mapPoints?.length) {
      if (liveRunIdRef.current !== last.runId) return;
      applyLive(last.mapPoints, last, "cache");
      return;
    }

    // 4) Shipped Kisumu sample only when this book looks like that demo
    const fromSample = await tryHydrateDemoSamplePoints({
      place,
      portfolioName: last.portfolio.name,
      portfolioSource: last.portfolio.source,
      nRows: last.portfolio.n_rows,
    });
    if (fromSample.length) {
      applyLive(fromSample, last, "cache");
      return;
    }

    // 5) Keep the place label — never silently show Nairobi demo for another book
    setLivePoints([]);
    setLiveMeta({
      place,
      runId: last.runId,
      nRows: 0,
      synthetic: Boolean(last.portfolio.synthetic),
      source: "cache",
    });
    setLoadState("missing");
    setSelected(null);
  }, [applyLive]);

  useEffect(() => {
    void reloadLive();
    const onStorage = (e: StorageEvent) => {
      if (e.key === "floodtail.lastTestRun.v1") void reloadLive();
    };
    const onFocus = () => void reloadLive();
    const onRunSaved = () => void reloadLive();
    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", onFocus);
    window.addEventListener("floodtail:last-run", onRunSaved);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("floodtail:last-run", onRunSaved);
    };
  }, [reloadLive]);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setHour((h) => (h >= 24 ? 0 : h + 1));
    }, 700);
    return () => window.clearInterval(id);
  }, [playing]);

  const hasLiveBook = liveMeta != null;
  const usingLive = livePoints != null && livePoints.length > 0;
  // Only the Nairobi sample when there is no last portfolio test at all.
  const basePoints = usingLive
    ? livePoints
    : hasLiveBook
      ? []
      : sampleAsPoints();

  const points = useMemo(() => {
    const list = basePoints.filter((p) => (insuredOnly ? p.insured : true));
    return list.map((p) => {
      if (usingLive) {
        // Live: depth comes from the engine; rainfall slider gently scales it.
        const depthBoost = 0.7 + (hour / 24) * 0.45;
        return {
          ...p,
          depth: Math.min(3.5, p.depth * depthBoost),
        };
      }
      const depthBoost = hour / 24;
      const depth = Math.min(3.2, p.hazard_severe * 3.5 * (0.55 + depthBoost));
      return { ...p, depth };
    });
  }, [basePoints, insuredOnly, hour, usingLive]);

  const hotspots = useMemo(() => {
    if (usingLive) {
      // High-risk sites from this portfolio act as local accumulation markers.
      return points
        .filter((p) => floodRiskScore(p) >= 0.55)
        .slice(0, 24)
        .map((p) => ({ name: p.id, lat: p.lat, lon: p.lon }));
    }
    if (hasLiveBook) return [];
    return samplePortfolio.hotspots;
  }, [usingLive, hasLiveBook, points]);

  const selectedPoint = points.find((p) => p.id === selected) ?? null;

  const placeLabel = hasLiveBook
    ? liveMeta?.place ?? "Uploaded portfolio"
    : "Nairobi (demo)";

  const modeHint =
    loadState === "missing"
      ? "map coordinates unavailable — re-run the portfolio test on Data → Start"
      : mode === "quality"
        ? "columns coloured by location confidence"
        : mode === "portfolio"
          ? "columns extruded by covered TIV · colour = flood risk"
          : mode === "hazard"
            ? "colour = flood risk · height = covered value"
            : mode === "loss" || mode === "risk"
              ? "colour = flood / loss intensity"
              : mode === "capital"
                ? "capital concentration · colour = flood risk"
                : "colour-coded flood risk on real portfolio coordinates";

  const statusChip =
    loadState === "loading"
      ? "Loading…"
      : loadState === "missing"
        ? "Re-run needed"
        : usingLive
          ? loadState === "cache"
            ? "Cached run"
            : "Live run"
          : "Demo map";

  return (
    <div className={clsx("glass relative overflow-hidden rounded-2xl", className)}>
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-white/10 px-3 py-3 sm:px-4">
        <div className="min-w-0 flex-1">
          <h3 className="section-title text-sm uppercase tracking-[0.12em] sm:text-base">
            {title}
          </h3>
          <p className="text-xs text-white/45">
            {placeLabel}
            {usingLive
              ? ` · ${liveMeta?.nRows ?? points.length} locations from last run`
              : hasLiveBook
                ? ""
                : " · synthetic demo portfolio"}{" "}
            · {modeHint}
          </p>
        </div>
        <span className="chip shrink-0 text-risk">
          <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-risk" />
          {statusChip}
        </span>
      </div>

      <div className="map-shell relative h-[min(55vh,360px)] min-h-[280px] sm:h-[520px] sm:min-h-0">
        {loadState === "missing" ? (
          <div className="absolute inset-0 z-[400] flex items-center justify-center bg-night-950/70 px-6 text-center backdrop-blur-sm">
            <p className="max-w-sm text-sm text-white/70">
              Last test was for <span className="text-accent">{placeLabel}</span>,
              but map coordinates are no longer on the API. Re-run the portfolio
              on Data → Start so the flood map follows that book.
            </p>
          </div>
        ) : null}
        <Map3D
          key={`${basemap}-${hasLiveBook ? liveMeta?.runId : "demo"}-${usingLive ? "pts" : "empty"}-${fallbackCenter?.join(",") ?? "k"}`}
          mode={mode}
          basemap={basemap}
          points={points}
          hotspots={hotspots}
          selectedId={selected}
          onSelect={setSelected}
          fitToData
          fallbackCenter={fallbackCenter}
        />

        <div className="pointer-events-none absolute right-2 top-2 z-[500] hidden rounded-xl border border-white/10 bg-night-950/80 p-2.5 text-xs backdrop-blur sm:right-3 sm:top-3 sm:block sm:p-3">
          <p className="mb-2 font-semibold uppercase tracking-wide text-white/60">
            Flood risk
          </p>
          <div
            className="mb-1 h-24 w-3 rounded-full"
            style={{
              background: `linear-gradient(to bottom, ${RISK_COLORS.extreme}, ${RISK_COLORS.high}, ${RISK_COLORS.moderate}, ${RISK_COLORS.low}, ${RISK_COLORS.veryLow})`,
            }}
          />
          <div className="mt-1 space-y-1 text-white/50">
            <p className="flex items-center gap-1.5">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: RISK_COLORS.extreme }}
              />
              Extreme
            </p>
            <p className="flex items-center gap-1.5">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: RISK_COLORS.high }}
              />
              High (light red)
            </p>
            <p className="flex items-center gap-1.5">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: RISK_COLORS.moderate }}
              />
              Moderate
            </p>
            <p className="flex items-center gap-1.5">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: RISK_COLORS.veryLow }}
              />
              Low
            </p>
          </div>
          <p className="mt-2 text-[10px] text-white/40">Height = covered TIV</p>
        </div>

        <div className="absolute left-2 top-2 z-[500] flex max-w-[calc(100%-1rem)] flex-wrap gap-1.5 sm:left-14 sm:top-3 sm:gap-2">
          <button
            type="button"
            onClick={() => setBasemap("streets")}
            className={clsx(
              "rounded-full px-2.5 py-1.5 text-[11px] font-medium backdrop-blur sm:px-3 sm:text-xs",
              basemap === "streets"
                ? "bg-accent text-night-950"
                : "border border-white/15 bg-night-950/70 text-white/70",
            )}
          >
            Streets
          </button>
          <button
            type="button"
            onClick={() => setBasemap("satellite")}
            className={clsx(
              "rounded-full px-2.5 py-1.5 text-[11px] font-medium backdrop-blur sm:px-3 sm:text-xs",
              basemap === "satellite"
                ? "bg-accent text-night-950"
                : "border border-white/15 bg-night-950/70 text-white/70",
            )}
          >
            Satellite
          </button>
        </div>

        <div className="absolute bottom-2 left-2 z-[500] flex max-w-[calc(100%-1rem)] flex-wrap gap-1.5 sm:bottom-3 sm:left-3 sm:gap-2">
          <button
            type="button"
            onClick={() => setInsuredOnly(true)}
            className={clsx(
              "rounded-full px-2.5 py-1.5 text-[11px] font-medium backdrop-blur sm:px-3 sm:text-xs",
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
              "rounded-full px-2.5 py-1.5 text-[11px] font-medium backdrop-blur sm:px-3 sm:text-xs",
              !insuredOnly
                ? "bg-accent text-night-950"
                : "border border-white/15 bg-night-950/70 text-white/70",
            )}
          >
            All buildings
          </button>
        </div>

        <div className="pointer-events-none absolute bottom-3 right-3 z-[500] hidden rounded-xl border border-white/10 bg-night-950/80 px-3 py-2 text-[11px] text-white/55 backdrop-blur sm:block">
          Drag to orbit · Scroll to zoom · Click a column
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
              <span>Rainfall stress (next 24h)</span>
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
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: RISK_COLORS.high }}
              />{" "}
              High risk
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: RISK_COLORS.moderate }}
              />{" "}
              Moderate
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span
                className="h-2 w-2 rounded-full"
                style={{ background: RISK_COLORS.veryLow }}
              />{" "}
              Low
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
            {placeLabel} · {selectedPoint.lat.toFixed(4)}, {selectedPoint.lon.toFixed(4)}{" "}
            · Covered value {formatKes(selectedPoint.value_kes)} · Depth{" "}
            {selectedPoint.depth.toFixed(1)} m · Hazard{" "}
            {(selectedPoint.hazard_severe * 100).toFixed(0)}% · Risk{" "}
            {(floodRiskScore(selectedPoint) * 100).toFixed(0)}%
            {selectedPoint.synthetic ? " · Synthetic" : ""}
          </p>
        </div>
      ) : null}
    </div>
  );
}
