/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        night: {
          950: "#03070f",
          900: "#06101c",
          800: "#0b1a2c",
          700: "#12263d",
          600: "#1a3552",
        },
        data: {
          DEFAULT: "#3b9eff",
          soft: "rgba(59,158,255,0.15)",
          glow: "rgba(59,158,255,0.45)",
        },
        risk: {
          DEFAULT: "#2dd4bf",
          soft: "rgba(45,212,191,0.15)",
          glow: "rgba(45,212,191,0.45)",
        },
        finance: {
          DEFAULT: "#f5b942",
          soft: "rgba(245,185,66,0.15)",
          glow: "rgba(245,185,66,0.45)",
        },
        decide: {
          DEFAULT: "#c084fc",
          soft: "rgba(192,132,252,0.15)",
          glow: "rgba(192,132,252,0.45)",
        },
        accent: {
          DEFAULT: "#22d3ee",
          soft: "rgba(34,211,238,0.15)",
          glow: "rgba(34,211,238,0.5)",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        body: ["var(--font-body)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        glass: "0 8px 32px rgba(0,0,0,0.35)",
        glow: "0 0 24px rgba(34,211,238,0.35)",
        "glow-blue": "0 0 20px rgba(59,158,255,0.35)",
        "glow-teal": "0 0 20px rgba(45,212,191,0.35)",
        "glow-gold": "0 0 20px rgba(245,185,66,0.35)",
        "glow-purple": "0 0 20px rgba(192,132,252,0.35)",
      },
      backgroundImage: {
        "hero-wash":
          "linear-gradient(180deg, rgba(3,7,15,0.35) 0%, rgba(3,7,15,0.72) 55%, #03070f 100%)",
        "panel-grad":
          "linear-gradient(145deg, rgba(18,38,61,0.85), rgba(6,16,28,0.92))",
      },
      animation: {
        "fade-up": "fadeUp 0.6s ease-out both",
        "pulse-soft": "pulseSoft 2.4s ease-in-out infinite",
        "slide-in": "slideIn 0.35s ease-out both",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
        slideIn: {
          "0%": { opacity: "0", transform: "translateY(-6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
