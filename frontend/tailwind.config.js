/** @type {import('tailwindcss').Config} */
// STRATA design system — warm graphite strata, single ember accent,
// depth as luminance, light from above. Tokens live in src/index.css.
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1440px" },
    },
    extend: {
      fontFamily: {
        inter: ['"Inter"', "ui-sans-serif", "system-ui", "sans-serif"],
        display: ['"Bricolage Grotesque"', "ui-sans-serif", "system-ui", "sans-serif"],
        sans: ['"Instrument Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      colors: {
        // Strata (back → front)
        bedrock: "hsl(var(--background))",
        surface: "hsl(var(--surface))",
        raised: "hsl(var(--raised))",
        overlay: "hsl(var(--overlay))",
        // Ink
        ink: {
          DEFAULT: "hsl(var(--foreground))",
          2: "hsl(var(--text-2))",
          3: "hsl(var(--text-3))",
        },
        // Hairlines
        edge: {
          DEFAULT: "hsl(var(--border))",
          strong: "hsl(var(--border-strong))",
        },
        // Heat + status
        ember: {
          DEFAULT: "hsl(var(--ember))",
          bright: "hsl(var(--ember-bright))",
        },
        "on-ember": "hsl(var(--on-ember))",
        moss: "hsl(var(--moss))",
        gold: "hsl(var(--gold))",
        rust: "hsl(var(--rust))",

        // shadcn compatibility
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        // 6 · 10 · 14 · 20 scale
        sm: "6px",
        md: "10px",
        lg: "14px",
        xl: "20px",
      },
      boxShadow: {
        // Depth rules: light from above; shadows fall down.
        stratum: "inset 0 1px 0 0 rgb(255 255 255 / 0.05), 0 1px 2px hsl(0 0% 0% / 0.4)",
        raised: "inset 0 1px 0 0 rgb(255 255 255 / 0.05), 0 8px 24px -12px hsl(0 0% 0% / 0.6)",
        overlay: "0 24px 64px -24px hsl(0 0% 0% / 0.7)",
        "ember-glow": "0 8px 32px -8px hsl(var(--ember) / 0.35)",
      },
      keyframes: {
        // Live heat: anything the AI is doing right now breathes.
        breathe: {
          "0%, 100%": { opacity: "0.55" },
          "50%": { opacity: "1" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        // Ember scan-line for active ingestion stages.
        scan: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(200%)" },
        },
        // Slow ambient thermal drift in the bedrock.
        thermal: {
          "0%, 100%": { transform: "translate(0, 0) scale(1)" },
          "50%": { transform: "translate(-4%, 3%) scale(1.06)" },
        },
        "caret-blink": {
          "0%, 70%, 100%": { opacity: "1" },
          "20%, 50%": { opacity: "0" },
        },
      },
      animation: {
        breathe: "breathe 2s ease-in-out infinite",
        shimmer: "shimmer 1.8s infinite",
        scan: "scan 1.6s ease-in-out infinite",
        thermal: "thermal 18s ease-in-out infinite",
        "caret-blink": "caret-blink 1.1s steps(1) infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
