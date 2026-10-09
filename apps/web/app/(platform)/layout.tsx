import type { ReactNode } from "react";
import { AssistantChat } from "@/components/ai/AssistantChat";
import { AuthGate } from "@/components/layout/AuthGate";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export default function PlatformLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGate>
      <div className="flex min-h-screen flex-col">
        <Header />
        <main className="page-shell flex-1 py-6 sm:py-8">{children}</main>
        <Footer />
        <AssistantChat />
      </div>
    </AuthGate>
  );
}
