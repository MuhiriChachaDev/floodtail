"use client";

const STEPS = [
  "Observed floods + claims",
  "Validation",
  "Calibration",
  "Model update",
];

export function LearningLoop() {
  return (
    <div className="glass rounded-2xl p-4 sm:p-5">
      <h3 className="section-title mb-1 text-base uppercase tracking-[0.12em]">
        Continuous learning
      </h3>
      <p className="mb-4 text-sm text-white/55">
        New facts improve the model only after checks — humans stay in control.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        {STEPS.map((step, i) => (
          <div key={step} className="flex items-center gap-2">
            <span className="rounded-full border border-risk/30 bg-risk-soft px-3 py-1.5 text-xs font-medium text-risk">
              {step}
            </span>
            {i < STEPS.length - 1 ? (
              <span className="text-white/30">→</span>
            ) : (
              <span className="text-white/30">↺</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
