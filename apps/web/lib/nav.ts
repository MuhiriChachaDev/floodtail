export type NavItem = {
  href: string;
  label: string;
  blurb: string;
};

export type NavGroup = {
  id: "data" | "finance" | "decisions" | "ai";
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
    ],
  },
  {
    id: "finance",
    label: "Finance",
    color: "finance",
    href: "/finance",
    items: [
      {
        href: "/finance",
        label: "Finance",
        blurb: "Treaty, pricing, and capital",
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
    items: ["Start"],
  },
  {
    id: "finance",
    title: "Finance",
    tagline: "See the money impact",
    color: "finance" as const,
    href: "/finance",
    items: ["Treaty", "Pricing", "Capital"],
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
