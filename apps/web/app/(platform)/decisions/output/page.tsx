"use client";

import { PageHeader } from "@/components/ui/PageHeader";
import { FlowSteps } from "@/components/ui/FlowSteps";
import { StatCard } from "@/components/ui/StatCard";

export default function DecisionOutputPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Decisions · Decision Output"
        title="Official record of what was decided"
        question="A material decision should not disappear into email — it becomes a FLOODTAIL record."
      />

      <FlowSteps
        accent="decide"
        steps={[
          { label: "Decision" },
          { label: "Official output" },
          { label: "Action" },
          { label: "Owner" },
          { label: "Completion" },
        ]}
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Decision ID" value="DEC-2026-014" tone="decide" />
        <StatCard label="Approver" value="Jane Doe" />
        <StatCard label="Date" value="8 Oct 2026" />
        <StatCard label="Status" value="Approved" tone="risk" />
      </div>

      <div className="glass rounded-2xl p-5 text-sm text-white/70">
        <h3 className="font-medium text-white">Snapshot</h3>
        <p className="mt-2">
          Approved technical pricing indication for Nairobi demo book with Eastlands
          monitoring. Evidence package linked to run SIM-1042, models v1.0, and
          portfolio version DEMO-600.
        </p>
        <p className="mt-4 text-xs text-white/40">
          Audit trail: hash-chained event written (demo). Next action owner: Portfolio
          Manager.
        </p>
      </div>
    </div>
  );
}
