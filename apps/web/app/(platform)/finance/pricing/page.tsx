"use client";

import { useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { Notice } from "@/components/ui/Notice";
import { formatKes } from "@/lib/format";
import { DEMO } from "@/lib/demo";

export default function PricingPage() {
  const [load, setLoad] = useState(1.25);
  const technical = DEMO.risk.expectedYearlyLoss * load;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Finance · Pricing"
        title="What price is supported by the risk?"
        question="Combine expected loss, catastrophe risk, and approved factors into a technical indication — not a final price."
      />

      <Notice>
        FLOODTAIL supports pricing. It does not become the final pricing authority.
        A person must still approve.
      </Notice>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="glass space-y-4 rounded-2xl p-5">
          <h2 className="section-title text-base">Building blocks</h2>
          <ul className="space-y-2 text-sm text-white/70">
            <li>• Expected loss: {formatKes(DEMO.risk.expectedYearlyLoss)}</li>
            <li>• Catastrophe risk load (adjustable below)</li>
            <li>• Exposure and treaty view</li>
            <li>• Approved pricing methodology (demo)</li>
          </ul>
          <label className="block text-xs text-white/55">
            Risk load × {load.toFixed(2)}
            <input
              type="range"
              min={1}
              max={1.8}
              step={0.05}
              value={load}
              onChange={(e) => setLoad(Number(e.target.value))}
              className="mt-2 w-full accent-finance"
            />
          </label>
        </div>
        <div className="grid gap-3">
          <StatCard
            label="Technical price indication"
            value={formatKes(technical)}
            tone="finance"
            status="Needs human approval"
            hint="Not a binding quote"
          />
          <StatCard
            label="Compared to expected loss"
            value={`+${Math.round((load - 1) * 100)}% load`}
            tone="neutral"
          />
        </div>
      </div>
    </div>
  );
}
