import type { Config } from "tailwindcss";

const v = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./src/**/*.{ts,tsx}"],
  darkMode: ["class"],
  theme: {
    borderRadius: { none: "0", DEFAULT: "2px", sm: "2px", full: "9999px" },
    extend: {
      colors: {
        canvas: v("canvas"),
        surface: v("surface"),
        sunken: v("sunken"),
        ink: { DEFAULT: v("ink"), 2: v("ink-2"), 3: v("ink-3") },
        line: { DEFAULT: v("line"), soft: v("line-soft") },
        brand: { DEFAULT: v("brand"), deep: v("brand-deep"), tint: v("brand-tint") },
        up: v("up"),
        down: v("down"),
        ref: v("ref"),
        ceil: v("ceil"),
        floor: v("floor"),
        strip: v("strip"),
      },
      fontFamily: {
        sans: ['"Be Vietnam Pro"', "system-ui", "Segoe UI", "sans-serif"],
      },
      fontSize: {
        "2xs": ["11px", "16px"],
        xs: ["12px", "16px"],
        sm: ["13px", "18px"],
        base: ["14px", "20px"],
        md: ["16px", "22px"],
        lg: ["20px", "26px"],
        xl: ["28px", "32px"],
        "2xl": ["40px", "44px"],
      },
    },
  },
  plugins: [],
} satisfies Config;
