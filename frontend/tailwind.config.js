/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Console chrome - dark, slightly olive-tinted slate (not pure black)
        ink: "#0B1210",
        surface: "#121B18",
        "surface-raised": "#16211D",
        "surface-hover": "#1B2722",
        border: "#22302A",
        "border-soft": "#1A2520",
        // Semantic status colors (used for meaning, never decoration)
        signal: "#3DDC84", // live / agent responding / connected
        "signal-dim": "#2A9E5E",
        amber: "#F5A623", // waiting / pending / warning
        "amber-dim": "#B57A19",
        coral: "#FF5D5D", // needs human / alert / frustrated
        "coral-dim": "#C44343",
        // Text
        paper: "#EDEFEC",
        muted: "#8B9A93",
        faint: "#5A6862",
        // Per-tenant brand accents
        "tenant-gold": "#C8A24A",
        "tenant-gold-dim": "#8A6F33",
        "tenant-steel": "#3E7CB1",
        "tenant-steel-dim": "#2C5A82",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      borderRadius: {
        sm: "4px",
        DEFAULT: "6px",
        md: "8px",
        lg: "12px",
        xl: "16px",
      },
      animation: {
        "pulse-dot": "pulse-dot 1.6s ease-in-out infinite",
        "travel-dot": "travel-dot 2.4s ease-in-out infinite",
        "fade-in": "fade-in 0.2s ease-out",
        "slide-in": "slide-in 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
        blink: "blink 1.1s steps(1) infinite",
      },
      keyframes: {
        "pulse-dot": {
          "0%, 100%": { opacity: 1, transform: "scale(1)" },
          "50%": { opacity: 0.55, transform: "scale(0.85)" },
        },
        "travel-dot": {
          "0%": { left: "2%", opacity: 0 },
          "8%": { opacity: 1 },
          "92%": { opacity: 1 },
          "100%": { left: "98%", opacity: 0 },
        },
        "fade-in": {
          "0%": { opacity: 0, transform: "translateY(2px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        "slide-in": {
          "0%": { transform: "translateX(16px)", opacity: 0 },
          "100%": { transform: "translateX(0)", opacity: 1 },
        },
        blink: {
          "0%, 100%": { opacity: 0.25 },
          "50%": { opacity: 1 },
        },
      },
    },
  },
  plugins: [],
};
