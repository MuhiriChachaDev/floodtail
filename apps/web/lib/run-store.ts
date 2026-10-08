import type { CreateRunResponse, MetricsPayload, PortfolioPayload } from "./api";
import type { PortfolioPoint } from "./map-portfolio";

const KEY = "floodtail.lastTestRun.v1";

export type LastTestRun = {
  savedAt: string;
  place: string;
  portfolio: PortfolioPayload;
  runId: string;
  status: string;
  metrics: MetricsPayload | null;
  stages: Array<{ stage?: string; name?: string; status?: string; message?: string }>;
  insight?: Record<string, unknown> | null;
  ollamaDegraded?: boolean;
  /**
   * Slim scored coordinates for the flood map. Cached so the map follows the
   * uploaded place (Kisumu, Mombasa, …) even if the API process restarted and
   * in-memory run properties are gone.
   */
  mapPoints?: PortfolioPoint[];
};

function emitSaved(record: LastTestRun) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, JSON.stringify(record));
  // Same-tab listeners (FloodMap) — `storage` only fires across tabs.
  window.dispatchEvent(new CustomEvent("floodtail:last-run", { detail: record }));
}

export function saveLastTestRun(
  place: string,
  portfolio: PortfolioPayload,
  result: CreateRunResponse,
  opts?: { mapPoints?: PortfolioPoint[] },
): LastTestRun {
  const record: LastTestRun = {
    savedAt: new Date().toISOString(),
    place,
    portfolio,
    runId: result.run.id,
    status: result.run.status,
    metrics: result.metrics,
    stages: result.run.stages ?? [],
    insight: result.insight ?? null,
    ollamaDegraded: result.ollama_degraded,
    mapPoints: opts?.mapPoints,
  };
  emitSaved(record);
  return record;
}

/** Merge map coordinates into an existing last-run record (same runId). */
export function patchLastTestRunMapPoints(mapPoints: PortfolioPoint[]): LastTestRun | null {
  const current = loadLastTestRun();
  if (!current?.runId || !mapPoints.length) return current;
  const next: LastTestRun = { ...current, mapPoints };
  emitSaved(next);
  return next;
}

export function loadLastTestRun(): LastTestRun | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    return JSON.parse(raw) as LastTestRun;
  } catch {
    return null;
  }
}
