import { PageHeader } from "@/components/ui/PageHeader";
import { Notice } from "@/components/ui/Notice";
import { FlowSteps } from "@/components/ui/FlowSteps";

export default function AboutPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="About"
        title="What FLOODTAIL is for"
        question="Help Kenya Re move from scattered flood information to one clear, traceable view of the Nairobi book."
      />

      <Notice>
        This prototype follows the Nairobi Urban Flood Challenge: build a working
        path from flood hazard → damage → covered properties → financial loss,
        and show results that an underwriter can understand without jargon.
      </Notice>

      <div className="glass rounded-2xl p-6">
        <h2 className="section-title mb-4">The journey</h2>
        <FlowSteps
          steps={[
            { label: "Know what we have" },
            { label: "Understand the flood" },
            { label: "Simulate the event" },
            { label: "Calculate loss" },
            { label: "Measure the risk" },
            { label: "Understand finance" },
            { label: "Explore decisions" },
            { label: "AI assists" },
            { label: "Human decides" },
            { label: "Record the outcome" },
          ]}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="glass rounded-2xl p-5">
          <h3 className="font-display text-lg text-white">Who it helps</h3>
          <ul className="mt-3 space-y-2 text-sm text-white/65">
            <li>• Underwriters & risk analysts needing a defensible loss view</li>
            <li>• Portfolio managers watching concentration in flood areas</li>
            <li>• Approvers who must sign off before action</li>
          </ul>
        </div>
        <div className="glass rounded-2xl p-5">
          <h3 className="font-display text-lg text-white">Honest limits</h3>
          <ul className="mt-3 space-y-2 text-sm text-white/65">
            <li>• Exposure is synthetic (demo buildings, not a real client book)</li>
            <li>• Hazard layers are a proxy, not measured flood gauges</li>
            <li>• AI explains and recommends — it does not invent loss numbers</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
