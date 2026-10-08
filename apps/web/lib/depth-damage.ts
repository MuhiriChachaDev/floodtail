import type { MetricsPayload } from "./api";

/** Mirror of packages/cat_core/vulnerability_prior.JRC_ADAPTED_CURVES — demo fallback. */
export const PRIOR_DEPTH_DAMAGE_CURVES: Record<
  string,
  Array<{ depth_m: number; damage_ratio: number }>
> = {
  informal_iron_sheet: [
    { depth_m: 0, damage_ratio: 0 },
    { depth_m: 0.2, damage_ratio: 0.15 },
    { depth_m: 0.5, damage_ratio: 0.35 },
    { depth_m: 1.0, damage_ratio: 0.6 },
    { depth_m: 1.5, damage_ratio: 0.78 },
    { depth_m: 2.0, damage_ratio: 0.9 },
    { depth_m: 3.0, damage_ratio: 0.98 },
    { depth_m: 4.0, damage_ratio: 1.0 },
  ],
  semi_permanent: [
    { depth_m: 0, damage_ratio: 0 },
    { depth_m: 0.2, damage_ratio: 0.1 },
    { depth_m: 0.5, damage_ratio: 0.28 },
    { depth_m: 1.0, damage_ratio: 0.5 },
    { depth_m: 1.5, damage_ratio: 0.68 },
    { depth_m: 2.0, damage_ratio: 0.82 },
    { depth_m: 3.0, damage_ratio: 0.94 },
    { depth_m: 4.0, damage_ratio: 1.0 },
  ],
  permanent_masonry: [
    { depth_m: 0, damage_ratio: 0 },
    { depth_m: 0.2, damage_ratio: 0.06 },
    { depth_m: 0.5, damage_ratio: 0.18 },
    { depth_m: 1.0, damage_ratio: 0.38 },
    { depth_m: 1.5, damage_ratio: 0.55 },
    { depth_m: 2.0, damage_ratio: 0.7 },
    { depth_m: 3.0, damage_ratio: 0.88 },
    { depth_m: 4.0, damage_ratio: 0.98 },
  ],
  concrete_rcc: [
    { depth_m: 0, damage_ratio: 0 },
    { depth_m: 0.2, damage_ratio: 0.03 },
    { depth_m: 0.5, damage_ratio: 0.12 },
    { depth_m: 1.0, damage_ratio: 0.28 },
    { depth_m: 1.5, damage_ratio: 0.42 },
    { depth_m: 2.0, damage_ratio: 0.55 },
    { depth_m: 3.0, damage_ratio: 0.75 },
    { depth_m: 4.0, damage_ratio: 0.9 },
  ],
};

export const HOUSING_CURVE_COLORS: Record<string, string> = {
  informal_iron_sheet: "#f87171",
  semi_permanent: "#f5b942",
  permanent_masonry: "#3b9eff",
  concrete_rcc: "#2dd4bf",
};

export type DepthDamageTierPoint = {
  tier: string;
  return_period: number;
  mean_depth_m: number;
  mean_damage_ratio: number;
  p90_depth_m?: number;
  p90_damage_ratio?: number;
};

export type DepthDamageHousingPoint = {
  housing_class: string;
  n: number;
  reference_tier?: string;
  mean_depth_m: number;
  mean_damage_ratio: number;
};

export type ResolvedDepthDamage = {
  curves: Record<string, Array<{ depth_m: number; damage_ratio: number }>>;
  byTier: DepthDamageTierPoint[];
  byHousing: DepthDamageHousingPoint[];
  dMaxM: number;
  source: "run" | "demo";
};

const DEMO_BY_TIER: DepthDamageTierPoint[] = [
  { tier: "common", return_period: 5, mean_depth_m: 0.35, mean_damage_ratio: 0.08 },
  { tier: "occasional", return_period: 20, mean_depth_m: 0.7, mean_damage_ratio: 0.18 },
  { tier: "moderate", return_period: 50, mean_depth_m: 1.2, mean_damage_ratio: 0.32 },
  { tier: "severe", return_period: 100, mean_depth_m: 1.9, mean_damage_ratio: 0.48 },
  { tier: "extreme", return_period: 250, mean_depth_m: 2.8, mean_damage_ratio: 0.62 },
];

export function resolveDepthDamage(
  metrics: MetricsPayload | null | undefined,
): ResolvedDepthDamage {
  const summary = metrics?.depth_damage_summary;
  const curves =
    (summary?.prior_curves as ResolvedDepthDamage["curves"] | undefined) ||
    PRIOR_DEPTH_DAMAGE_CURVES;
  const byTier = Array.isArray(summary?.by_tier)
    ? (summary!.by_tier as DepthDamageTierPoint[])
    : [];
  const byHousing = Array.isArray(summary?.by_housing_class)
    ? (summary!.by_housing_class as DepthDamageHousingPoint[])
    : [];

  if (byTier.length > 0) {
    return {
      curves,
      byTier: [...byTier].sort((a, b) => a.return_period - b.return_period),
      byHousing,
      dMaxM: Number(summary?.d_max_m ?? 4),
      source: "run",
    };
  }

  // Fallback: approximate depth from mean damage on EP tiers if summary missing
  const tiers = metrics?.tier_losses;
  if (tiers && tiers.length > 0) {
    const dMax = 4;
    const approx = [...tiers]
      .sort((a, b) => a.return_period - b.return_period)
      .map((t) => {
        const dr = Number(t.mean_damage_ratio ?? 0);
        // Invert average of permanent_masonry-ish curve for a rough depth
        const depth = Math.min(dMax, Math.max(0, dr * dMax * 1.15));
        return {
          tier: t.tier,
          return_period: t.return_period,
          mean_depth_m: Math.round(depth * 1000) / 1000,
          mean_damage_ratio: dr,
        };
      });
    return {
      curves: PRIOR_DEPTH_DAMAGE_CURVES,
      byTier: approx,
      byHousing: [],
      dMaxM: dMax,
      source: "run",
    };
  }

  return {
    curves: PRIOR_DEPTH_DAMAGE_CURVES,
    byTier: DEMO_BY_TIER,
    byHousing: [],
    dMaxM: 4,
    source: "demo",
  };
}

export function housingCurveLabel(housing: string): string {
  const map: Record<string, string> = {
    informal_iron_sheet: "Iron-sheet (most vulnerable)",
    semi_permanent: "Semi-permanent",
    permanent_masonry: "Permanent masonry",
    concrete_rcc: "Concrete RCC (most resistant)",
  };
  return map[housing] ?? housing.replaceAll("_", " ");
}
