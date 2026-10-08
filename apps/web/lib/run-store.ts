import type { CreateRunResponse, MetricsPayload, PortfolioPayload } from "./api";

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
};

export function saveLastTestRun(
  place: string,
  portfolio: PortfolioPayload,
  result: CreateRunResponse,
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
  };
  if (typeof window !== "undefined") {
    window.localStorage.setItem(KEY, JSON.stringify(record));
  }
  return record;
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
