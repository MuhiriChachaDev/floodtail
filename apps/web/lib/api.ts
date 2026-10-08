const DIRECT_API =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

const TOKEN_KEY = "floodtail.api_token.v1";

/**
 * Call the FastAPI backend directly (not via Next rewrite).
 * Long pipeline runs (~30–60s) hang up the Next.js proxy and surface as
 * opaque "Internal Server Error" — direct CORS calls avoid that.
 */
function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${DIRECT_API}${p}`;
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAccessToken(token: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

function protoHeaders(extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "X-Floodtail-Role": "underwriter",
    "X-Floodtail-Actor": "web-tester",
    "X-Floodtail-Tenant": "default",
  };
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return { ...headers, ...extra };
}

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  role: string;
  actor: string;
  tenant_id: string;
};

/** Exchange email/password for a JWT (required when API ENV != prototype). */
export async function fetchAccessToken(opts: {
  email: string;
  password: string;
  role?: string;
}): Promise<TokenResponse> {
  const res = await fetchSafe(apiUrl("/v1/auth/token"), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: opts.email,
      password: opts.password,
      role: opts.role || "underwriter",
    }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
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

export type IngestStatsPayload = {
  n_insured_houses?: number;
  total_tiv_kes?: number;
  location_label?: string;
  /** min_lat, min_lon, max_lat, max_lon */
  bbox?: [number, number, number, number] | number[] | null;
  housing_class_counts?: Record<string, number>;
  synthetic?: boolean;
  source?: string;
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

export type PortfolioPayload = {
  id: string;
  name: string;
  location_label: string;
  source: string;
  synthetic: boolean;
  n_rows: number;
  ingest_stats?: IngestStatsPayload | null;
  data_labels?: DataLabels | null;
  extra?: {
    warnings?: string[];
    column_mapping?: Record<string, string>;
  };
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

/** RAG knowledge document after ingest (PDF / DOCX / text). */
export type KnowledgeDocumentResult = {
  document_id: string;
  filename: string;
  n_chunks: number;
  backend: string;
  embedding_degraded?: boolean;
  warnings?: string[];
};

export type KnowledgeSearchHit = {
  content: string;
  score: number;
  document_id: string;
  chunk_index: number;
  filename: string;
};

export type KnowledgeSearchResult = {
  query: string;
  n_hits: number;
  context: string;
  hits: KnowledgeSearchHit[];
  backend?: string;
};

export async function uploadKnowledgeDocument(opts: {
  file: File;
  locationLabel?: string;
  title?: string;
}): Promise<{ document: KnowledgeDocumentResult }> {
  const form = new FormData();
  form.append("file", opts.file);
  const meta: Record<string, string> = {};
  if (opts.locationLabel?.trim()) meta.location_label = opts.locationLabel.trim();
  if (opts.title?.trim()) meta.title = opts.title.trim();
  if (Object.keys(meta).length) {
    form.append("metadata_json", JSON.stringify(meta));
  }

  const res = await fetchSafe(apiUrl("/v1/knowledge/documents"), {
    method: "POST",
    headers: protoHeaders(),
    body: form,
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function searchKnowledge(opts: {
  query: string;
  k?: number;
  documentId?: string;
}): Promise<KnowledgeSearchResult> {
  const res = await fetchSafe(apiUrl("/v1/knowledge/search"), {
    method: "POST",
    headers: protoHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      query: opts.query,
      k: opts.k ?? 6,
      document_id: opts.documentId || null,
    }),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
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

/** One scored location row from GET /v1/runs/{id}/properties. */
export type RunPropertyRow = {
  loc_id?: string;
  lat?: number;
  lon?: number;
  housing_class?: string;
  tiv_kes?: number;
  synthetic?: boolean;
  dist_hotspot_km?: number | null;
  dist_waterway_km?: number | null;
  loss_kes_severe?: number | null;
  loss_kes_extreme?: number | null;
  damage_ratio_severe?: number | null;
  damage_ratio_extreme?: number | null;
  depth_m_severe?: number | null;
  depth_m_extreme?: number | null;
  hazard_score_severe?: number | null;
  hazard_score_extreme?: number | null;
  hazard_score_pred_severe?: number | null;
  hazard_score_pred_extreme?: number | null;
  [key: string]: unknown;
};

export type RunPropertiesPayload = {
  run_id: string;
  total: number;
  offset: number;
  limit: number;
  properties: RunPropertyRow[];
};

export async function fetchRunProperties(
  runId: string,
  opts?: { limit?: number; offset?: number },
): Promise<RunPropertiesPayload | null> {
  try {
    const limit = opts?.limit ?? 600;
    const offset = opts?.offset ?? 0;
    const res = await fetch(
      apiUrl(`/v1/runs/${runId}/properties?limit=${limit}&offset=${offset}`),
      { headers: protoHeaders(), cache: "no-store" },
    );
    if (!res.ok) return null;
    return (await res.json()) as RunPropertiesPayload;
  } catch {
    return null;
  }
}

export async function fetchPortfolioProperties(
  portfolioId: string,
  opts?: { limit?: number; offset?: number },
): Promise<{
  portfolio_id: string;
  location_label?: string;
  total: number;
  properties: RunPropertyRow[];
  bbox?: number[] | null;
} | null> {
  try {
    const limit = opts?.limit ?? 600;
    const offset = opts?.offset ?? 0;
    const res = await fetch(
      apiUrl(
        `/v1/portfolios/${portfolioId}/properties?limit=${limit}&offset=${offset}`,
      ),
      { headers: protoHeaders(), cache: "no-store" },
    );
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export { DIRECT_API as API_BASE };
