"use client";

import { useEffect, useState } from "react";

/** Flood progression: start → rising → severe → wipeout → loop */
const FRAMES = [
  { src: "/login/flood-01-start.jpg", label: "Flood beginning" },
  { src: "/login/flood-02-rising.jpg", label: "Waters rising" },
  { src: "/login/flood-03-severe.jpg", label: "Severe inundation" },
  { src: "/login/flood-04-overwhelm.jpg", label: "City overwhelmed" },
] as const;

const HOLD_MS = 4500;
const FADE_MS = 1200;

export function FloodBackdrop() {
  const [index, setIndex] = useState(0);
  const [reduceMotion, setReduceMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReduceMotion(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  useEffect(() => {
    if (reduceMotion) return;
    const id = window.setInterval(() => {
      setIndex((i) => (i + 1) % FRAMES.length);
    }, HOLD_MS);
    return () => window.clearInterval(id);
  }, [reduceMotion]);

  useEffect(() => {
    for (const frame of FRAMES) {
      const img = new Image();
      img.src = frame.src;
    }
  }, []);

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      {FRAMES.map((frame, i) => {
        const active = reduceMotion ? i === 0 : i === index;
        return (
          <div
            key={frame.src}
            className="absolute inset-0 bg-cover bg-center will-change-[opacity,transform]"
            style={{
              backgroundImage: `url('${frame.src}')`,
              opacity: active ? 0.68 : 0,
              transform: active ? "scale(1.05)" : "scale(1)",
              transition: reduceMotion
                ? "none"
                : `opacity ${FADE_MS}ms ease-in-out, transform ${HOLD_MS}ms ease-out`,
            }}
            role="img"
            aria-label={frame.label}
          />
        );
      })}

      <div className="absolute inset-0 bg-gradient-to-br from-night-950/72 via-night-950/58 to-night-900/68" />
      <div className="absolute inset-0 bg-gradient-to-t from-night-950/90 via-transparent to-night-950/30" />

      {!reduceMotion ? (
        <div className="absolute bottom-4 left-1/2 z-[1] flex -translate-x-1/2 gap-1.5 sm:bottom-6">
          {FRAMES.map((frame, i) => (
            <span
              key={frame.src}
              className={`h-1 rounded-full transition-all duration-500 ${
                i === index ? "w-6 bg-accent/80" : "w-1.5 bg-white/30"
              }`}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
