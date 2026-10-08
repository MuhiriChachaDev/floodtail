import type { RunPropertyRow } from "./api";

export type PortfolioPoint = {
  id: string;
  lat: number;
  lon: number;
  asset: string;
  housing: string;
  value_kes: number;
  hazard_severe: number;
  insured: boolean;
  confidence: string;
  synthetic: boolean;
  depth: number;
  loss_kes?: number;
};

/**
 * Flood-risk colour scale (low → high).
 * High risk uses light / medium red as requested.
 */
export const RISK_COLORS = {
  veryLow: "#fef9c3", // pale yellow
  low: "#fde68a",
  moderate: "#fdba74", // orange
  high: "#fca5a5", // light red
  extreme: "#ef4444", // strong red
} as const;

/** 0–1 composite flood risk from hazard, depth, and loss share of TIV. */
export function floodRiskScore(p: {
  hazard_severe: number;
  depth: number;
  value_kes: number;
  loss_kes?: number;
}): number {
  const fromHazard = Math.max(0, Math.min(1, p.hazard_severe));
  const fromDepth = Math.max(0, Math.min(1, p.depth / 3.2));
  const lossShare =
    p.value_kes > 0 && p.loss_kes != null
      ? Math.max(0, Math.min(1, p.loss_kes / p.value_kes))
      : 0;
  return Math.max(fromHazard, fromDepth * 0.85, lossShare);
}

export function colorForFloodRisk(score: number): string {
  if (score >= 0.72) return RISK_COLORS.extreme;
  if (score >= 0.5) return RISK_COLORS.high;
  if (score >= 0.32) return RISK_COLORS.moderate;
  if (score >= 0.15) return RISK_COLORS.low;
  return RISK_COLORS.veryLow;
}

function num(v: unknown, fallback = 0): number {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : fallback;
}

/** Map a scored run property row into a map column. */
export function propertyRowToPoint(row: RunPropertyRow): PortfolioPoint | null {
  const lat = num(row.lat, NaN);
  const lon = num(row.lon, NaN);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;

  const hazard = Math.max(
    num(row.hazard_score_pred_extreme),
    num(row.hazard_score_pred_severe),
    num(row.hazard_score_extreme),
    num(row.hazard_score_severe),
  );
  const depthRaw = Math.max(num(row.depth_m_extreme), num(row.depth_m_severe));
  const depth = depthRaw > 0 ? depthRaw : Math.min(3.2, hazard * 3.5);
  const loss = Math.max(num(row.loss_kes_extreme), num(row.loss_kes_severe));
  const value = num(row.tiv_kes);

  return {
    id: String(row.loc_id ?? `${lat.toFixed(4)}_${lon.toFixed(4)}`),
    lat,
    lon,
    asset: "residential",
    housing: String(row.housing_class ?? "unknown"),
    value_kes: value,
    hazard_severe: hazard,
    insured: true,
    confidence: "high",
    synthetic: Boolean(row.synthetic),
    depth,
    loss_kes: loss,
  };
}

export function boundsFromPoints(
  points: Array<{ lat: number; lon: number }>,
): [[number, number], [number, number]] | null {
  if (!points.length) return null;
  let minLat = Infinity;
  let maxLat = -Infinity;
  let minLon = Infinity;
  let maxLon = -Infinity;
  for (const p of points) {
    if (!Number.isFinite(p.lat) || !Number.isFinite(p.lon)) continue;
    minLat = Math.min(minLat, p.lat);
    maxLat = Math.max(maxLat, p.lat);
    minLon = Math.min(minLon, p.lon);
    maxLon = Math.max(maxLon, p.lon);
  }
  if (!Number.isFinite(minLat) || !Number.isFinite(minLon)) return null;
  // Pad tiny single-point / tight clusters so fitBounds still frames the area.
  const padLat = Math.max(0.008, (maxLat - minLat) * 0.18);
  const padLon = Math.max(0.008, (maxLon - minLon) * 0.18);
  return [
    [minLon - padLon, minLat - padLat],
    [maxLon + padLon, maxLat + padLat],
  ];
}

/** Parse a simple portfolio CSV (header + rows) into map points. */
export function parsePortfolioCsvToPoints(text: string): PortfolioPoint[] {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map((h) => h.trim().toLowerCase());
  const idx = (name: string) => headers.indexOf(name);
  const iLat = idx("lat");
  const iLon = idx("lon");
  if (iLat < 0 || iLon < 0) return [];
  const iId = idx("loc_id");
  const iHousing = idx("housing_class");
  const iTiv = idx("tiv_kes");
  const iHazSev = idx("hazard_score_severe");
  const iHazExt = idx("hazard_score_extreme");
  const iSyn = idx("synthetic");

  const out: PortfolioPoint[] = [];
  for (const line of lines.slice(1)) {
    const cols = line.split(",");
    const lat = Number(cols[iLat]);
    const lon = Number(cols[iLon]);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
    const hazard = Math.max(
      Number(cols[iHazExt] ?? 0) || 0,
      Number(cols[iHazSev] ?? 0) || 0,
    );
    const value = Number(cols[iTiv] ?? 0) || 0;
    out.push({
      id: iId >= 0 ? String(cols[iId] || `${lat}_${lon}`) : `${lat}_${lon}`,
      lat,
      lon,
      asset: "residential",
      housing: iHousing >= 0 ? String(cols[iHousing] || "unknown") : "unknown",
      value_kes: value,
      hazard_severe: hazard,
      insured: true,
      confidence: "high",
      synthetic: iSyn >= 0 ? /true|1|yes/i.test(String(cols[iSyn])) : false,
      depth: Math.min(3.2, hazard * 3.5),
      loss_kes: value * hazard * 0.35,
    });
  }
  return out;
}

/**
 * Center [lon, lat] from ingest bbox (min_lat, min_lon, max_lat, max_lon).
 */
export function centerFromBbox(
  bbox: number[] | null | undefined,
): [number, number] | null {
  if (!Array.isArray(bbox) || bbox.length < 4) return null;
  const [minLat, minLon, maxLat, maxLon] = bbox.map(Number);
  if (
    ![minLat, minLon, maxLat, maxLon].every((n) => Number.isFinite(n))
  ) {
    return null;
  }
  return [(minLon + maxLon) / 2, (minLat + maxLat) / 2];
}

/**
 * Last-resort hydrate for the shipped Kisumu *sample* CSV only — never for an
 * arbitrary Kisumu-labelled custom upload (would paint the wrong book).
 */
export async function tryHydrateDemoSamplePoints(opts: {
  place: string;
  portfolioName?: string;
  portfolioSource?: string;
  nRows?: number;
}): Promise<PortfolioPoint[]> {
  if (!/kisumu/i.test(opts.place)) return [];
  const name = `${opts.portfolioName ?? ""} ${opts.portfolioSource ?? ""}`;
  const looksLikeSample =
    /kisumu[-_ ]?demo|sample|demo kisumu/i.test(name) ||
    opts.nRows === 12;
  if (!looksLikeSample) return [];
  try {
    const res = await fetch("/samples/kisumu-demo-portfolio.csv", {
      cache: "force-cache",
    });
    if (!res.ok) return [];
    return parsePortfolioCsvToPoints(await res.text());
  } catch {
    return [];
  }
}
