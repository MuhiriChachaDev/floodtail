const DIRECT_API =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

/**
 * Call the FastAPI backend directly (not via Next rewrite).
 * Long pipeline runs (~30–60s) hang up the Next.js proxy and surface as
 * opaque "Internal Server Error" — direct CORS calls avoid that.
 */
function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${DIRECT_API}${p}`;
}

function protoHeaders(extra?: HeadersInit): HeadersInit {
  return {
    Accept: "application/json",
    "X-Floodtail-Role": "underwriter",
    "X-Floodtail-Actor": "web-tester",
    "X-Floodtail-Tenant": "default",
    ...extra,
  };
}

export type HealthPayload = {
  status?: string;
  ollama_up?: boolean;
  registry?: {
    registry_ready?: boolean;
    hazard_pinned?: string | null;
    vulnerability_pinned?: string | null;
  };
};

export type PortfolioPayload = {
  id: string;
  name: string;
  location_label: string;
  source: string;
  synthetic: boolean;
  n_rows: number;
};

export type RunStage = {
  stage?: string;
  name?: string;
  status?: string;
  message?: string;
  warnings?: string[];
};

export type MetricsPayload = {
  total_tiv_kes?: number;
  aal_kes?: number;
  n_locations?: number;
  ep_curve?: Array<{ return_period?: number; loss_kes?: number }>;
  data_labels?: Record<string, unknown>;
  [key: string]: unknown;
};

export type CreateRunResponse = {
  run: {
    id: string;
    status: string;
    stages?: RunStage[];
    error?: string | null;
  };
  metrics: MetricsPayload | null;
  insight?: Record<string, unknown> | null;
  ollama_degraded?: boolean;
};

async function parseError(res: Response): Promise<string> {
  const text = await res.text();
  if (text === "Internal Server Error" || !text) {
    return (
      `Backend error (${res.status}). Is the API running on ${DIRECT_API}? ` +
      "Start it with: uvicorn apps.api.main:app --reload --port 8000"
    );
  }
  try {
    const body = JSON.parse(text);
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    if (detail?.message) return String(detail.message);
    if (Array.isArray(detail)) {
      return detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ");
    }
    return JSON.stringify(body);
  } catch {
    return text.slice(0, 400) || res.statusText || `HTTP ${res.status}`;
  }
}

async function fetchSafe(input: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch {
    throw new Error(
      `Cannot reach the FLOODTAIL API at ${DIRECT_API}. ` +
        "Start it with: cd floodtail && .venv/bin/uvicorn apps.api.main:app --port 8000",
    );
  }
}

export async function fetchHealth(): Promise<HealthPayload | null> {
  try {
    const res = await fetch(apiUrl("/v1/health"), {
      headers: protoHeaders(),
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as HealthPayload;
  } catch {
    return null;
  }
}

export async function uploadPortfolio(opts: {
  file: File;
  locationLabel: string;
  name?: string;
}): Promise<{ portfolio: PortfolioPayload; warnings: string[] }> {
  const form = new FormData();
  form.append("source", "upload");
  form.append("location_label", opts.locationLabel.trim() || "uploaded");
  if (opts.name?.trim()) form.append("name", opts.name.trim());
  form.append("file", opts.file);

  const res = await fetchSafe(apiUrl("/v1/portfolios"), {
    method: "POST",
    headers: protoHeaders(),
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function createBuiltinPortfolio(opts?: {
  locationLabel?: string;
  name?: string;
}): Promise<{ portfolio: PortfolioPayload; warnings: string[] }> {
  const form = new FormData();
  form.append("source", "builtin_nairobi");
  form.append("location_label", opts?.locationLabel || "Nairobi County");
  if (opts?.name) form.append("name", opts.name);

  const res = await fetchSafe(apiUrl("/v1/portfolios"), {
    method: "POST",
    headers: protoHeaders(),
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function createRun(portfolioId: string): Promise<CreateRunResponse> {
  const res = await fetchSafe(apiUrl("/v1/runs"), {
    method: "POST",
    headers: protoHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      portfolio_id: portfolioId,
      use_ml: true,
      features_approved: true,
      require_human_gate_1: false,
    }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchRunMetrics(
  runId: string,
): Promise<MetricsPayload | null> {
  try {
    const res = await fetch(apiUrl(`/v1/runs/${runId}/metrics`), {
      headers: protoHeaders(),
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = await res.json();
    return (data.metrics ?? null) as MetricsPayload | null;
  } catch {
    return null;
  }
}

export { DIRECT_API as API_BASE };
