import { PageHeader } from "@/components/ui/PageHeader";
import { FlowSteps } from "@/components/ui/FlowSteps";

const SOURCES = [
  {
    title: "Nairobi demo portfolio",
    status: "Verified synthetic",
    detail: "600 buildings · labelled synthetic=True",
  },
  {
    title: "Flood hotspot list",
    status: "Government-named areas",
    detail: "24 geocoded neighbourhoods from the starter kit",
  },
  {
    title: "Hazard proxy rasters",
    status: "Proxy — not gauges",
    detail: "Terrain + stream distance susceptibility tiers",
  },
  {
    title: "Model run output",
    status: "Computed",
    detail: "Pinned hazard & vulnerability models v1.0",
  },
];

export default function KnowledgePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="AI · Knowledge & Evidence"
        title="Where answers come from"
        question="Every AI statement should be traceable to a source, record, and field."
      />

      <FlowSteps
        accent="accent"
        steps={[
          { label: "AI statement" },
          { label: "Evidence" },
          { label: "Source" },
          { label: "Document / record" },
          { label: "Page / field" },
        ]}
      />

      <div className="grid gap-3 md:grid-cols-2">
        {SOURCES.map((s) => (
          <div key={s.title} className="glass rounded-2xl p-4">
            <div className="flex items-start justify-between gap-3">
              <p className="font-medium text-white">{s.title}</p>
              <span className="chip">{s.status}</span>
            </div>
            <p className="mt-2 text-sm text-white/55">{s.detail}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
