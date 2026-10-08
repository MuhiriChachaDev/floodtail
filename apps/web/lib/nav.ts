export type NavItem = {
  href: string;
  label: string;
  blurb: string;
};

export type NavGroup = {
  id: "data" | "risk" | "finance" | "decisions" | "ai";
  label: string;
  color: "data" | "risk" | "finance" | "decide" | "accent";
  href: string;
  items: NavItem[];
};

export const NAV_GROUPS: NavGroup[] = [
  {
    id: "data",
    label: "Data",
    color: "data",
    href: "/data/start",
    items: [
      {
        href: "/data/start",
        label: "Start",
        blurb: "Bring in risk information",
      },
      {
        href: "/data/quality",
        label: "Data Quality & Location",
        blurb: "Can we trust where risks are?",
      },
      {
        href: "/data/portfolio",
        label: "Portfolio & Exposure",
        blurb: "What do we cover, and where?",
      },
    ],
  },
  {
    id: "risk",
    label: "Risk Modelling",
    color: "risk",
    href: "/risk/hazard",
    items: [
      {
        href: "/risk/hazard",
        label: "Flood Hazard",
        blurb: "Where is the flood?",
      },
      {
        href: "/risk/simulation",
        label: "Event Simulation",
        blurb: "What could happen?",
      },
      {
        href: "/risk/loss",
        label: "Loss Modelling",
        blurb: "What could it cost?",
      },
      {
        href: "/risk/analytics",
        label: "Risk Analytics",
        blurb: "What does the risk mean?",
      },
    ],
  },
  {
    id: "finance",
    label: "Finance",
    color: "finance",
    href: "/finance/treaty",
    items: [
      {
        href: "/finance/treaty",
        label: "Risk & Treaty",
        blurb: "How reinsurance responds",
      },
      {
        href: "/finance/pricing",
        label: "Pricing",
        blurb: "Supported price indication",
      },
      {
        href: "/finance/capital",
        label: "Capital & Portfolio",
        blurb: "Impact on capacity",
      },
    ],
  },
  {
    id: "decisions",
    label: "Decisions",
    color: "decide",
    href: "/decisions/lab",
    items: [
      {
        href: "/decisions/lab",
        label: "Decision Lab",
        blurb: "Compare options first",
      },
      {
        href: "/decisions/ai",
        label: "AI Intelligence",
        blurb: "What needs attention",
      },
      {
        href: "/decisions/review",
        label: "Human Review & Approval",
        blurb: "People make the call",
      },
      {
        href: "/decisions/output",
        label: "Decision Output",
        blurb: "Official record",
      },
    ],
  },
  {
    id: "ai",
    label: "AI",
    color: "accent",
    href: "/ai/control",
    items: [
      {
        href: "/ai/control",
        label: "AI Control",
        blurb: "What AI is doing now",
      },
      {
        href: "/ai/agents",
        label: "Agents & Workflows",
        blurb: "How the helpers work",
      },
      {
        href: "/ai/knowledge",
        label: "Knowledge & Evidence",
        blurb: "Where answers come from",
      },
      {
        href: "/ai/governance",
        label: "AI Governance",
        blurb: "What AI is allowed to do",
      },
    ],
  },
];

export const CROSS_CUTTING = [
  { href: "/controls/governance", label: "Governance" },
  { href: "/controls/security", label: "Security" },
  { href: "/controls/audit", label: "Audit" },
  { href: "/controls/model-registry", label: "Model Registry" },
  { href: "/controls/uncertainty", label: "Uncertainty" },
  { href: "/controls/validation", label: "Validation" },
  { href: "/controls/disaster-recovery", label: "Disaster Recovery" },
] as const;

export const MODULE_CARDS = [
  {
    id: "data",
    title: "Data",
    tagline: "Know what we have",
    color: "data" as const,
    href: "/data/start",
    items: ["Start", "Data Quality & Location", "Portfolio & Exposure"],
  },
  {
    id: "risk",
    title: "Risk Modelling",
    tagline: "Understand the flood",
    color: "risk" as const,
    href: "/risk/hazard",
    items: [
      "Flood Hazard",
      "Event Simulation",
      "Loss Modelling",
      "Risk Analytics",
    ],
  },
  {
    id: "finance",
    title: "Finance",
    tagline: "See the money impact",
    color: "finance" as const,
    href: "/finance/treaty",
    items: ["Risk & Treaty", "Pricing", "Capital & Portfolio"],
  },
  {
    id: "decisions",
    title: "Decisions",
    tagline: "Explore, then decide",
    color: "decide" as const,
    href: "/decisions/lab",
    items: [
      "Decision Lab",
      "AI Intelligence",
      "Human Review & Approval",
      "Decision Output",
    ],
  },
];
