"use client";

import { useState } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Notice } from "@/components/ui/Notice";
import { formatKes } from "@/lib/format";
import { DEMO } from "@/lib/demo";

export default function ReviewPage() {
  const [decision, setDecision] = useState<"pending" | "approved" | "rejected" | "returned">(
    "pending",
  );
  const [reason, setReason] = useState("");

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Decisions · Human Review & Approval"
        title="People make the final call"
        question="Review the proposal, the AI recommendation, and the impacts — then approve, reject, or send back."
      />

      <Notice>
        AI recommends. The human decides. Material outcomes stay under human
        authority.
      </Notice>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="glass space-y-4 rounded-2xl p-5">
          <h2 className="section-title text-base">Proposed decision</h2>
          <p className="text-sm text-white/75">
            Accept technical pricing indication of{" "}
            <strong className="text-white">
              {formatKes(DEMO.risk.expectedYearlyLoss * 1.25)}
            </strong>{" "}
            for the Nairobi demo book, subject to Eastlands monitoring.
          </p>
          <ul className="space-y-2 text-sm text-white/60">
            <li>• AI recommendation: Approve with monitoring</li>
            <li>• Risk impact: Expected yearly loss unchanged at base</li>
            <li>• Capital impact: Within illustrative headroom</li>
            <li>• Model versions: hazard v1.0 · vulnerability v1.0</li>
            <li>• Assumptions: synthetic portfolio · proxy hazard</li>
          </ul>
        </div>

        <div className="glass space-y-4 rounded-2xl p-5">
          <h2 className="section-title text-base">Your decision</h2>
          <textarea
            className="input-field min-h-[120px]"
            placeholder="Mandatory reason for the audit trail…"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-primary !bg-risk !text-night-950"
              onClick={() => reason.trim() && setDecision("approved")}
            >
              Approve
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => reason.trim() && setDecision("returned")}
            >
              Send back
            </button>
            <button
              type="button"
              className="btn-ghost !border-rose-400/40 !text-rose-200"
              onClick={() => reason.trim() && setDecision("rejected")}
            >
              Reject
            </button>
          </div>
          {decision !== "pending" ? (
            <p className="text-sm text-accent">
              Recorded as <strong>{decision}</strong>. Continue to Decision Output
              for the official record.
            </p>
          ) : (
            <p className="text-xs text-white/40">A reason is required before action.</p>
          )}
        </div>
      </div>
    </div>
  );
}
