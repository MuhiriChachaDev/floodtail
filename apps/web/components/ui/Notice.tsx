import { Info } from "lucide-react";
import type { ReactNode } from "react";

export function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-3 rounded-2xl border border-accent/25 bg-accent-soft px-4 py-3 text-sm text-white/75">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
      <div>{children}</div>
    </div>
  );
}
