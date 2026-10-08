import type { ReactNode } from "react";

type Props = {
  eyebrow?: string;
  title: string;
  question: string;
  children?: ReactNode;
};

export function PageHeader({ eyebrow, title, question, children }: Props) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl animate-fade-up">
        {eyebrow ? (
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.18em] text-accent">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="font-display text-2xl font-semibold text-white sm:text-3xl">
          {title}
        </h1>
        <p className="mt-2 text-base text-white/70">{question}</p>
      </div>
      {children ? <div className="animate-fade-up">{children}</div> : null}
    </div>
  );
}
