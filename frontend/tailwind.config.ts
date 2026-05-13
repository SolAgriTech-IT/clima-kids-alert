import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          green: "#1B4332",
          mint: "#2D6A4F",
          cream: "#FAF9F6",
          alert: "#D90429",
          warn: "#F77F00",
        },
      },
    },
  },
  plugins: [],
};

export default config;
