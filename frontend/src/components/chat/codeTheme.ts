/**
 * Warm-tuned Prism theme for react-syntax-highlighter.
 * Strings sand, keywords ember, functions moss, comments stone italic —
 * the code palette matches the strata around it.
 */

const ink = "hsl(36 20% 90%)";
const stone = "hsl(28 6% 48%)";
const embr = "hsl(24 92% 62%)";
const sand = "hsl(38 55% 66%)";
const moss = "hsl(150 30% 58%)";
const slate = "hsl(215 16% 64%)";
const clay = "hsl(10 50% 62%)";

export const strataCodeTheme: Record<string, React.CSSProperties> = {
  'pre[class*="language-"]': {
    color: ink,
    background: "transparent",
    fontFamily: '"IBM Plex Mono", ui-monospace, monospace',
    fontSize: "13px",
    lineHeight: 1.7,
    whiteSpace: "pre",
    wordSpacing: "normal",
    wordBreak: "normal",
    tabSize: 2,
  },
  'code[class*="language-"]': {
    color: ink,
    background: "transparent",
    fontFamily: '"IBM Plex Mono", ui-monospace, monospace',
    fontSize: "13px",
    lineHeight: 1.7,
  },
  comment: { color: stone, fontStyle: "italic" },
  prolog: { color: stone },
  doctype: { color: stone },
  cdata: { color: stone },
  punctuation: { color: "hsl(30 8% 60%)" },
  property: { color: slate },
  tag: { color: clay },
  boolean: { color: embr },
  number: { color: embr },
  constant: { color: embr },
  symbol: { color: embr },
  deleted: { color: clay },
  selector: { color: sand },
  "attr-name": { color: sand },
  string: { color: sand },
  char: { color: sand },
  builtin: { color: moss },
  inserted: { color: moss },
  operator: { color: "hsl(30 8% 64%)" },
  entity: { color: sand },
  url: { color: slate },
  variable: { color: ink },
  atrule: { color: embr },
  "attr-value": { color: sand },
  function: { color: moss },
  "class-name": { color: slate },
  keyword: { color: embr },
  regex: { color: sand },
  important: { color: embr, fontWeight: "600" },
  bold: { fontWeight: "600" },
  italic: { fontStyle: "italic" },
};
