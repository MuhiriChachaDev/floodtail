import { notFound } from "next/navigation";
import { PageHeader } from "@/components/ui/PageHeader";
import { CROSS_CUTTING } from "@/lib/nav";

const COPY: Record<
  string,
  { title: string; question: string; body: string[] }
> = {
  governance: {
    title: "Governance",
    question: "Who is allowed to change what, and under which rules?",
    body: [
      "Role-based access decides who can run models, approve decisions, or change settings.",
      "Appetite rules and mandatory human reasons apply before material actions.",
      "Cross-cutting — kept out of the main journey so the path stays simple.",
    ],
  },
  security: {
    title: "Security",
    question: "How is the Kenya Re environment protected?",
    body: [
      "Sign-in establishes identity, role, and permissions before analysis opens.",
      "Sensitive fields can be masked; prompts to AI are filtered.",
      "Demo login is local-only — production would use Kenya Re identity services.",
    ],
  },
  audit: {
    title: "Audit",
    question: "Can we reconstruct what happened?",
    body: [
      "Key events are written to a hash-chained audit trail.",
      "Decisions require a human reason that stays with the record.",
      "Ask “where did this number come from?” and follow run → model → portfolio → data.",
    ],
  },
  "model-registry": {
    title: "Model Registry",
    question: "Which calculation models are approved to run?",
    body: [
      "Hazard and vulnerability models are pinned by version and integrity check.",
      "A hash mismatch fails the prediction stages — no silent swaps.",
      "Cards document intended use and known limits.",
    ],
  },
  uncertainty: {
    title: "Uncertainty",
    question: "Where are we less sure?",
    body: [
      "Hazard is a proxy, not measured flood depth everywhere.",
      "Some neighbourhoods flood for drainage reasons the proxy cannot see.",
      "The interface should show freshness and confidence, not fake real-time certainty.",
    ],
  },
  validation: {
    title: "Validation",
    question: "Have outputs been checked against known facts?",
    body: [
      "Hotspot checks compare the proxy to government-named flood areas.",
      "AI narratives are validated so invented numbers are rejected.",
      "Continuous learning only updates models after controlled validation.",
    ],
  },
  "disaster-recovery": {
    title: "Disaster Recovery",
    question: "What happens if the platform is disrupted?",
    body: [
      "Critical services should recover with clear runbooks.",
      "Audit and decision records must remain readable offline from backups.",
      "This page is a control surface — details belong in Kenya Re ops playbooks.",
    ],
  },
};

export function generateStaticParams() {
  return CROSS_CUTTING.map((c) => ({
    slug: c.href.replace("/controls/", ""),
  }));
}

export default function ControlPage({
  params,
}: {
  params: { slug: string };
}) {
  const page = COPY[params.slug];
  if (!page) notFound();

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Cross-cutting"
        title={page.title}
        question={page.question}
      />
      <div className="glass space-y-3 rounded-2xl p-6 text-sm text-white/70">
        {page.body.map((p) => (
          <p key={p}>{p}</p>
        ))}
      </div>
    </div>
  );
}
