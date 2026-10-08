import type { ReactNode } from "react";
import { Notice } from "@/components/ui/Notice";

type Props = {
  /** Short title for what this screen is */
  title?: string;
  children: ReactNode;
};

/** Clear badge so stakeholders don't treat UX shells as live model output. */
export function PrototypeBadge({
  title = "Prototype / illustrative screen",
  children,
}: Props) {
  return (
    <Notice>
      <p className="font-medium text-amber-100/90">{title}</p>
      <div className="mt-1 text-white/70">{children}</div>
    </Notice>
  );
}
