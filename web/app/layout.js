import "./globals.css";

export const metadata = {
  title: "Kenya Re — Flood Risk Intelligence Platform",
  description: "Enterprise Catastrophe Reinsurance Analytics, Stochastic Hazard Modeling & Multi-Agent Underwriting Decision Engine for Kenya",
  icons: {
    icon: "/favicon.ico",
  },
};

export const viewport = {
  themeColor: "#03070f",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
