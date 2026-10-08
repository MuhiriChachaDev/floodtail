import { clsx } from "clsx";

type Step = { label: string; detail?: string };

export function FlowSteps({
  steps,
  accent = "accent",
}: {
  steps: Step[];
  accent?: "data" | "risk" | "finance" | "decide" | "accent";
}) {
  const color = {
    data: "border-data/40 bg-data-soft text-data",
    risk: "border-risk/40 bg-risk-soft text-risk",
    finance: "border-finance/40 bg-finance-soft text-finance",
    decide: "border-decide/40 bg-decide-soft text-decide",
    accent: "border-accent/40 bg-accent-soft text-accent",
  }[accent];

  return (
    <ol className="flex flex-wrap items-stretch gap-2">
      {steps.map((step, i) => (
        <li key={step.label} className="flex items-center gap-2">
          <div className={clsx("rounded-xl border px-3 py-2", color)}>
            <p className="text-sm font-semibold">{step.label}</p>
            {step.detail ? (
              <p className="text-xs opacity-80">{step.detail}</p>
            ) : null}
          </div>
          {i < steps.length - 1 ? (
            <span className="text-white/30">→</span>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
