/*
 * Chart palette — earthy hues separated by luminance, never by saturation
 * alone, so every chart remains legible in grayscale.
 */

const LANGUAGE_COLORS: Record<string, string> = {
  python: "hsl(150 26% 50%)",
  typescript: "hsl(215 14% 58%)",
  javascript: "hsl(44 85% 58%)",
  tsx: "hsl(215 14% 70%)",
  jsx: "hsl(44 70% 68%)",
  go: "hsl(150 26% 40%)",
  rust: "hsl(24 92% 58%)",
  java: "hsl(10 42% 52%)",
  unknown: "hsl(28 8% 42%)",
};

export function languageColor(language: string): string {
  return LANGUAGE_COLORS[language.toLowerCase()] ?? LANGUAGE_COLORS.unknown;
}

export const COMPLEXITY_COLORS = {
  low: "hsl(150 30% 52%)",
  medium: "hsl(44 85% 58%)",
  high: "hsl(8 68% 56%)",
} as const;

export const CHART_THEME = {
  grid: "hsl(26 10% 15.5%)",
  axis: "hsl(28 6% 45%)",
  tooltipBg: "hsl(24 10% 12%)",
  tooltipBorder: "hsl(26 10% 15.5%)",
  ember: "hsl(24 92% 58%)",
};

/** Ordered series palette: ember → sand → moss → clay → slate → stone. */
export const SERIES_COLORS = [
  "hsl(24 92% 58%)",
  "hsl(38 55% 64%)",
  "hsl(150 26% 50%)",
  "hsl(10 42% 52%)",
  "hsl(215 14% 58%)",
  "hsl(28 8% 42%)",
];
