import type { ReactNode } from "react";
import { Suspense } from "react";

export default function LoginLayout({ children }: { children: ReactNode }) {
  return <Suspense fallback={<div className="grid min-h-screen place-items-center text-white/50">Loading…</div>}>{children}</Suspense>;
}
