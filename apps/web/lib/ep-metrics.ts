import type {
  DataLabels,
  EPPoint,
  FinancialView,
  MetricsPayload,
  PricingIndication,
  TierLoss,
} from "./api";
import { DEMO, EP_CURVE } from "./demo";

export type EpDisplayPoint = {
  tier: string;
  label: string;
  rarity: string;
  return_period: number;
  aep: number;
  loss_kes: number;
  mean_damage_ratio?: number | null;
  /** Highlight for “rains too much” / tail scenarios */
  isHeavyRain?: boolean;
};

const TIER_META: Record<
  string,
  { label: string; rarity: string; isHeavyRain?: boolean }
> = {
  common: { label: "Common", rarity: "Often (1-in-5)" },
  occasional: { label: "Occasional", rarity: "Every few years (1-in-20)" },
  moderate: { label: "Moderate", rarity: "Uncommon (1-in-50)" },
  severe: {
    label: "Severe",
    rarity: "Rare — rains too much (1-in-100)",
    isHeavyRain: true,
  },
  extreme: {
    label: "Extreme",
    rarity: "Very rare — extreme rainfall (1-in-250)",
    isHeavyRain: true,
  },
};

const RP_TO_TIER: Record<number, string> = {
  5: "common",
  20: "occasional",
  50: "moderate",
  100: "severe",
  250: "extreme",
};

function titleCase(tier: string): string {
  return tier.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function metaFor(tier: string, rp: number) {
  const key = tier || RP_TO_TIER[rp] || "";
  return (
    TIER_META[key] ?? {
      label: titleCase(key || `RP${rp}`),
      rarity: `1-in-${rp}`,
      isHeavyRain: rp >= 100,
    }
  );
}

function fromTierLosses(tiers: TierLoss[]): EpDisplayPoint[] {
  return [...tiers]
    .sort((a, b) => a.return_period - b.return_period)
    .map((t) => {
      const m = metaFor(t.tier, t.return_period);
      return {
        tier: t.tier,
        label: m.label,
        rarity: m.rarity,
        return_period: t.return_period,
        aep: t.aep,
        loss_kes: t.loss_kes,
        mean_damage_ratio: t.mean_damage_ratio,
        isHeavyRain: m.isHeavyRain,
      };
    });
}

function fromEpCurve(curve: EPPoint[]): EpDisplayPoint[] {
  return [...curve]
    .sort((a, b) => a.return_period - b.return_period)
    .map((p) => {
      const rp = Math.round(p.return_period);
      const tier = RP_TO_TIER[rp] || `rp${rp}`;
      const m = metaFor(tier, rp);
      return {
        tier,
        label: m.label,
        rarity: m.rarity,
        return_period: rp,
        aep: p.aep,
        loss_kes: p.loss_kes,
        isHeavyRain: m.isHeavyRain,
      };
    });
}

function fromDemo(): EpDisplayPoint[] {
  return EP_CURVE.map((p, i) => {
    const rps = [5, 20, 50, 100, 250];
    const tiers = ["common", "occasional", "moderate", "severe", "extreme"];
    const rp = rps[i] ?? 5;
    const tier = tiers[i] ?? "common";
    const m = metaFor(tier, rp);
    return {
      tier,
      label: p.label,
      rarity: m.rarity,
      return_period: rp,
      aep: 1 / rp,
      loss_kes: p.loss,
      isHeavyRain: m.isHeavyRain,
    };
  });
}

export type ResolvedEpMetrics = {
  points: EpDisplayPoint[];
  aalKes: number;
  totalTivKes: number;
  nHouses: number;
  locationLabel: string;
  capitalBand: MetricsPayload["capital_band"];
  financial: FinancialView | null;
  pricing: PricingIndication | null;
  dataLabels: DataLabels | null;
  assumptionsVersion: string | null;
  hazardModel: string | null;
  vulnModel: string | null;
  source: "run" | "demo";
  runId?: string;
};

const DEMO_LABELS: DataLabels = {
  synthetic_exposure: true,
  proxy_hazard: true,
  assumed_rp: true,
  d_max_m: 4,
  notes: [
    "Demo fallback — run a portfolio test for live ground-up + net EP figures.",
  ],
};

/** Build chart-ready EP points from a live run, or fall back to labelled demo. */
export function resolveEpMetrics(
  metrics: MetricsPayload | null | undefined,
  opts?: { runId?: string; locationLabel?: string },
): ResolvedEpMetrics {
  const tiers = metrics?.tier_losses;
  const curve = metrics?.ep_curve;
  const hasLive =
    (Array.isArray(tiers) && tiers.length > 0) ||
    (Array.isArray(curve) && curve.length > 0);

  if (hasLive && metrics) {
    const points =
      tiers && tiers.length > 0
        ? fromTierLosses(tiers)
        : fromEpCurve(curve as EPPoint[]);
    return {
      points,
      aalKes: Number(metrics.aal_kes ?? 0),
      totalTivKes: Number(metrics.total_tiv_kes ?? 0),
      nHouses: Number(metrics.n_insured_houses ?? metrics.n_locations ?? 0),
      locationLabel:
        opts?.locationLabel ||
        String(metrics.location_label || "Portfolio"),
      capitalBand: metrics.capital_band ?? null,
      financial: metrics.financial ?? null,
      pricing: metrics.pricing ?? null,
      dataLabels: metrics.data_labels ?? null,
      assumptionsVersion: metrics.assumptions_version ?? null,
      hazardModel: metrics.hazard_model_version ?? null,
      vulnModel: metrics.vuln_model_version ?? null,
      source: "run",
      runId: opts?.runId || metrics.run_id,
    };
  }

  return {
    points: fromDemo(),
    aalKes: DEMO.risk.expectedYearlyLoss,
    totalTivKes: DEMO.portfolio.valueCovered,
    nHouses: DEMO.portfolio.properties,
    locationLabel: opts?.locationLabel || "Nairobi County (demo)",
    capitalBand: {
      floor_kes: DEMO.risk.severeFloodLoss,
      central_kes: DEMO.risk.expectedYearlyLoss,
      ceiling_kes: DEMO.risk.rareFloodLoss,
      currency: "KES",
    },
    financial: null,
    pricing: null,
    dataLabels: DEMO_LABELS,
    assumptionsVersion: "nairobi-pluvial-v1",
    hazardModel: null,
    vulnModel: null,
    source: "demo",
  };
}

/** Pick the reference tier layer (default severe / RP100) for treaty flow display. */
export function referenceLayer(financial: FinancialView | null | undefined) {
  if (!financial?.layered_by_tier?.length) return null;
  const pref = financial.reference_tier || "severe";
  return (
    financial.layered_by_tier.find((l) => l.tier === pref) ||
    financial.layered_by_tier.find((l) => l.return_period === 100) ||
    financial.layered_by_tier[financial.layered_by_tier.length - 1]
  );
}

export function lossAtRp(
  points: EpDisplayPoint[],
  rp: number,
): number | null {
  const hit = points.find((p) => p.return_period === rp);
  return hit ? hit.loss_kes : null;
}

export function heavyRainLosses(points: EpDisplayPoint[]) {
  return {
    severe: lossAtRp(points, 100) ?? points.find((p) => p.tier === "severe")?.loss_kes ?? null,
    extreme:
      lossAtRp(points, 250) ??
      points.find((p) => p.tier === "extreme")?.loss_kes ??
      null,
  };
}

export function formatAepPct(aep: number): string {
  if (!Number.isFinite(aep) || aep <= 0) return "—";
  const pct = aep * 100;
  if (pct >= 1) return `${pct.toFixed(0)}%`;
  if (pct >= 0.1) return `${pct.toFixed(1)}%`;
  return `${pct.toFixed(2)}%`;
}
