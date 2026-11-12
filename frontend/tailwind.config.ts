import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#050812",
        panel: "#0b1220",
        line: "#1d2b40",
        electric: "#38bdf8"
      },
      boxShadow: {
        glow: "0 0 42px rgba(14, 165, 233, 0.12)"
      }
    }
  },
  plugins: []
};

export default config;
