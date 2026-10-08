"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { FlowSteps } from "@/components/ui/FlowSteps";
import { StatCard } from "@/components/ui/StatCard";
import { FloodMap } from "@/components/map/FloodMap";
import { LOSS_CHAIN, DEMO } from "@/lib/demo";
import { formatKes } from "@/lib/format";

export default function LossPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Risk Modelling · Loss Modelling"
        title="What could it cost?"
        question="Turn flood impact into money figures you can follow step by step."
      />

      <FlowSteps
        accent="risk"
        steps={LOSS_CHAIN.map((s) => ({
          label: s.step,
          detail: s.value,
        }))}
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Gross damage"
          value={formatKes(268_400_000)}
          tone="risk"
          status="From damage engine"
        />
        <StatCard
          label="After insurance terms"
          value={formatKes(DEMO.risk.severeFloodLoss)}
          tone="finance"
        />
        <StatCard label="Hazard model" value="v1.0" hint="Pinned version" />
        <StatCard label="Vulnerability model" value="v1.0" hint="Pinned version" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <FloodMap mode="loss" title="Loss intensity map" showTimeline={false} />
        <div className="glass rounded-2xl p-5">
          <h3 className="section-title mb-3 text-base">Where this number came from</h3>
          <ol className="space-y-3 text-sm text-white/70">
            <li>1. Flood depth estimated per property from the hazard model.</li>
            <li>2. Damage share predicted from depth + building type.</li>
            <li>3. Loss = damage share × covered value.</li>
            <li>4. Results tagged with run ID, model versions, and data labels.</li>
          </ol>
          <p className="mt-4 text-xs text-white/40">
            AI does not invent these figures. The numerical engine calculates them;
            AI only explains.
          </p>
        </div>
      </div>
    </div>
  );
}
