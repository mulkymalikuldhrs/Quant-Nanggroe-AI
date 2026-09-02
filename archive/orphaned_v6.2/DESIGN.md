# Design System: QNA Causal Engine Dashboard

## 1. Visual Theme & Atmosphere

A dense, command-center interface designed for institutional-grade quantitative trading. The atmosphere is **clinical precision meets tactical edge** — like a war room in a systematic hedge fund. Dark charcoal canvases anchor a cockpit-dense information hierarchy, where every pixel communicates data, not decoration.

- **Density:** 8/10 (Cockpit Dense) — Data-rich panels, compact metrics, information-dense tables
- **Variance:** 6/10 (Offset Asymmetric) — Purposeful asymmetry in card sizing, correlation matrices biased to the left, metrics skewed to emphasis
- **Motion:** 5/10 (Fluid CSS) — Restrained transitions, spring-physics micro-interactions, never cinematic or distracting

The palette is **Deep Charcoal + Tactical Gold** — warm luxury meets cold data. One singular accent (Gold) for all primary interactive elements. Cyan reserved exclusively for positive financial metrics (correlation, Sharpe, P&L).

## 2. Color Palette & Roles

- **Deep Charcoal** (#1A1D20) — Primary background surface. Not pure black, not navy. A warm, deep slate.
- **Midnight Navy** (#0F172A) — Card, container, and header fill. One step lighter than the canvas for clear elevation.
- **Tactical Gold** (#D9A441) — **Single accent.** CTAs, active states, focus rings, warning badges, section dividers. Warm, saturated but under 80%. All interactive elements use this.
- **Cyber Cyan** (#00D1C7) — **Semantic positive.** Exclusively for positive financial metrics (mean correlation, Sharpe ratio, P&L gain). Never used for buttons or interactive elements.
- **Card Surface** (#1E2230) — Elevated card backgrounds, slightly lighter than Midnight Navy.
- **Text Primary** (#E8E8EA) — High-contrast body and headline text.
- **Text Secondary** (#8888AA) — Descriptions, metadata, table headers, muted labels.
- **Border Structure** (#2A2E40) — 1px structural dividers, card borders, table row separators.
- **Crimson Alert** (#FF4757) — **Semantic negative.** Exclusively for danger states, drawdown breaches, kill-switch activation, error badges.

**BANNED:** Pure black (#000000), neon purple/blue gradients, oversaturated accents, warm/cool gray fluctuation.

## 3. Typography Rules

- **Display / Headlines:** `Geist` — Track-tight (-0.02em), weight-driven hierarchy (700→600→500). Never scream via size alone. Maximum 1.3rem for section headers.
- **Body:** `Geist` — Relaxed leading (1.6), 65ch max-width on prose. Secondary color (#8888AA) for metadata.
- **Mono:** `JetBrains Mono` — All numerical data, metrics, prices, correlations, timestamps, z-scores. Required in all dashboard cards.
- **Scale:** `clamp(0.75rem, 1.5vw, 0.9rem)` for body content. Metric values at `1.8rem`. Section titles at `0.9rem` uppercase.
- **BANNED:** Inter, system-font stack for premium contexts. Serif fonts anywhere (dashboard constraint). All-caps body text.

## 4. Component Stylings

### Cards
- **Shape:** Generously rounded corners (10px / 0.625rem). No sharp edges.
- **Fill:** Card Surface (#1E2230) with 1px Border Structure (#2A2E40) stroke.
- **Shadow:** None — rely on background elevation, not drop shadows. In high-density layouts, cards use border-top dividers instead of full card containers.
- **Header:** Uppercase, letter-spaced (1px), Text Secondary color. Small (0.75rem).
- **Usage:** Only when elevation communicates hierarchy. Metric cards get full card treatment. Tables get border-top dividers only.

### Metric Values
- **Font:** JetBrains Mono, 1.8rem, font-weight 700, letter-spacing -0.5px
- **Positive:** Cyber Cyan (#00D1C7)
- **Negative:** Crimson Alert (#FF4757)
- **Neutral:** Tactical Gold (#D9A441)
- **Label:** 0.75rem, Text Secondary, 4px gap above value

### Buttons / CTAs
- **Primary:** Tactical Gold fill, dark text (Deep Charcoal). Border-radius 6px. Padding 6px 16px.
- **Secondary / Ghost:** Transparent fill, 1px Border Structure stroke, Text Secondary color.
- **Hover:** Primary → darken fill. Ghost → Border and text become Cyber Cyan.
- **Active:** Tactile `scale(0.97)` transform. 200ms ease-out transition.
- **BANNED:** Neon outer glows, custom mouse cursors, gradient fills.

### Tables / Data Grids
- **Rows:** No alternating background (reduces noise). Bottom border only (rgba(42,46,64,0.5)).
- **Hover:** Subtle cyan tint (rgba(0,209,199,0.04)).
- **Headers:** Text Secondary, 500 weight, border-bottom 1px #2A2E40.
- **Cells:** JetBrains Mono for all numeric columns. Right-aligned numerics.
- **Compact:** 6px 8px padding. 0.8rem font size.

### Badges / Status Indicators
- **Running/Active:** Cyan tint fill, Cyan text. `rgba(0,209,199,0.15)` + #00D1C7.
- **Warning:** Gold tint fill, Gold text. `rgba(217,164,65,0.15)` + #D9A441.
- **Danger/Error:** Crimson tint fill, Crimson text. `rgba(255,71,87,0.15)` + #FF4757.
- **Neutral/Inactive:** Gray tint fill, Gray text. `rgba(136,136,170,0.15)` + #8888AA.

### Inputs / Selects
- **Label:** Above input. 0.75rem, Text Secondary.
- **Field:** Midnight Navy fill, 1px Border Structure stroke, Text Primary value.
- **Focus:** Border becomes Tactical Gold. No glow. 0.2s transition.
- **Range Slider:** Midnight Navy track, Tactical Gold thumb. Full width.
- **BANNED:** Floating labels, placeholder-as-label patterns.

### Correlation Matrix
- **Cell size:** 32×24px. JetBrains Mono 0.6rem.
- **Positive corr:** Cyan gradient (light→dark: `rgba(0,209,199,0.25)` → `rgba(0,209,199,0.5)`)
- **Negative corr:** Crimson gradient (light→dark: `rgba(255,71,87,0.25)` → `rgba(255,71,87,0.5)`)
- **Neutral corr:** Gray tint (`rgba(136,136,170,0.15)`)
- **Labels:** 0.55rem, Text Secondary. Abbreviated asset codes.

### Loading States
- **Skeleton:** Matching card dimensions. Shimmer animation via CSS gradient sweep.
- **Content:** Opacity 0.4 with 0.3s fade-up on load complete.
- **BANNED:** Generic circular spinners, infinite rotating indicators.

## 5. Layout Principles

- **Max-width container:** 1440px centered. Full-bleed backgrounds, contained content.
- **Grid:** CSS Grid with `repeat(auto-fit, minmax(340px, 1fr))`. Cards auto-flow into rows.
- **Wide spans:** `grid-column: 1 / -1` for correlation matrix, pipeline evaluation.
- **Spacing:** 16px card gap, 24px section gap, 20px body padding.
- **Section dividers:** 0.9rem uppercase Tactical Gold title with bottom border separator.
- **Header:** Full-width Midnight Navy banner, max-width 1440px. Logo left, status center, refresh right.
- **Mobile (< 768px):** Single-column collapse. All grids become 1fr. Container padding reduces to 0. Touch targets minimum 44px.
- **BANNED:** CSS `calc()` percentage hacks, flexbox margin math for grids, 3-column equal card rows, absolute-positioned content stacking, centered hero sections.

## 6. Motion & Interaction

- **Hover Transitions:** 200ms ease-out. Color, border-color, and opacity transitions only.
- **Active / Click:** `scale(0.97)` transform, 150ms spring (stiffness: 100, damping: 20). Tactile, not elastic.
- **Data Updates:** Opacity 0.4 during fetch (loading class), snap to 1.0 on complete. 300ms transition.
- **Staggered Mount:** Dashboard sections mount in cascade — header first, metrics row, then cards left-to-right, top-to-bottom. 80ms delay between sections.
- **Auto-Refresh:** 30s interval. Content updates in-place with no layout shift (fixed dimensions).
- **Status Dot:** Stable cyan pulse for connected, static warning for degraded, static danger for error.
- **BANNED:** Linear easing, CSS `top/left/width/height` animations, parallax scroll, bouncing loaders.

## 7. Anti-Patterns (Banned)

- No emojis anywhere — not in labels, not in status, not in data
- No Inter font — use Geist for display/body, JetBrains Mono for data
- No serif fonts — this is a dashboard, not an editorial site
- No pure black (#000000) — use Deep Charcoal (#1A1D20)
- No neon/outer glow shadows — flat surfaces only
- No oversaturated accents — Tactical Gold at #D9A441, not #FFD700
- No gradient text on headers — solid color only
- No custom mouse cursors — system cursors always
- No overlapping elements — every element in its own clean spatial zone
- No 3-column equal card layouts — asymmetric sizing preferred
- No generic names — use real asset symbols (GC1!, ES1!, BTC/USDT)
- No fake round numbers — display calculated values with appropriate precision
- No AI copywriting clichés — "Elevate", "Seamless", "Unleash", "Next-Gen"
- No filler text — no "Scroll to explore", no bouncing chevrons
- No circular spinners — skeletal loaders matching layout dimensions
- No broken image links — use inline SVG for any icons
- No linear easing — spring physics (stiffness: 100, damping: 20) for all interactive animations

---


---

> **SSOT:** `CANONICAL.md` v8.0.21 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live
