# Amad Brand Guidelines

**Version 1.0**

> This document is the definitive reference for Amad's visual and verbal identity.
> All product teams, designers, and developers should follow these guidelines.
> For the canonical token source of truth, see `lib/brand-tokens/amad.tokens.json`.

---

## 1. Brand Foundation

See `docs/brand/brand-foundation.md` for the complete brand strategy, positioning, voice, and naming rules.

**One-line summary:** Amad is operational intelligence for the Saudi construction market — structural, precise, authoritative.

---

## 2. Logo System

### 2.1 The Symbol — Three Pillars (عَمَد)

The Amad symbol is a geometric abstraction of three vertical pillars resting on a horizontal foundation.

```
   ▐█▌
▐█▌███▐█▌
▔▔▔▔▔▔▔▔▔
```

**Concept rationale:**
- Three pillars mirror the literal Arabic meaning of عَمَد (structural supports/columns)
- The centre pillar stands taller — dominant, commanding, a data peak
- The horizontal foundation line grounds the mark — everything rests on something solid
- The A-silhouette of the three pillars references the English wordmark without spelling it out
- The mark reads equally as a bar chart, a building elevation, and an abstract letter A

**Geometry:**
- viewBox: `0 0 48 48`
- Left pillar: `x=5 y=22 w=10 h=22 rx=1.5`
- Centre pillar: `x=19 y=8 w=10 h=36 rx=1.5`
- Right pillar: `x=33 y=22 w=10 h=22 rx=1.5`
- Baseline: `x=3 y=44 w=42 h=2 rx=1`

**File:** `artifacts/web/public/brand/amad-symbol.svg`

### 2.2 Logo Variants

| File | Purpose |
|------|---------|
| `amad-symbol.svg` | Standalone geometric mark. `currentColor` — inherits from parent. |
| `amad-mark-light.svg` | Explicit navy fill `#0D1F3C` — for use on white/light backgrounds. |
| `amad-mark-dark.svg` | Explicit white fill `#FFFFFF` — for use on dark/navy backgrounds. |
| `amad-wordmark-en.svg` | English wordmark "AMAD" — geometric SVG paths. |
| `amad-wordmark-ar.svg` | Arabic wordmark "عَمَد" — Noto Sans Arabic 700. |
| `amad-lockup-en.svg` | English full lockup — symbol + AMAD + descriptor. |
| `amad-lockup-ar.svg` | Arabic full lockup — Arabic wordmark + descriptor + symbol (RTL). |

### 2.3 In-Application Usage

The `LogoMark` React component (`src/components/LogoMark.tsx`) renders the symbol as inline SVG using `currentColor`. Control the fill colour with Tailwind `text-*` classes.

```tsx
// On dark sidebar (gold mark)
<LogoMark className="w-6 h-6 text-sidebar-primary-foreground" />

// On light background (navy mark)
<LogoMark className="w-6 h-6 text-[#0D1F3C]" />
```

### 2.4 Clear Space

Maintain a minimum clear space equal to the height of the baseline bar on all four sides.

### 2.5 Minimum Sizes

| Context | Minimum size |
|---------|-------------|
| Favicon / app icon | 16×16px (use `brand/favicon.svg`) |
| Sidebar icon | 24×24px |
| Login panel | 40×40px |
| Print / document | 20mm |

### 2.6 Incorrect Usage

❌ Do not rotate the symbol.
❌ Do not use the symbol with a drop shadow or glow.
❌ Do not recolour the symbol to red, green, or any status colour.
❌ Do not stretch or distort the symbol.
❌ Do not use the Arabic character `عَ` alone as the logo mark.
❌ Do not add a border or outline to the symbol.
❌ Do not place the mark on patterned or photographic backgrounds without sufficient contrast.

---

## 3. Favicon & App Icon System

| File | Usage |
|------|-------|
| `brand/favicon.svg` | Browser tab icon. Navy square, gold three-pillar mark. Referenced in `index.html`. |
| `brand/app-icon.svg` | PWA / general app icon. 512×512 equivalent, rounded-rect navy. |
| `brand/app-icon-maskable.svg` | Maskable mobile icon. Full-bleed navy, symbol within safe zone. |

### 3.1 Future Export Sizes

When producing PNG exports for platform distribution:

| Size | Platform | Notes |
|------|----------|-------|
| 16×16 | Browser (legacy favicon) | Export from `brand/favicon.svg` |
| 32×32 | Browser (HiDPI) | Export from `brand/favicon.svg` |
| 180×180 | Apple Touch Icon | Export from `brand/app-icon.svg` |
| 192×192 | Android / PWA | Export from `brand/app-icon.svg` |
| 512×512 | Android / PWA splash | Export from `brand/app-icon.svg` |
| 512×512 maskable | Android adaptive icon | Export from `brand/app-icon-maskable.svg` |

---

## 4. Colour System

### 4.1 Brand Palette

| Name | Hex | HSL | Usage |
|------|-----|-----|-------|
| Navy 900 | `#0D1F3C` | 222 55% 15% | Primary CTA, sidebar background |
| Navy 950 | `#080E1C` | 222 45% 7% | Dark mode background |
| Gold 500 | `#C8953A` | 38 58% 51% | Accent, active state, KPI emphasis |
| Gold 400 | `#DFA035` | 38 62% 54% | Dark mode accent (brighter) |
| White | `#FFFFFF` | — | Primary text on dark, card surface |
| Silver 96 | `#F1F4F8` | 220 16% 96% | Light mode background |

### 4.2 Light Mode Token Usage

| Token | Value | Purpose |
|-------|-------|---------|
| `--background` | 220 16% 96% | Page background |
| `--card` | 0 0% 100% | Card / panel surface |
| `--primary` | 222 55% 18% | CTA buttons, strong actions |
| `--accent` | 38 58% 51% | Active navigation, KPI emphasis |
| `--sidebar` | 222 60% 14% | Sidebar background |
| `--sidebar-primary` | 38 58% 51% | Logo container, active nav indicator |
| `--muted` | 220 16% 91% | Dividers, disabled surfaces |
| `--muted-foreground` | 222 22% 44% | Secondary text |

### 4.3 Dark Mode Token Usage

| Token | Value | Purpose |
|-------|-------|---------|
| `--background` | 222 45% 7% | Page background (deep navy-black) |
| `--card` | 222 42% 11% | Elevated card surface |
| `--primary` | 38 62% 58% | Brighter gold — primary in dark mode |
| `--accent` | 38 62% 58% | Same gold |
| `--sidebar` | 222 55% 5% | Deepest sidebar navy |

### 4.4 Semantic Colours

| Token | Light | Dark | Meaning |
|-------|-------|------|---------|
| `--destructive` | 0 82% 54% | 0 68% 58% | Error, danger, destructive actions |
| Success (badge) | `emerald-100/800` | `emerald-900/30/400` | Completed, approved, closed |
| Warning (badge) | `amber-100/800` | `amber-900/30/400` | Delayed, pending, on hold |
| Danger (badge) | `red-100/800` | `red-900/30/400` | Critical, overdue, rejected |
| Info (badge) | `blue-100/800` | `blue-900/30/400` | Informational, neutral positive |

### 4.5 Chart / Data Visualisation Palette

Chart colours are designed to be distinguishable for colourblind users and readable on both light and dark surfaces. Do not override chart colours with brand colours.

| Position | Light Hex | Dark Hex | Description |
|----------|-----------|----------|-------------|
| Chart 1 | `#C8953A` | `#DFA035` | Gold — primary series |
| Chart 2 | `#2057A8` | `#5B9CF5` | Blue — secondary series |
| Chart 3 | `#2E8A68` | `#2EB86A` | Teal — tertiary series |
| Chart 4 | `#7A4EBF` | `#A78BFA` | Purple — quaternary series |
| Chart 5 | `#E82222` | `#E55555` | Red — danger / critical series |

### 4.6 Prohibited Colour Combinations

❌ Do not use gold text on white background (insufficient contrast).
❌ Do not use gold on gold.
❌ Do not use light navy text on dark navy background.
❌ Do not use chart colours for semantic status (danger, success, warning).
❌ Do not use excessive gold coverage — it degrades to "luxury" from "precision".

---

## 5. Typography

### 5.1 Typeface Selection

| Language | Primary | Fallback |
|----------|---------|----------|
| English / Latin | Inter (Google Fonts) | Segoe UI → system-ui |
| Arabic | Noto Sans Arabic (Google Fonts) | Geeza Pro → Arial Unicode MS |
| Monospace | JetBrains Mono | Fira Code → Menlo → Consolas |

**Loading:** Both fonts are loaded via Google Fonts `display=swap` in `index.html`. The CSS fallback stack ensures the UI is usable even when the network request fails.

**Arabic fallback strategy:** The font-family stack includes both Inter and Noto Sans Arabic. Inter has no Arabic glyphs, so the browser falls through to Noto Sans Arabic automatically for Arabic codepoints. No per-element font switching is required for mixed content.

### 5.2 Type Scale

| Role | Size | Weight | Usage |
|------|------|--------|-------|
| Display | 36px | 700 | Login hero title |
| H1 | 28px | 700 | Page titles |
| H2 | 22px | 700 | Section headings |
| H3 | 18px | 600 | Sub-section headings |
| H4 | 15px | 600 | Card titles, panel headers |
| Body | 14px | 400 | Default body text |
| Body Medium | 14px | 500 | Emphasis within body |
| Small | 12px | 400 | Supplementary text |
| Caption | 11px | 400 | Timestamps, helper text |
| Label | 11px | 600 | Form labels, table headers, badges |
| KPI Number | 36px | 700 | Dashboard KPIs — tabular numerals |
| Table Header | 11px | 600 | Uppercase, tracked, tabular |
| Table Body | 13px | 400 | Dense, tabular numerals |

### 5.3 Numeric Readability

KPI and table numeric columns must use tabular numerals to prevent layout shifts when numbers change. Apply the `.tabular-nums` CSS class or `font-variant-numeric: tabular-nums`.

### 5.4 Arabic Typography Notes

- Arabic text should not be mixed with English text in the same heading — use separate elements.
- Arabic numerals (٠١٢٣...) are not used in this platform. Western-Arabic numerals (0123...) are used throughout for consistency with engineering documents.
- Diacriticals (tashkeel) are used in the product name `عَمَد` only — not in UI text generally.
- Line-height in Arabic should be 1.6 minimum to accommodate vowel marks.

---

## 6. Iconography

Use Lucide React for all icons. This ensures visual consistency (stroke-based, `currentColor`, uniform stroke width).

**Rules:**
- Use 16px (`w-4 h-4`) for inline / navigation icons
- Use 20px (`w-5 h-5`) for topbar / action icons
- Use 24px (`w-6 h-6`) for empty state icons
- Use 48px (`w-12 h-12`) for hero / illustration icons
- Never fill Lucide icons — they are stroke-only
- Never substitute emoji for icons in the UI

---

## 7. Data Visualisation

Amad is a data-intensive platform. Charts are a first-class citizen of the design system.

**Principles:**
- Data clarity over aesthetics. Never reduce chart information for decorative reasons.
- Gold (Chart 1) should be the primary series in all charts — it connects to the brand.
- Use the defined 5-colour chart palette. Do not use random or arbitrary colours in charts.
- Always include axis labels, legends, and accessible colour descriptions.
- Recharts is the chart library — respect its built-in responsive and accessible patterns.

---

## 8. Light / Dark Theme Guidance

Both themes are production-quality experiences. Rules:

- Do not use `opacity` to create dark-mode colours — define explicit dark-mode token values.
- Test contrast ratios in both modes. WCAG AA minimum is 4.5:1 for body text, 3:1 for large text and UI components.
- Navigation indicators and focus rings must be visible in both modes.
- Gold in dark mode is brighter (`38 62% 58%`) than in light mode (`38 58% 51%`) to compensate for dark background luminance.
- Never use pure black (`#000000`) as a background — use the defined dark-mode navy values.

---

## 9. Arabic / RTL Considerations

- Direction is controlled by `document.documentElement.dir = 'rtl'` — switching happens at the document level.
- The CSS custom variant `@custom-variant dark (&:is(.dark *))` is RTL-compatible.
- Sidebar slides in from the right in RTL mode — the `sidebarHiddenClass` in `layout.tsx` handles this.
- Arabic SVG lockup (`amad-lockup-ar.svg`) places the symbol on the right, wordmark on the left.
- Do not hard-code `left` / `right` in styles — use `start` / `end` or Tailwind's `s-*` / `e-*` variants.
- Test all pages in both LTR and RTL — table alignment, card padding, and form labels must all flip.

---

## 10. Accessibility

**Standards:** WCAG 2.1 Level AA minimum, targeting Level AAA for critical paths (login, navigation, KPI cards).

**Colour contrast:**
- Body text on background: minimum 7:1 (AAA) in light mode.
- Muted text: minimum 4.5:1 (AA).
- Interactive elements (buttons, links): minimum 3:1 border contrast vs background.
- Focus ring: 2px solid `hsl(var(--focus-ring))` — visible in both themes.

**Focus management:**
- All interactive elements must be reachable by keyboard.
- Use `:focus-visible` (not `:focus`) so mouse users do not see unnecessary outlines.
- The mobile sidebar must be keyboard-operable (open/close with keyboard, trap focus when open).

**ARIA:**
- Navigation landmark: `<nav aria-label="Navigation sidebar">`.
- Icon-only buttons must have `aria-label`.
- Status badges are purely visual — do not use them as the only error indicator.
- Charts must have `aria-label` or adjacent text description.

**Reduced motion:**
- All CSS transitions and animations are suppressed at `@media (prefers-reduced-motion: reduce)`.
- This is implemented globally in `index.css`.

---

## 11. Motion Principles

Amad uses functional motion only. Motion serves the user, not the brand.

**Allowed:**
- Hover transitions: `150ms ease-out` colour/background changes
- Focus transitions: `150ms ease-out` ring appearance
- Sidebar slide: `300ms cubic-bezier(0.32, 0.72, 0, 1)` (iOS-like deceleration)
- Skeleton shimmer: `1.6s linear` background-position pulse
- Overlay fade: `200ms ease-out` opacity

**Not allowed:**
- Entrance animations on page navigation
- Bounce or spring effects
- Loading spinners that run indefinitely beyond 10s
- Animated decorations that serve no functional purpose

**All motion must be suppressed when `prefers-reduced-motion: reduce` is detected.**

---

## 12. Mobile Application Reuse

The brand token source of truth is `lib/brand-tokens/amad.tokens.json`. A future React Native / Expo app should consume this file directly.

**What to reuse:**
- `brand.*` colour values → Expo `StyleSheet` colours
- `semantic.light.*` and `semantic.dark.*` → theme contexts in Expo
- `typography.scale.*` → `StyleSheet.text` definitions
- `spacing.*` → consistent margin/padding values
- `radius.*` → `borderRadius` values
- All SVG assets in `artifacts/web/public/brand/` are platform-agnostic

**What NOT to copy from the web implementation to mobile:**
- CSS custom properties (`--variable`) — web only
- Tailwind `@theme inline` blocks — Tailwind v4 / web-only
- `bg-*` / `text-*` Tailwind class strings — web only
- `hsl()` CSS colour functions — use hex or rgba in React Native

**Fonts in Expo:**
```js
// Install: expo-google-fonts
import { Inter_400Regular, Inter_700Bold } from '@expo-google-fonts/inter';
import { NotoSansArabic_400Regular, NotoSansArabic_700Bold } from '@expo-google-fonts/noto-sans-arabic';
```

---

## 13. Product UI Examples

### Login screen
- Left panel: deep navy (`--sidebar`), LogoMark in gold, brand tagline in white
- Right panel: light background (`--background`), form with standard brand inputs
- Both panels use the same `LogoMark` component with `currentColor`

### Dashboard
- KPI cards: white/card surface, KPI numbers in `.kpi-number` class (tabular numerals)
- Risk indicators use semantic badge classes (`.badge-danger`, `.badge-warning`, etc.)
- Charts use the defined 5-colour chart palette

### Sidebar
- Deep navy background
- Gold active indicator (left border + `bg-sidebar-primary/15` tint)
- LogoMark in gold in the rounded-square container

---

## 14. Reports / PDF Reuse

When generating PDF reports from Amad data:

- Use the English lockup `amad-lockup-en.svg` in headers
- Use navy (`#0D1F3C`) as the header bar colour
- Use gold (`#C8953A`) for section headings and accents
- Use Inter (or system equivalent) for body text
- Use Noto Sans Arabic for any Arabic content sections
- Status colours should match the Amad semantic palette

---

## 15. Presentations / Demo Reuse

For sales decks, demos, or investor presentations:

- Use the English or Arabic lockup SVG on the title slide
- Navy slide backgrounds are appropriate — use `#0D1F3C` or `#080E1C`
- Gold headings or accent lines are on-brand
- Include the tagline: "Operational intelligence for the built world."
- Do not mix Amad branding with competitor product screenshots

---

*End of Amad Brand Guidelines v1.0*
