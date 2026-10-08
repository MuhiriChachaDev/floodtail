"use client";

import Link from "next/link";
import { Hero } from "@/components/home/Hero";
import { ModuleCards } from "@/components/home/ModuleCards";
import { PortfolioGlance } from "@/components/home/PortfolioGlance";
import { LearningLoop } from "@/components/home/LearningLoop";
import { FloodMap } from "@/components/map/FloodMap";
import { useLivePortfolioView } from "@/lib/live-view";

export default function HomePage() {
  const view = useLivePortfolioView();

  return (
    <div className="space-y-8">
      <Hero place={view.place} hasLiveBook={view.hasRun} />

      <section id="command-center" className="scroll-mt-24 space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="font-display text-xl font-semibold text-white">
              Command Centre
            </h2>
            <p className="text-sm text-white/55">
              Current flood status, portfolio health, and where to go next.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="chip text-amber-200">{view.statusChip}</span>
            <span className="chip">{view.weatherChip}</span>
          </div>
        </div>

        <ModuleCards />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.35fr_1fr]">
        <FloodMap mode="overview" />
        <div className="space-y-4">
          <PortfolioGlance />
          <div className="glass rounded-2xl p-5">
            <h3 className="section-title mb-2 text-base uppercase tracking-[0.12em]">
              FLOODTAIL AI summary
            </h3>
            <p className="text-sm leading-relaxed text-white/70">
              {view.aiSummary}
            </p>
            <div className="mt-4 space-y-2">
              {view.attention.map((item) => (
                <Link
                  key={item.id}
                  href={item.href}
                  className="block rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 transition hover:border-accent/40 hover:bg-accent/5"
                >
                  <p className="text-sm font-medium text-white">{item.title}</p>
                  <p className="text-xs text-white/50">{item.detail}</p>
                </Link>
              ))}
            </div>
          </div>
          <LearningLoop />
        </div>
      </section>
    </div>
  );
}
