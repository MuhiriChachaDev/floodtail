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

export type EPPoint = {
  return_period: number;
  aep: number;
  loss_kes: number;
};

export type TierLoss = {
  tier: string;
  return_period: number;
  aep: number;
  loss_kes: number;
  mean_damage_ratio?: number | null;
};

export type CapitalBand = {
  floor_kes: number;
  central_kes: number;
  ceiling_kes: number;
  currency?: string;
  method?: string;
  floor_basis?: string;
  central_basis?: string;
  ceiling_basis?: string;
  notes?: string[];
};

export type DataLabels = {
  synthetic_exposure?: boolean;
  proxy_hazard?: boolean;
  assumed_rp?: boolean;
  d_max_m?: number;
  location_flexible?: boolean;
  notes?: string[];
};

export type TreatyTerms = {
  name: string;
  status?: string;
  currency?: string;
  attachment_kes: number;
  limit_kes: number;
  retention_kes: number;
  notes?: string[];
};

export type LayeredLoss = {
  tier: string;
  return_period: number;
  aep: number;
  gross_kes: number;
  retained_kes: number;
  recovery_kes: number;
  net_kes: number;
};

export type FinancialView = {
  treaty: TreatyTerms;
  layered_by_tier: LayeredLoss[];
  ep_curve_gross?: EPPoint[];
  ep_curve_net?: EPPoint[];
  aal_gross_kes: number;
  aal_net_kes: number;
  aal_ceded_kes: number;
  reference_tier?: string;
};

export type PricingIndication = {
  aal_basis_kes: number;
  load_factor: number;
  technical_premium_kes: number;
  currency?: string;
  formula?: string;
  basis?: string;
  status?: string;
  notes?: string[];
};

export type MetricsPayload = {
  run_id?: string;
  portfolio_id?: string;
  assumptions_version?: string;
  total_tiv_kes?: number;
  aal_kes?: number;
  n_insured_houses?: number;
  n_locations?: number;
  location_label?: string;
  ep_curve?: EPPoint[];
  tier_losses?: TierLoss[];
  capital_band?: CapitalBand | null;
  financial?: FinancialView | null;
  pricing?: PricingIndication | null;
  hazard_model_version?: string | null;
  vuln_model_version?: string | null;
  baseline_delta?: Record<string, unknown>;
  accumulation_summary?: {
    by_housing_class?: Array<Record<string, unknown>>;
    top_locations?: Array<Record<string, unknown>>;
    reference_tier?: string;
  };
  depth_damage_summary?: {
    source?: string;
    d_max_m?: number;
    assumptions_version?: string;
    by_tier?: Array<{
      tier: string;
      return_period: number;
      mean_depth_m: number;
      mean_damage_ratio: number;
      p90_depth_m?: number;
      p90_damage_ratio?: number;
    }>;
    by_housing_class?: Array<{
      housing_class: string;
      n: number;
      reference_tier?: string;
      mean_depth_m: number;
      mean_damage_ratio: number;
    }>;
    prior_curves?: Record<
      string,
      Array<{ depth_m: number; damage_ratio: number }>
    >;
  };
  data_labels?: DataLabels;
  warnings?: string[];
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
