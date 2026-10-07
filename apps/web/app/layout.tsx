import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "FLOODTAIL",
  description:
    "Nairobi urban flood CAT — frontend scaffold only. Use the FastAPI backend for modelling.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
