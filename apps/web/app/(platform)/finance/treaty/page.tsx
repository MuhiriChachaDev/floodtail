"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { FlowSteps } from "@/components/ui/FlowSteps";
import { StatCard } from "@/components/ui/StatCard";
import { Notice } from "@/components/ui/Notice";
import { formatKes } from "@/lib/format";

export default function TreatyPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Finance · Risk & Treaty"
        title="How does reinsurance respond?"
        question="Follow modelled losses through the reinsurance structure to Kenya Re’s net view."
      />

      <Notice>
        This screen is illustrative for the hackathon. Full treaty structuring is
        out of scope for the Nairobi prototype — figures show the intended flow.
      </Notice>

      <FlowSteps
        accent="finance"
        steps={[
          { label: "Gross loss", detail: formatKes(268_400_000) },
          { label: "Retention" },
          { label: "Attachment" },
          { label: "Limit" },
          { label: "Recovery" },
          { label: "Net Kenya Re" },
        ]}
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Gross loss" value={formatKes(268_400_000)} tone="finance" />
        <StatCard label="Estimated recovery" value={formatKes(96_000_000)} tone="risk" />
        <StatCard label="Net Kenya Re view" value={formatKes(172_400_000)} tone="decide" />
        <StatCard label="Treaty source" value="Demo XL" hint="Traceable reference" />
      </div>

      <div className="glass rounded-2xl p-5 text-sm text-white/65">
        <p className="font-medium text-white">Why this matters</p>
        <p className="mt-2">
          Underwriters need to see not only total damage, but how much stays with
          Kenya Re after the reinsurance response — and be able to open the treaty
          terms that produced that answer.
        </p>
      </div>
    </div>
  );
}
