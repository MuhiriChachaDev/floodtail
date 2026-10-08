"use client";

import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { Notice } from "@/components/ui/Notice";

const SIGNALS = [
  {
    title: "Eastlands concentration rising",
    happened: "More covered value sits in known flood-prone neighbourhoods.",
    why: "A severe flood there would hit many risks at once.",
    evidence: "Portfolio concentration chart · hotspot overlay",
    href: "/data/portfolio",
  },
  {
    title: "Three locations need confirmation",
    happened: "Geocoding could not place three properties with high confidence.",
    why: "Loss for those sites may be misplaced on the map.",
    evidence: "Data quality checks · intake log",
    href: "/data/quality",
  },
  {
    title: "Pricing case ready for review",
    happened: "Technical indication prepared for the Nairobi demo book.",
    why: "Needs an authorised person before it becomes a decision.",
    evidence: "Pricing worksheet · model versions v1.0",
    href: "/decisions/review",
  },
];

export default function AiIntelligencePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Decisions · AI Intelligence"
        title="What deserves attention?"
        question="FLOODTAIL AI connects signals and points to evidence — it does not replace judgement."
      />

      <Notice>
        Every important AI statement should answer: What happened? Why does it
        matter? What evidence supports it? What needs a human look?
      </Notice>

      <div className="space-y-4">
        {SIGNALS.map((s) => (
          <article key={s.title} className="glass rounded-2xl p-5">
            <h3 className="font-display text-lg text-decide">{s.title}</h3>
            <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-white/45">What happened</dt>
                <dd className="mt-1 text-white/80">{s.happened}</dd>
              </div>
              <div>
                <dt className="text-white/45">Why it matters</dt>
                <dd className="mt-1 text-white/80">{s.why}</dd>
              </div>
              <div>
                <dt className="text-white/45">Evidence</dt>
                <dd className="mt-1 text-white/80">{s.evidence}</dd>
              </div>
              <div className="flex items-end">
                <Link href={s.href} className="btn-ghost !text-xs">
                  Open evidence →
                </Link>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </div>
  );
}
