"use client";

import { useCallback, useEffect, useState } from "react";
import { heavyRainLosses, resolveEpMetrics, type ResolvedEpMetrics } from "./ep-metrics";
import { loadLastTestRun, type LastTestRun } from "./run-store";
import { formatKes } from "./format";

export type LivePortfolioView = {
  hasRun: boolean;
  last: LastTestRun | null;
  resolved: ResolvedEpMetrics;
  place: string;
  statusChip: string;
  weatherChip: string;
  aiSummary: string;
  attention: Array<{
    id: string;
    title: string;
    detail: string;
    href: string;
    tone: "warn" | "info" | "action";
  }>;
  concentration: Array<{ name: string; share: number; value: number }>;
  qualityChecks: Array<{ label: string; value: string; ok: boolean }>;
  freshnessLabel: string;
};

function housingConcentration(
  last: LastTestRun | null,
  resolved: ResolvedEpMetrics,
): Array<{ name: string; share: number; value: number }> {
  const counts = last?.portfolio.ingest_stats?.housing_class_counts;
  const byClass = last?.metrics?.accumulation_summary?.by_housing_class;
  if (Array.isArray(byClass) && byClass.length) {
    const rows = byClass
      .map((r) => {
        const name = String(r.housing_class ?? r.class ?? "Other").replaceAll(
          "_",
          " ",
        );
        const value = Number(r.tiv_kes ?? r.total_tiv_kes ?? r.loss_kes ?? 0);
        return { name, value };
      })
      .filter((r) => r.value > 0);
    const total = rows.reduce((s, r) => s + r.value, 0) || 1;
    return rows
      .sort((a, b) => b.value - a.value)
      .slice(0, 8)
      .map((r) => ({
        name: r.name,
        value: r.value,
        share: Math.round((r.value / total) * 100),
      }));
  }
  if (counts && Object.keys(counts).length) {
    const totalN = Object.values(counts).reduce((s, n) => s + n, 0) || 1;
    const tiv = resolved.totalTivKes || 0;
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .map(([name, n]) => ({
        name: name.replaceAll("_", " "),
        share: Math.round((n / totalN) * 100),
        value: tiv > 0 ? (tiv * n) / totalN : n,
      }));
  }
  return [];
}

function buildQualityChecks(last: LastTestRun | null, resolved: ResolvedEpMetrics) {
  const warnings = last?.portfolio.extra?.warnings ?? [];
  const n = resolved.nHouses || last?.portfolio.n_rows || 0;
  const bbox = last?.portfolio.ingest_stats?.bbox;
  const hasBbox = Array.isArray(bbox) && bbox.length === 4;
  const hazardWarn = warnings.some((w) =>
    /HAZARD_ZERO_FILL|outside raster|No hazard rasters overlap/i.test(w),
  );
  return [
    {
      label: "Rows ingested",
      value: n > 0 ? String(n) : "—",
      ok: n > 0,
    },
    {
      label: "Coordinates",
      value: hasBbox ? "BBox from upload" : n > 0 ? "Present" : "Missing",
      ok: n > 0,
    },
    {
      label: "Hazard scores",
      value: hazardWarn ? "Check CSV / coverage" : "Attached",
      ok: !hazardWarn,
    },
    {
      label: "Pipeline status",
      value: last?.status ?? "No run",
      ok: Boolean(
        last?.status &&
          !["FAILED", "ERROR", "HALTED"].includes(String(last.status).toUpperCase()),
      ),
    },
    {
      label: "Place label",
      value: last?.place || last?.portfolio.location_label || "—",
      ok: Boolean(last?.place || last?.portfolio.location_label),
    },
    {
      label: "Ingest notes",
      value: warnings.length ? `${warnings.length} note(s)` : "Clean",
      ok: warnings.length === 0,
    },
  ];
}

export function buildLivePortfolioView(last: LastTestRun | null): LivePortfolioView {
  const resolved = resolveEpMetrics(last?.metrics, {
    runId: last?.runId,
    locationLabel: last?.place || last?.portfolio.location_label,
  });
  const hasRun = Boolean(last?.runId && resolved.source === "run");
  const place = resolved.locationLabel;
  const heavy = heavyRainLosses(resolved.points);
  const concentration = housingConcentration(last, resolved);

  if (!hasRun) {
    return {
      hasRun: false,
      last,
      resolved,
      place: resolved.locationLabel,
      statusChip: "No live portfolio — upload to drive the map",
      weatherChip: "Waiting for portfolio test",
      aiSummary:
        "Upload a portfolio for any place (Kisumu, Mombasa, Nairobi, …) on Data → Start. The flood map, loss figures, and capital band will follow that book’s coordinates and scores.",
      attention: [
        {
          id: "upload",
          title: "Run a portfolio test",
          detail: "Upload CSV with lat, lon, housing_class, tiv_kes (hazard optional).",
          href: "/data/start",
          tone: "action",
        },
      ],
      concentration,
      qualityChecks: buildQualityChecks(last, resolved),
      freshnessLabel: "Demo fallback",
    };
  }

  const warnings = last?.portfolio.extra?.warnings ?? [];
  const attention: LivePortfolioView["attention"] = [];
  if (warnings.length) {
    attention.push({
      id: "warn",
      title: `${warnings.length} ingest note(s)`,
      detail: warnings[0],
      href: "/data/quality",
      tone: "warn",
    });
  }
  if (heavy.severe != null) {
    attention.push({
      id: "severe",
      title: `Severe flood loss ~ ${formatKes(heavy.severe)}`,
      detail: `From the last run on ${place}.`,
      href: "/finance",
      tone: "info",
    });
  }
  attention.push({
    id: "review",
    title: "Review capital / decision",
    detail: "Figures come from this portfolio’s pipeline run.",
    href: "/decisions/review",
    tone: "action",
  });

  const saved = last?.savedAt
    ? new Date(last.savedAt).toLocaleString()
    : "just now";

  return {
    hasRun: true,
    last,
    resolved,
    place,
    statusChip: `${place} · ${resolved.nHouses} locations`,
    weatherChip: `Run ${last?.status ?? "done"}`,
    aiSummary: `Live book: ${place}. ${resolved.nHouses} insured locations, TIV ${formatKes(resolved.totalTivKes)}, expected yearly loss ${formatKes(resolved.aalKes)}. Numbers come from the deterministic engine on this upload — not a Nairobi demo stub.`,
    attention,
    concentration,
    qualityChecks: buildQualityChecks(last, resolved),
    freshnessLabel: `Saved ${saved}`,
  };
}

/** Client hook: reloads when a new portfolio test is saved. */
export function useLivePortfolioView(): LivePortfolioView & { reload: () => void } {
  const [view, setView] = useState<LivePortfolioView>(() =>
    buildLivePortfolioView(null),
  );

  const reload = useCallback(() => {
    setView(buildLivePortfolioView(loadLastTestRun()));
  }, []);

  useEffect(() => {
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
  }, [reload]);

  return { ...view, reload };
}
