"use client";

import Link from "next/link";
import { MapPin } from "lucide-react";
import { KenyaReLogo } from "@/components/brand/KenyaReLogo";

type Props = {
  place?: string;
  hasLiveBook?: boolean;
};

export function Hero({ place, hasLiveBook }: Props) {
  const placeLabel = place?.trim() || "Kenya";
  const coverLine = hasLiveBook
    ? `One place to see what Kenya Re covers in ${placeLabel}, how floods could affect it, what it might cost, and what a person should decide next.`
    : "One place to see what Kenya Re covers, how floods could affect the book, what it might cost, and what a person should decide next.";

  return (
    <section className="relative overflow-hidden rounded-2xl border border-white/10 sm:rounded-3xl">
      <div
        className="absolute inset-0 bg-cover bg-center"
        style={{
          backgroundImage: "url('/hero/flooded-city.jpg')",
        }}
      />
      <div className="absolute inset-0 bg-hero-wash" />
      <div className="absolute inset-0 bg-gradient-to-r from-night-950/85 via-night-950/55 to-transparent" />

      <div className="relative grid gap-6 px-4 py-10 sm:gap-8 sm:px-10 sm:py-12 lg:grid-cols-[1.2fr_0.8fr] lg:py-16">
        <div className="animate-fade-up max-w-xl">
          <KenyaReLogo variant="white" heightClass="h-9 sm:h-12" priority />
          <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.22em] text-accent sm:mt-5 sm:text-xs">
            Smarter insights. Stronger decisions.
          </p>
          <h1 className="mt-3 font-display text-2xl font-semibold leading-tight text-white sm:text-4xl lg:text-[2.6rem]">
            Flood Risk Intelligence Platform
          </h1>
          <p className="mt-4 max-w-lg text-sm text-white/70 sm:text-base">{coverLine}</p>
          <Link href="#command-center" className="btn-primary mt-6 w-full sm:mt-7 sm:w-auto">
            Open Command Center →
          </Link>
        </div>

        <div className="animate-fade-up relative flex flex-col justify-end gap-4 lg:items-end">
          <div className="inline-flex items-center gap-2 self-start rounded-full border border-white/15 bg-night-950/55 px-3 py-1.5 text-sm text-white/80 backdrop-blur lg:self-end">
            <MapPin className="h-4 w-4 text-accent" />
            {hasLiveBook ? `${placeLabel}, Kenya` : "Kenya"}
          </div>
          <div className="glass max-w-sm rounded-2xl p-5 text-sm leading-relaxed text-white/75">
            <p className="font-medium text-white">
              Real risk. Real data. Real decisions.
            </p>
            <p className="mt-2">
              Built for underwriters and risk teams who need a clear flood view
              of the book — not a pile of separate spreadsheets and models.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
