import type { CSSProperties, ReactNode } from "react";
import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

export const metadata: Metadata = {
  title: "FLOODTAIL · Kenya Re Flood Risk Intelligence",
  description:
    "Kenya-focused flood-risk intelligence for Kenya Re — data, hazard, loss, finance, and human decisions in one place.",
};

const fontVars = {
  ["--font-display" as string]: '"Outfit", system-ui, sans-serif',
  ["--font-body" as string]: '"Source Sans 3", system-ui, sans-serif',
} as CSSProperties;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700&family=Source+Sans+3:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body
        className="min-h-screen bg-night-950 font-body text-white antialiased"
        style={fontVars}
      >
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
