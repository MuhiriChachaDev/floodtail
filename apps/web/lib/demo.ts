/** Demo figures for the Nairobi prototype — clearly labelled as synthetic. */
export const DEMO = {
  portfolio: {
    valueCovered: 63_635_075_000,
    properties: 600,
    activeWatched: 197,
    pendingReview: 3,
    counties: ["Nairobi"],
    synthetic: true,
    updatedAgo: "Updated 4 minutes ago",
  },
  risk: {
    expectedYearlyLoss: 128_870_000,
    severeFloodLoss: 227_600_000,
    rareFloodLoss: 312_400_000,
    floodStatus: "Watch — rainfall rising in eastern Nairobi",
    lastObservation: "Last observation 42 minutes ago",
    modelRun: "Model run completed 10:32",
  },
  attention: [
    {
      id: "att-1",
      title: "3 properties need location confirmation",
      detail: "Addresses could not be placed with high confidence.",
      href: "/data/quality",
      tone: "warn" as const,
    },
    {
      id: "att-2",
      title: "Eastlands concentration rising",
      detail: "More covered value sits in known flood-prone areas.",
      href: "/risk/analytics",
      tone: "info" as const,
    },
    {
      id: "att-3",
      title: "Decision waiting for approval",
      detail: "Pricing indication for Nairobi book needs a human sign-off.",
      href: "/decisions/review",
      tone: "action" as const,
    },
  ],
  aiSummary:
    "Flood watch is elevated in eastern Nairobi. Portfolio coverage looks complete for 597 of 600 properties. One pricing case is ready for human review. Numbers below come from the deterministic loss engine — AI only explains and flags attention.",
  freshness: {
    portfolio: "Updated 4 minutes ago",
    weather: "Last observation 42 minutes ago",
    model: "Model run completed 10:32",
  },
};

export const EP_CURVE = [
  { label: "Common", rarity: "Often", loss: 42_000_000 },
  { label: "Occasional", rarity: "Every few years", loss: 78_000_000 },
  { label: "Moderate", rarity: "Uncommon", loss: 128_870_000 },
  { label: "Severe", rarity: "Rare", loss: 227_600_000 },
  { label: "Extreme", rarity: "Very rare", loss: 312_400_000 },
];

export const COUNTY_EXPOSURE = [
  { name: "Eastlands", share: 28, value: 17_800_000_000 },
  { name: "Westlands", share: 18, value: 11_400_000_000 },
  { name: "Central", share: 16, value: 10_100_000_000 },
  { name: "South", share: 14, value: 8_900_000_000 },
  { name: "North", share: 12, value: 7_600_000_000 },
  { name: "Other", share: 12, value: 7_835_075_000 },
];

export const LOSS_CHAIN = [
  { step: "Flood depth", value: "Mapped per property" },
  { step: "Damage share", value: "From building type + depth" },
  { step: "Gross damage", value: "Damage share × covered value" },
  { step: "Insurance terms", value: "Applied where available" },
  { step: "Net loss", value: "Final figure for Kenya Re view" },
];
