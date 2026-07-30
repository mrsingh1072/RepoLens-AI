# REPOLENS AI — Design Language

**Product:** RepoLens AI — AI Software Engineer for GitHub Repositories
**System name:** RepoLens AI
**Version:** 1.0

---

## 1. The Idea

A codebase is a geological object. It accumulates in layers — commits over commits,
modules over modules, decisions fossilized in files. This product excavates those
layers: it parses, indexes, and explains them.

The design language is built on that single metaphor:

> **Dark, warm rock. Light comes from above. Heat comes from within.**

- **Rock** — every surface is a stratum of warm graphite/basalt. Depth is expressed
  as luminance: deeper layers are darker, raised layers are lighter. No glassmorphism,
  no blur-everything, no floating neon.
- **Light from above** — every elevated surface carries a 1px top highlight, as if lit
  by a single overhead source. Shadows fall downward. This one rule makes depth
  physically coherent across the whole product.
- **Ember** — a single warm copper-orange accent, used like heat: sparingly, and only
  where the system is *alive* — the primary action, the active nav item, streaming
  tokens, indexing progress. When the machine works, it glows.

The interface must remain beautiful in grayscale. This is guaranteed by construction:
hierarchy is carried entirely by luminance steps and typography; color is annotation,
never structure.

**Deliberately avoided:** purple/blue AI gradients, glass cards, neon glows on
everything, oversized hero type, decorative borders, and any resemblance to the
Linear/Vercel/ChatGPT visual families. Warm-dark + copper + editorial grotesque is
its own identity.

---

## 2. Color Philosophy

### 2.1 Dark theme (default)

The base hue is warm (H ≈ 20–28°), never blue-gray. Warm darks read as material
(stone, charcoal); cool darks read as "software default."

| Token          | Value                | Role |
|----------------|----------------------|------|
| `bg`           | `hsl(20 14% 4.2%)`   | Bedrock. App background. |
| `surface`      | `hsl(22 12% 6.8%)`   | Stratum 1 — cards, panels, sidebar. |
| `raised`       | `hsl(24 10% 9.5%)`   | Stratum 2 — hover states, nested surfaces, inputs. |
| `overlay`      | `hsl(24 10% 12%)`    | Stratum 3 — popovers, dialogs, command palette. |
| `border`       | `hsl(26 10% 15.5%)`  | Hairlines between strata. |
| `border-strong`| `hsl(26 12% 22%)`    | Interactive/hover borders. |
| `text`         | `hsl(36 20% 93%)`    | Primary text — warm off-white, never pure white. |
| `text-2`       | `hsl(30 8% 64%)`     | Secondary text. |
| `text-3`       | `hsl(28 6% 45%)`     | Metadata, placeholders. |
| `ember`        | `hsl(24 92% 58%)`    | THE accent. Copper-orange. |
| `ember-bright` | `hsl(28 96% 66%)`    | Hover/active accent. |
| `on-ember`     | `hsl(20 50% 7%)`     | Text on ember fills — dark ink, not white. Premium detail. |
| `moss`         | `hsl(150 30% 52%)`   | Success, completed, healthy. |
| `gold`         | `hsl(44 85% 58%)`    | Warning, in-progress. |
| `rust`         | `hsl(8 68% 56%)`     | Error, destructive. |

**Chart palette** (earthy, luminance-separated so it survives grayscale):
ember `hsl(24 92% 58%)` → sand `hsl(38 55% 64%)` → moss `hsl(150 26% 50%)` →
clay `hsl(10 42% 52%)` → slate `hsl(215 14% 58%)` → stone `hsl(28 8% 42%)`.

### 2.2 Light theme

Warm paper, not clinical white: `bg hsl(40 30% 96.5%)`, surfaces pure white, ink text
`hsl(24 20% 10%)`, ember deepened to `hsl(22 88% 47%)` for contrast. All strata
relationships invert (raised surfaces are *lighter* toward white); the top-highlight
rule is dropped in light mode (paper needs no rim light).

### 2.3 Rules

1. Ember appears **at most twice** per viewport region: one primary action, one status.
2. Status colors are never fills at rest — they are dots, rings, and text. Fills are
   reserved for the moment of the event (a completed step flashes moss, then settles).
3. No gradients between hues. The only permitted gradients are luminance ramps of a
   single hue (e.g. ember → transparent for glows, bg → surface for vignettes).

---

## 3. Typography

Three voices, each with a reason:

| Family | Role | Why |
|--------|------|-----|
| **Bricolage Grotesque** | Display — hero, page titles, big numerals | A grotesque with genuine character (ink traps, tight apertures). It makes the product feel *authored*, not templated — and nobody's dashboard uses it. Used only above 22px, where its personality shows. |
| **Instrument Sans** | UI — everything else | Quiet, slightly warm grotesque with excellent rendering at 13–15px. Neutral enough to disappear behind content. Deliberately *not* Inter. |
| **IBM Plex Mono** | Code, data, labels | A mono with humanist warmth that matches the warm palette. Used for code, file paths, stats, and — as a signature — for **overline labels**. |

**Signature typographic device — the mono overline:** every section, card, and panel is
titled with an 11px IBM Plex Mono, uppercase, letter-spaced (`0.14em`), `text-3`-colored
label (e.g. `REPOSITORIES`, `INGESTION · STAGE 4/6`). It reads like an engineer's
annotation on a blueprint and instantly unifies every screen.

### Scale (desktop, 1rem = 16px)

| Step | Size / line | Family | Usage |
|------|-------------|--------|-------|
| display | 56–68 / 1.05, -2% tracking | Bricolage 640 | Landing hero only |
| h1 | 32 / 1.15 | Bricolage 600 | Page titles |
| h2 | 24 / 1.2 | Bricolage 600 | Section titles |
| h3 | 18 / 1.35 | Instrument 600 | Card titles |
| body | 14 / 1.6 | Instrument 450 | Default UI |
| body-lg | 16 / 1.65 | Instrument 450 | Chat prose, landing copy |
| small | 13 / 1.5 | Instrument 450 | Secondary UI |
| overline | 11 / 1 · caps · +14% | Plex Mono 500 | Section labels |
| code | 13 / 1.7 | Plex Mono 450 | Code blocks |
| stat | 28–40 / 1 | Bricolage 640, `tnum` | Big numbers |

Numbers everywhere use tabular figures (`font-variant-numeric: tabular-nums`) so
stats and tables never wobble while streaming.

---

## 4. Space, Grid, Radius

- **Grid:** 4px base. Component padding uses 8/12/16/20/24; page gutters 24 (desktop)
  /16 (mobile); card grids gap 16–20; landing section rhythm 96–128.
- **Layout:** app shell = fixed 264px sidebar (72px when collapsed) + fluid content
  capped at 1440px. Content columns on a 12-col grid, 24px gutter.
- **Radius scale:** 6 (chips, badges) · 10 (buttons, inputs) · 14 (cards) ·
  20 (dialogs, large panels) · pill (status dots, toggles). Nested radii obey
  `inner = outer − padding` so corners stay concentric.

---

## 5. Depth & Elevation

Five physical layers, always in this order (back → front):

1. **Bedrock** — `bg` + ambient texture (see §7.1)
2. **Strata surfaces** — cards/panels: `surface` fill, 1px `border`, top highlight
   `inset 0 1px 0 hsl(36 20% 93% / 0.04)`, shadow `0 1px 2px hsl(0 0% 0% / .4)`
3. **Raised** — hover lift: fill steps to `raised`, border to `border-strong`,
   shadow deepens `0 8px 24px -12px hsl(0 0% 0% / .6)`, translateY(-2px)
4. **Overlay** — popovers/dropdowns/command palette: `overlay` fill,
   `0 24px 64px -24px hsl(0 0% 0% / .7)`
5. **Modal** — dialogs above a `bg/70` scrim with 8px backdrop blur (the only blur
   in the system — used to push the world back, not to decorate)

Ember glow is elevation-adjacent: the primary CTA and live-progress elements carry
`0 8px 32px -8px ember/30`. Nothing else glows.

---

## 6. Motion — "Settle"

Everything in Strata moves like a mass coming to rest: fast start, soft landing,
no bounce beyond one gentle overshoot. Framer Motion springs only; no CSS ease-in-out
for anything the user touches.

### Spring presets (`src/lib/motion.ts`)

| Preset | Config | Use |
|--------|--------|-----|
| `snap` | stiffness 520, damping 32 | Buttons, toggles, chips |
| `settle` | stiffness 380, damping 30 | Cards, list items, panels |
| `drift` | stiffness 200, damping 26 | Page transitions, large surfaces |

### Rules

- **Enter:** fade + 10px rise (`drift`); lists stagger children 40ms, capped at 8 items.
- **Hover:** cards rise 2px and their spotlight fades in (§7.2); nav items slide a
  shared ember indicator (layoutId) rather than re-rendering highlights.
- **Press:** interactive elements compress to `scale(0.98)` with `snap`.
- **Page transitions:** old page fades down 6px, new page rises 10px. 200ms total.
- **Streaming:** chat tokens appear inside a container whose height animates with
  `settle`; a breathing ember caret marks the write head.
- **Indexing:** the pipeline is a vertical strata column — each stage is a layer that
  fills with an ember scan-line while active, then settles to moss. Progress numbers
  count up with springs.
- **Reduced motion:** `useReducedMotion()` + CSS media query collapse all movement to
  opacity-only, instantly. This is a hard requirement, not a nice-to-have.
- **Duration discipline:** nothing the user waits on exceeds 300ms; ambient loops
  (background drift, breathing) run 6–20s at opacity ≤ 0.1 so they're felt, not seen.

---

## 7. Signature Elements

The four devices that make Strata recognizably itself:

### 7.1 Ambient bedrock
The app background is not flat: a static SVG grain (2% opacity), a faint warm
vignette from the top, and one very slow ember thermal drifting near the active
region. Felt as material, never watched.

### 7.2 Ember spotlight
Interactive cards track the cursor with a 300px radial ember wash at ~6% opacity
(CSS custom properties updated on `pointermove`, GPU-cheap). The card border also
brightens along the cursor edge. This is the "cards respond to the cursor" moment —
subtle enough to feel like light, not an effect.

### 7.3 Blueprint corners
Hero surfaces and empty states carry small `+` tick marks at their corners, drawn in
`text-3` mono-weight strokes — the engineer's-drawing motif that pairs with the
mono overlines.

### 7.4 Live heat
Anything the AI is *doing right now* — streaming an answer, embedding chunks,
tracing a graph — is marked by breathing ember (opacity 0.6→1.0, 2s loop). Idle
things are stone-cold by rule, so the eye always finds the live process instantly.

---

## 8. Components

- **Buttons:** primary = ember fill with dark ink text + subtle glow; secondary =
  `raised` fill with border; ghost = text-only, `raised` wash on hover; destructive =
  rust outline that fills on hover. All compress on press. One primary per view.
- **Inputs:** `raised` fill, hairline border, no inset shadow. Focus = ember ring
  (2px, offset 2px) — the system-wide focus treatment for keyboard users.
- **Cards:** stratum 1 with spotlight; a mono overline, an h3, then content. Repo
  cards show a language-colored dot, mono stats row, and a status ring.
- **Badges/status:** pill, `raised` fill, colored dot + text; never full-color fills.
- **Tabs:** underline style, ember indicator slides with layoutId.
- **Dropdown/popover/command palette:** overlay stratum; palette is 640px, opens with
  `drift` scale 0.98→1, mono overline group headers, ⌘K everywhere.
- **Dialogs:** stratum 20px radius over scrim; enter = rise + fade with `drift`.
- **Toasts (sonner):** overlay stratum, left ember/moss/rust rail by intent, bottom-right.
- **Tables:** hairline rows only (no zebra), mono numerals right-aligned, header as
  mono overline.
- **Skeletons:** `raised` blocks with a slow warm shimmer sweep; layouts match the
  real content's exact geometry so loading never jumps.
- **Code blocks:** stratum 2 with a title bar (traffic dots + mono filename + copy),
  warm-tuned syntax theme (strings sand, keywords ember, functions moss, comments
  stone italic), line numbers in `text-3`.
- **Chat:** user messages = compact raised bubbles right-aligned; assistant = full-width
  prose on bedrock (no bubble) with an ember-dot avatar that breathes while streaming.
  Citations = numbered mono chips `[1]` inline, expandable source cards below.
- **File tree:** indent guides as hairlines, chevrons rotate with `snap`, active file
  carries an ember left rail, folders show mono file-counts.
- **Graphs (React Flow):** nodes are strata cards (kind-colored dot + mono label);
  edges warm-gray, animated ember dashes only for active/highlighted paths; selection
  raises the node and dims non-neighbors; background dots at 3% opacity.
- **Charts (Recharts):** earth palette (§2.1), hairline grid, no axis lines, warm
  tooltip on overlay stratum, areas draw in with organic ease on mount.

---

## 9. Page Personalities (one consistent language, distinct moods)

- **Landing** — *the specimen.* Editorial: huge Bricolage headline, mono annotations,
  a live "excavation" hero showing a repository being deconstructed into strata
  (files → symbols → graph), blueprint corners, generous 128px rhythm. No screenshots
  wall, no gradient hero.
- **Dashboard** — *mission control at rest.* Calm grid of repo cards with spotlight,
  mono stat row up top, everything cold unless something is indexing (that one card
  breathes ember).
- **Upload / Ingestion** — *the machine at work.* The most alive screen: URL/ZIP intake
  up top, then the six-stage strata column filling with ember scan-lines, streaming
  status text in mono, counters springing upward.
- **Repository Overview** — *the specimen table.* Three-pane: file tree, stats/languages,
  symbol detail. Feels like an instrument, dense but airy.
- **Chat** — *the conversation.* Quietest page: prose-width column, breathing ember dot,
  citations as artifacts.
- **Analytics** — *the lab report.* Chart grid with mono axis labels, heatmap in ember
  luminance ramp, duplicate/dead-code panels as findings with severity dots.
- **Architecture / Dependencies** — *the map room.* Near-fullscreen canvas, floating
  toolbar (overlay stratum), zoomable graph with dimming focus.
- **Settings** — *the utility closet.* Plain stacked sections, hairline-separated. Calm.
- **404 / errors** — *the missing stratum:* a strata column with one layer displaced,
  mono `ERR · 404` overline, one ghost action home.
- **Empty states** — blueprint corners + one-line explanation + one action. Never
  illustrations-for-illustration's-sake.

---

## 10. Accessibility

- Text contrast ≥ 4.5:1 on all strata (verified per token); `text-3` used only for
  non-essential metadata.
- Ember focus ring on every focusable element, always visible on `:focus-visible`.
- Full keyboard map: ⌘K palette, `g`+key page nav, `/` to search, Esc to close layers.
- `prefers-reduced-motion` collapses all motion to opacity (§6).
- Status never encoded by color alone — always dot + text label.
- Touch targets ≥ 40px on mobile; sidebar becomes a scrim-drawer, three-pane layouts
  become tab-switched panes (re-thought, not stacked).

---

## 11. Implementation Map

- Tokens: `frontend/src/index.css` (CSS custom properties) + `frontend/tailwind.config.js`
- Motion presets & variants: `frontend/src/lib/motion.ts`
- Signature components: `AmbientBackground`, `SpotlightCard`, `BlueprintCorners`,
  breathing-ember primitives in `frontend/src/components/common/`
- Fonts: Bricolage Grotesque, Instrument Sans, IBM Plex Mono via Google Fonts in
  `frontend/index.html`
- All existing routes, stores, API modules, and data flows are preserved; only the
  presentation layer is rebuilt.
