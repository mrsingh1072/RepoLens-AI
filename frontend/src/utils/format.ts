/** Small presentation helpers. */

/** Format large numbers compactly, e.g. 12500 -> "12.5k". */
export function formatCompact(value: number): string {
  return new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

/** Convenience: derive initials from a name for avatars. */
export function initials(name: string): string {
  return name
    .split(/[\s/_-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}
