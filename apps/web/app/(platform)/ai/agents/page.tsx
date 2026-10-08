import { PageHeader } from "@/components/ui/PageHeader";
import { FlowSteps } from "@/components/ui/FlowSteps";
import { Notice } from "@/components/ui/Notice";

const AGENTS = [
  {
    name: "Data helper",
    job: "Ingest and check portfolio information",
    level: "L1 Analysis",
  },
  {
    name: "Hazard helper",
    job: "Watch flood signals and prepare overlays",
    level: "L1 Analysis",
  },
  {
    name: "Loss helper",
    job: "Call approved calculation tools",
    level: "L2 Recommendation",
  },
  {
    name: "Risk helper",
    job: "Summarise patterns and concentrations",
    level: "L2 Recommendation",
  },
  {
    name: "Decision helper",
    job: "Prepare cases for human approval",
    level: "L2 Recommendation",
  },
];

export default function AgentsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="AI · Agents & Workflows"
        title="How the helpers work together"
        question="Structured steps and tools — not free-for-all chat between agents."
      />

      <Notice>
        Helpers call approved tools. They do not invent catastrophe loss numbers or
        exercise unrestricted authority.
      </Notice>

      <FlowSteps
        accent="accent"
        steps={[
          { label: "Data" },
          { label: "Hazard" },
          { label: "Loss" },
          { label: "Risk" },
          { label: "Decision" },
        ]}
      />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {AGENTS.map((a) => (
          <div key={a.name} className="glass rounded-2xl p-4">
            <p className="font-medium text-accent">{a.name}</p>
            <p className="mt-2 text-sm text-white/70">{a.job}</p>
            <p className="mt-3 text-xs text-white/40">{a.level}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
