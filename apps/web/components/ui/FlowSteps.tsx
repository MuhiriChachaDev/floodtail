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
        <li key={step.label} className="flex min-w-0 max-w-full items-center gap-2">
          <div className={clsx("min-w-0 rounded-xl border px-2.5 py-2 sm:px-3", color)}>
            <p className="text-xs font-semibold sm:text-sm">{step.label}</p>
            {step.detail ? (
              <p className="break-words text-[11px] opacity-80 sm:text-xs">{step.detail}</p>
            ) : null}
          </div>
          {i < steps.length - 1 ? (
            <span className="hidden shrink-0 text-white/30 sm:inline" aria-hidden>
              →
            </span>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
