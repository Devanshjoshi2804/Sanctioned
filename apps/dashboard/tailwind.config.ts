import type { Config } from "tailwindcss";

// Design tokens for the "underwriting terminal" direction — an institutional
// decision instrument, not a marketing page. The decision triad (approve/refer/
// reject) is the only colour that earns saturation; everything else stays quiet.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#15171c",
        slate: "#5b6472",
        paper: "#eef1f4",
        surface: "#ffffff",
        line: "#d8dee6",
        accent: "#2f4b7c",
        approve: "#1f7a55",
        refer: "#b4791a",
        reject: "#b23b3b",
      },
      fontFamily: {
        display: ["var(--font-archivo)", "system-ui", "sans-serif"],
        body: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-plex-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 0 0 #d8dee6, 0 1px 3px 0 rgba(21,23,28,0.04)",
      },
      borderRadius: {
        sm: "3px",
      },
    },
  },
  plugins: [],
};

export default config;
