"use client";

import Link from "next/link";
import {
  ArrowUpRight,
  Coins,
  Database,
  Network,
  Sparkles,
} from "lucide-react";
import { clsx } from "clsx";
import { MODULE_CARDS } from "@/lib/nav";

const icons = {
  data: Database,
  risk: Network,
  finance: Coins,
  decisions: Sparkles,
};

const styles = {
  data: {
    border: "border-data/35 hover:shadow-glow-blue",
    text: "text-data",
    soft: "bg-data-soft",
  },
  risk: {
    border: "border-risk/35 hover:shadow-glow-teal",
    text: "text-risk",
    soft: "bg-risk-soft",
  },
  finance: {
    border: "border-finance/35 hover:shadow-glow-gold",
    text: "text-finance",
    soft: "bg-finance-soft",
  },
  decide: {
    border: "border-decide/35 hover:shadow-glow-purple",
    text: "text-decide",
    soft: "bg-decide-soft",
  },
};

export function ModuleCards() {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {MODULE_CARDS.map((card, idx) => {
        const Icon = icons[card.id as keyof typeof icons];
        const s = styles[card.color];
        return (
          <Link
            key={card.id}
            href={card.href}
            className={clsx(
              "glass group relative rounded-2xl p-5 transition duration-300 hover:-translate-y-1",
              s.border,
            )}
            style={{ animationDelay: `${idx * 80}ms` }}
          >
            <div className="mb-4 flex items-start justify-between">
              <span
                className={clsx(
                  "grid h-11 w-11 place-items-center rounded-xl",
                  s.soft,
                  s.text,
                )}
              >
                <Icon className="h-5 w-5" />
              </span>
              <ArrowUpRight className="h-4 w-4 text-white/30 transition group-hover:text-white/80" />
            </div>
            <h3 className={clsx("font-display text-lg font-semibold", s.text)}>
              {card.title}
            </h3>
            <p className="mt-1 text-sm text-white/55">{card.tagline}</p>
            <ul className="mt-4 space-y-1.5">
              {card.items.map((item) => (
                <li key={item} className="text-sm text-white/75">
                  <span className={clsx("mr-2", s.text)}>•</span>
                  {item}
                </li>
              ))}
            </ul>
          </Link>
        );
      })}
    </div>
  );
}
