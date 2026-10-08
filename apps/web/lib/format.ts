export function formatKes(value: number, compact = true): string {
  if (!Number.isFinite(value)) return "—";
  if (!compact) {
    return `KES ${value.toLocaleString("en-KE")}`;
  }
  const abs = Math.abs(value);
  if (abs >= 1_000_000_000) {
    return `KES ${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (abs >= 1_000_000) {
    return `KES ${(value / 1_000_000).toFixed(1)}M`;
  }
  if (abs >= 1_000) {
    return `KES ${(value / 1_000).toFixed(0)}K`;
  }
  return `KES ${value.toFixed(0)}`;
}

export function classLabel(housing: string): string {
  const map: Record<string, string> = {
    formal_masonry: "Solid building",
    semi_permanent: "Semi-permanent home",
    informal_iron_sheet: "Iron-sheet home",
    apartment: "Apartment",
    warehouse: "Warehouse",
    industrial: "Industrial site",
  };
  return map[housing] ?? housing.replaceAll("_", " ");
}

export function assetEmoji(asset: string): string {
  switch (asset) {
    case "commercial":
      return "🏢";
    case "industrial":
      return "🏭";
    case "hotel":
      return "🏨";
    case "hospital":
      return "🏥";
    case "warehouse":
      return "🏬";
    default:
      return "🏠";
  }
}
