import { PageHeader } from "@/components/ui/PageHeader";
import { Notice } from "@/components/ui/Notice";

const LEVELS = [
  { id: "L0", title: "Read only", detail: "View information" },
  { id: "L1", title: "Analysis", detail: "Compare and summarise" },
  { id: "L2", title: "Recommendation", detail: "Suggest actions with evidence" },
  {
    id: "L3",
    title: "Controlled action",
    detail: "Reversible steps only, with logging",
  },
  { id: "L4", title: "Human decision", detail: "People own consequences" },
];

export default function AiGovernancePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="AI · Governance"
        title="What is AI allowed to do?"
        question="AI controls operational workflow; humans control the consequences."
      />

      <Notice>
        Autonomy stops at recommendation for material pricing, capital, and binding
        decisions. Approval gates remain mandatory.
      </Notice>

      <div className="grid gap-3 md:grid-cols-5">
        {LEVELS.map((l) => (
          <div
            key={l.id}
            className="glass rounded-2xl border border-accent/20 p-4 text-center"
          >
            <p className="font-display text-xl text-accent">{l.id}</p>
            <p className="mt-2 text-sm font-medium text-white">{l.title}</p>
            <p className="mt-1 text-xs text-white/50">{l.detail}</p>
          </div>
        ))}
      </div>

      <div className="glass rounded-2xl p-5 text-sm text-white/65">
        Controls include tool access lists, model version pins, prompt safety checks,
        audit logging, and change management before any helper gains new powers.
      </div>
    </div>
  );
}
