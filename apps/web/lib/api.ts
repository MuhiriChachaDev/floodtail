const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export type HealthPayload = {
  status?: string;
  ollama?: { available?: boolean; model?: string };
  models?: { hazard?: string; vulnerability?: string };
};

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { Accept: "application/json" },
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export async function fetchHealth(): Promise<HealthPayload | null> {
  return getJson<HealthPayload>("/v1/health");
}

export async function fetchLatestRunMetrics(): Promise<Record<
  string,
  unknown
> | null> {
  // Best-effort: list is not always available; callers fall back to demo numbers.
  return getJson("/v1/runs");
}

export { API_BASE };
