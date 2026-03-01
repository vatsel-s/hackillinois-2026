import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["system-ui", "sans-serif"],
        mono: ["ui-monospace", "monospace"],
      },
      colors: {
        surface: {
          DEFAULT: "hsl(var(--surface))",
          muted: "hsl(var(--surface-muted))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          muted: "hsl(var(--accent-muted))",
        },
      },
    },
  },
  plugins: [],
};
export default config;
