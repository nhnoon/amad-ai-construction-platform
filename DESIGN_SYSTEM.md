# AMAD Enterprise Design System
## Version 2.0 - Design Standards & Component Specifications

**Platform**: AMAD Construction AI Platform  
**Framework**: React 19 + Tailwind CSS + TypeScript  
**Goal**: Reusable, consistent, enterprise-grade UI standards

---

## TABLE OF CONTENTS

1. [Design Tokens](#design-tokens)
2. [Spacing System](#spacing-system)
3. [Typography](#typography)
4. [Color Palette](#color-palette)
5. [Components](#components)
6. [Patterns](#patterns)
7. [Elevation & Shadows](#elevation--shadows)
8. [Animations & Transitions](#animations--transitions)
9. [Responsive Breakpoints](#responsive-breakpoints)
10. [Accessibility](#accessibility)
11. [Dark Mode](#dark-mode)
12. [RTL Support](#rtl-support)
13. [Icon Library](#icon-library)
14. [Usage Examples](#usage-examples)

---

## DESIGN TOKENS

### Token Hierarchy

```
Design Tokens (Base Values)
├── Spacing
├── Typography
├── Colors
├── Shadows
├── Border Radius
├── Animations
└── Breakpoints

Component Tokens (Derived)
├── Button Tokens
├── Input Tokens
├── Card Tokens
├── Modal Tokens
└── Badge Tokens
```

### Token Naming Convention

```
{category}-{property}-{variant}

Examples:
- spacing-xs (extra small)
- color-primary (primary color)
- shadow-lg (large shadow)
- border-radius-md (medium radius)
- animation-fade (fade animation)
- breakpoint-md (medium breakpoint)
```

---

## SPACING SYSTEM

### Core Spacing Scale

Built on **4px base unit** (Tailwind default).

```
spacing-0    = 0px
spacing-1    = 4px
spacing-2    = 8px
spacing-3    = 12px
spacing-4    = 16px
spacing-5    = 20px
spacing-6    = 24px
spacing-7    = 28px
spacing-8    = 32px
spacing-9    = 36px
spacing-10   = 40px
spacing-12   = 48px
spacing-14   = 56px
spacing-16   = 64px
spacing-20   = 80px
spacing-24   = 96px
```

### Tailwind Equivalents

```
Spacing in Tailwind (already available):
p-0, p-1, p-2, p-3, p-4, p-5, p-6, p-7, p-8, p-9, p-10, p-12, p-14, p-16, p-20, p-24

m-0, m-1, m-2, m-3, m-4, m-5, m-6, m-7, m-8, m-9, m-10, m-12, m-14, m-16, m-20, m-24

gap-0, gap-1, gap-2, gap-3, gap-4, gap-5, gap-6, gap-7, gap-8, gap-9, gap-10, gap-12, gap-14, gap-16, gap-20, gap-24

ps-{n}, pe-{n} (padding-start/end - for RTL)
ms-{n}, me-{n} (margin-start/end - for RTL)
```

### Spacing Guidelines

#### Padding (Content Inside Container)

| Usage | Spacing |
|-------|---------|
| Compact input | p-2 (8px) |
| Normal button | p-2 py-2.5 (8px/10px) |
| Card body | p-4 (16px) |
| Modal body | p-6 (24px) |
| Page body | p-6 (24px) |
| Sidebar | p-4 (16px) |

#### Margins (Space Between Elements)

| Usage | Spacing |
|-------|---------|
| Between form fields | mb-4 (16px) |
| Between card rows | my-3 (12px) |
| Between sections | mb-8 (32px) |
| Between pages | mb-6 (24px) |

#### Gaps (Between Grid Items)

| Usage | Spacing |
|-------|---------|
| Tight grid (cards) | gap-3 (12px) |
| Normal grid | gap-4 (16px) |
| Loose grid | gap-6 (24px) |
| Form fields | gap-2 (8px) - horizontal, gap-4 (16px) - vertical |

### Spacing in Practice

```jsx
// Page spacing
<div className="space-y-6">           // 24px gap between children
  <h1>Title</h1>
  <p>Content</p>
</div>

// Card spacing
<div className="p-6 space-y-4">       // 24px padding, 16px between children
  <h2>Card Title</h2>
  <p>Card content</p>
</div>

// Grid spacing (module cards)
<div className="grid grid-cols-3 gap-4"> // 16px gap between cards
  {cards.map(card => <Card />)}
</div>

// Flex spacing
<div className="flex gap-3 items-center"> // 12px gap, centered
  <Icon />
  <span>Label</span>
</div>

// Responsive spacing
<div className="p-4 md:p-6 lg:p-8">  // 16px (mobile), 24px (tablet), 32px (desktop)
  Content
</div>
```

---

## TYPOGRAPHY

### Font Family

```
Font Stack (System):
-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif

Monospace:
"SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace
```

### Font Sizes

```
text-xs     = 12px  (line-height: 16px)
text-sm     = 14px  (line-height: 20px)
text-base   = 16px  (line-height: 24px)
text-lg     = 18px  (line-height: 28px)
text-xl     = 20px  (line-height: 28px)
text-2xl    = 24px  (line-height: 32px)
text-3xl    = 30px  (line-height: 36px)
text-4xl    = 36px  (line-height: 40px)
```

### Font Weights

```
font-normal    = 400 (Regular)
font-medium    = 500 (Medium)
font-semibold  = 600 (Semibold)
font-bold      = 700 (Bold)
font-black     = 900 (Black - rare)
```

### Typography Scale

| Element | Size | Weight | Line Height | Usage |
|---------|------|--------|-------------|-------|
| Page Title | 2xl (24px) | bold (700) | 32px | `<h1>` |
| Section Title | xl (20px) | bold (700) | 28px | `<h2>` |
| Card Title | lg (18px) | semibold (600) | 28px | Card headers |
| Body Text | base (16px) | normal (400) | 24px | Paragraphs |
| Label | sm (14px) | medium (500) | 20px | Form labels |
| Small Text | xs (12px) | normal (400) | 16px | Captions, hints |
| Button Text | sm (14px) | medium (500) | 20px | All buttons |

### Typography in Practice

```jsx
// Page header
<h1 className="text-2xl font-bold leading-tight">Page Title</h1>

// Section header
<h2 className="text-xl font-bold mb-4">Section Title</h2>

// Card title
<h3 className="text-lg font-semibold">Card Title</h3>

// Body text
<p className="text-base leading-relaxed">
  This is body text with proper line height for readability.
</p>

// Label
<label className="text-sm font-medium text-muted-foreground">
  Form Label
</label>

// Small text / caption
<span className="text-xs text-muted-foreground">
  Caption or helper text
</span>

// Responsive typography
<h1 className="text-lg md:text-2xl lg:text-3xl">
  Responsive Title
</h1>
```

---

## COLOR PALETTE

### Semantic Colors

```
Color System (Semantic):
├── Neutral (Grays)
├── Primary (Brand Color)
├── Secondary (Accent)
├── Destructive (Danger/Error)
├── Warning (Caution)
├── Success (Positive)
└── Info (Informational)
```

### Neutral Colors (Grays)

```
foreground              = #0F172A (Text color - almost black)
background              = #FFFFFF (Page background)
card                    = #FFFFFF (Card background)
muted                   = #F1F5F9 (Muted backgrounds)
muted-foreground        = #64748B (Muted text)
border                  = #E2E8F0 (Border color)
input                   = #FFFFFF (Input backgrounds)

Dark Mode:
foreground              = #F8FAFC (Text color - almost white)
background              = #0F172A (Page background - dark)
card                    = #1E293B (Card background - dark)
muted                   = #1E293B (Muted backgrounds - dark)
muted-foreground        = #94A3B8 (Muted text - dark)
border                  = #334155 (Border color - dark)
input                   = #0F172A (Input backgrounds - dark)
```

### Brand Colors (Primary)

```
primary                 = #3B82F6 (Primary blue)
primary-foreground      = #FFFFFF (Text on primary)

Shades:
primary-50              = #EFF6FF
primary-100             = #DBEAFE
primary-200             = #BFDBFE
primary-300             = #93C5FD
primary-400             = #60A5FA
primary-500             = #3B82F6 (Main)
primary-600             = #2563EB
primary-700             = #1D4ED8
primary-800             = #1E40AF
primary-900             = #1E3A8A
```

### Status Colors

```
SUCCESS (Green):
success                 = #10B981
success-foreground      = #FFFFFF
success-50              = #F0FDF4
success-600             = #059669

WARNING (Amber):
warning                 = #F59E0B
warning-foreground      = #FFFFFF
warning-50              = #FFFBEB
warning-600             = #D97706

DESTRUCTIVE/DANGER (Red):
destructive             = #EF4444
destructive-foreground  = #FFFFFF
destructive-50          = #FEF2F2
destructive-600         = #DC2626

INFORMATION (Cyan):
info                    = #0891B2
info-foreground         = #FFFFFF
info-50                 = #ECFDFD
info-600                = #0E7490
```

### Module Colors (Operations Workspace)

```
Projects (Blue):
- Icon: #3B82F6
- Background: #EFF6FF
- Border: #BFDBFE
- Text: #1E40AF

Meetings (Purple):
- Icon: #A855F7
- Background: #FAF5FF
- Border: #E9D5FF
- Text: #6B21A8

Procurement (Green):
- Icon: #10B981
- Background: #F0FDF4
- Border: #BBFBDB
- Text: #065F46

Site Reports (Amber):
- Icon: #F59E0B
- Background: #FFFBEB
- Border: #FDE68A
- Text: #92400E

RFIs (Cyan):
- Icon: #06B6D4
- Background: #ECFDFD
- Border: #A5F3FC
- Text: #0E7490

Change Orders (Pink):
- Icon: #EC4899
- Background: #FCE7F3
- Border: #FBCFE8
- Text: #831843

Claims (Red):
- Icon: #EF4444
- Background: #FEF2F2
- Border: #FECACA
- Text: #7F1D1D
```

### Color Usage

| Component | Background | Text | Border |
|-----------|-----------|------|--------|
| Primary Button | primary (blue) | primary-foreground (white) | — |
| Secondary Button | muted | foreground | border |
| Destructive Button | destructive (red) | destructive-foreground (white) | — |
| Input Field | input (white/dark) | foreground | border |
| Card | card | foreground | border |
| Success Badge | success-50 | success-600 | success-200 |
| Warning Badge | warning-50 | warning-600 | warning-200 |
| Danger Badge | destructive-50 | destructive-600 | destructive-200 |

### Color in Practice

```jsx
// Primary button
<button className="bg-primary text-primary-foreground">
  Primary Action
</button>

// Success badge
<span className="bg-success-50 text-success-600 border border-success-200 px-2 py-1 rounded">
  Success
</span>

// Card with border
<div className="bg-card text-foreground border border-border rounded-lg p-4">
  Card content
</div>

// Muted text
<p className="text-muted-foreground">
  This text is muted
</p>

// Module card (Projects - blue)
<div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
  <div className="flex items-center gap-2">
    <Briefcase className="w-6 h-6 text-blue-600" />
    <h3 className="font-semibold text-blue-900">Projects</h3>
  </div>
</div>
```

---

## COMPONENTS

### Button

```jsx
// Variants
<button className="bg-primary text-primary-foreground px-4 py-2 rounded-lg font-medium">
  Primary
</button>

<button className="bg-muted text-foreground px-4 py-2 rounded-lg font-medium border border-border">
  Secondary
</button>

<button className="bg-destructive text-destructive-foreground px-4 py-2 rounded-lg font-medium">
  Destructive
</button>

<button className="bg-transparent text-foreground px-4 py-2 rounded-lg font-medium border border-border hover:bg-muted">
  Ghost
</button>

// Sizes
<button className="px-2 py-1 text-xs rounded font-medium">Small</button>
<button className="px-4 py-2 text-sm rounded-lg font-medium">Medium (default)</button>
<button className="px-6 py-3 text-base rounded-lg font-medium">Large</button>

// With Icon
<button className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg">
  <Icon className="w-4 h-4" />
  Button Label
</button>

// Specs
Button Dimensions:
- Height: 36px (default/medium)
- Padding: px-4 py-2.5 (16px horizontal, 10px vertical)
- Border Radius: rounded-lg (8px)
- Font: text-sm font-medium
- Transition: all 200ms ease-in-out
- Hover: Increase shadow, scale 1.02
- Active: Scale 0.98
- Disabled: opacity-50, cursor-not-allowed
```

### Input & Select

```jsx
// Text Input
<input
  type="text"
  placeholder="Placeholder text"
  className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-input text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-transparent"
/>

// Textarea
<textarea
  placeholder="Multi-line input"
  className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-input text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary focus:border-transparent min-h-[100px]"
/>

// Select
<select className="px-3 py-2 text-sm border border-border rounded-lg bg-input text-foreground focus:outline-none focus:ring-1 focus:ring-primary">
  <option>Option 1</option>
  <option>Option 2</option>
</select>

// Specs
Input Dimensions:
- Height: 36px (py-2)
- Padding: px-3 (12px horizontal)
- Border Radius: rounded-lg (8px)
- Font: text-sm
- Border: 1px border-border
- Focus: ring-1 ring-primary, border-transparent
- Disabled: opacity-50, cursor-not-allowed
```

### Card

```jsx
// Basic Card
<div className="bg-card border border-border rounded-lg p-6">
  <h3 className="text-lg font-semibold mb-4">Card Title</h3>
  <p className="text-muted-foreground">Card content</p>
</div>

// Card with Header & Body
<div className="bg-card border border-border rounded-lg overflow-hidden">
  <div className="border-b border-border px-6 py-4">
    <h3 className="font-semibold">Card Title</h3>
  </div>
  <div className="p-6">
    <p>Card content</p>
  </div>
</div>

// Module Card (Operations)
<button className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-start group hover:shadow-lg hover:scale-102 transition-all">
  <div className="flex items-start justify-between mb-3">
    <Briefcase className="w-6 h-6 text-blue-600" />
  </div>
  <h4 className="font-semibold text-blue-900 mb-2">Projects</h4>
  <p className="text-sm text-blue-700 mb-3">48 Active · 3 Delayed</p>
  <button className="text-blue-600 text-sm font-medium group-hover:underline">
    Open Projects →
  </button>
</button>

// Specs
Card Dimensions:
- Border Radius: rounded-lg (8px)
- Border: 1px border-border
- Padding: p-6 (24px)
- Shadow: shadow-sm (subtle)
- Hover Shadow: shadow-lg (elevated)
- Transition: all 200ms ease-in-out
```

### Badge

```jsx
// Status Badge
<span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
  Active
</span>

// Severity Badge
<span className="inline-flex items-center px-2 py-1 rounded text-xs font-bold bg-red-50 text-red-700">
  Critical
</span>

// Icon Badge (e.g., notifications)
<div className="relative">
  <Bell className="w-6 h-6" />
  <span className="absolute -top-2 -right-2 h-5 w-5 bg-destructive text-white rounded-full flex items-center justify-center text-xs font-bold">
    5
  </span>
</div>

// Specs
Badge Dimensions:
- Height: 24px (py-1)
- Padding: px-3 (horizontal), px-2 (icon badge)
- Border Radius: rounded-full (success/status), rounded (severity)
- Font: text-xs font-semibold
- Border: 1px (optional, for subtle variants)
```

### Modal / Dialog

```jsx
// Modal Container
<div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50">
  <div className="bg-card border border-border rounded-lg shadow-lg p-6 w-full max-w-md">
    {/* Header */}
    <div className="flex items-center justify-between mb-6">
      <h2 className="text-lg font-semibold">Modal Title</h2>
      <button className="text-muted-foreground hover:text-foreground">
        <X className="w-4 h-4" />
      </button>
    </div>

    {/* Body */}
    <div className="space-y-4 mb-6">
      <p className="text-foreground">Modal content goes here</p>
    </div>

    {/* Footer */}
    <div className="flex gap-3 justify-end">
      <button className="px-4 py-2 text-sm font-medium border border-border rounded-lg hover:bg-muted">
        Cancel
      </button>
      <button className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-lg hover:bg-primary-600">
        Confirm
      </button>
    </div>
  </div>
</div>

// Specs
Modal Dimensions:
- Backdrop: bg-black/40 backdrop-blur-sm
- Content: max-w-md (432px), centered with flex
- Padding: p-6 (24px)
- Border Radius: rounded-lg (8px)
- Shadow: shadow-lg
- Z-index: z-50 (above everything)
```

### Tabs

```jsx
// Tab Navigation
<div className="flex gap-0 border-b border-border">
  {tabs.map(tab => (
    <button
      key={tab.id}
      onClick={() => setActiveTab(tab.id)}
      className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
        activeTab === tab.id
          ? "border-primary text-primary"
          : "border-transparent text-muted-foreground hover:text-foreground"
      }`}
    >
      {tab.label}
    </button>
  ))}
</div>

// Tab Content
<div className="p-6">
  {tabs.find(t => t.id === activeTab)?.content}
</div>

// Specs
Tab Dimensions:
- Height: 40px (py-2.5)
- Padding: px-4 (16px)
- Font: text-sm font-medium
- Border: 2px bottom indicator
- Transition: colors 200ms
- Active: border-primary text-primary
- Inactive: border-transparent text-muted-foreground
```

### Breadcrumb

```jsx
<nav className="flex items-center gap-2 text-sm">
  <Link href="/">Home</Link>
  <ChevronRight className="w-4 h-4 text-muted-foreground" />
  <Link href="/projects">Projects</Link>
  <ChevronRight className="w-4 h-4 text-muted-foreground" />
  <span className="text-foreground font-medium">Downtown Plaza</span>
</nav>

// Specs
Breadcrumb Dimensions:
- Font: text-sm
- Separator: ChevronRight icon (w-4 h-4)
- Color: Links (primary), current (foreground)
- Gap: gap-2 (8px)
```

### Tooltip

```jsx
<div className="group relative inline-block">
  <button>Hover me</button>
  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block bg-foreground text-background px-3 py-2 rounded text-xs whitespace-nowrap z-10">
    Tooltip text
    <div className="absolute top-full left-1/2 -translate-x-1/2 w-2 h-2 bg-foreground rotate-45" />
  </div>
</div>

// Specs
Tooltip Dimensions:
- Font: text-xs
- Padding: px-3 py-2
- Border Radius: rounded (4px)
- Background: foreground (text color)
- Text: background (opposite of foreground)
- Arrow: w-2 h-2 rotated
```

---

## PATTERNS

### Page Layout

```jsx
<div className="space-y-6">
  {/* Page Header */}
  <div className="page-header">
    <div>
      <h1 className="page-title">Page Title</h1>
      <p className="page-subtitle">Page description or stats</p>
    </div>
    <div className="flex items-center gap-3">
      <button>Action 1</button>
      <button>Action 2</button>
    </div>
  </div>

  {/* Content */}
  <div className="panel">
    <div className="panel-header border-b border-border px-6 py-4">
      <h2 className="panel-title">Section Title</h2>
    </div>
    <div className="panel-body p-6">
      Content here
    </div>
  </div>
</div>

// Tailwind Classes
.page-header: flex justify-between items-start md:items-center gap-6 flex-wrap
.page-title: text-3xl font-bold
.page-subtitle: text-muted-foreground text-sm mt-1
.panel: bg-card border border-border rounded-lg
.panel-header: flex items-center justify-between
.panel-title: font-semibold
.panel-body: p-6 space-y-4
```

### Form Layout

```jsx
<form className="space-y-6">
  {/* Form Group */}
  <div className="space-y-2">
    <label className="text-sm font-medium">Label</label>
    <input
      type="text"
      placeholder="Placeholder"
      className="w-full px-3 py-2 border border-border rounded-lg"
    />
    <p className="text-xs text-muted-foreground">Helper text</p>
  </div>

  {/* Submit */}
  <div className="flex gap-3 justify-end">
    <button type="button" className="px-4 py-2 border rounded-lg">
      Cancel
    </button>
    <button type="submit" className="px-4 py-2 bg-primary text-primary-foreground rounded-lg">
      Submit
    </button>
  </div>
</form>

// Specs
Form Group:
- space-y-2 (8px gap between label, input, helper)
- Label: text-sm font-medium
- Input: Full width, px-3 py-2
- Helper: text-xs text-muted-foreground
- Actions: flex gap-3 justify-end
```

### Data Table

```jsx
<div className="overflow-x-auto">
  <table className="w-full text-sm">
    <thead>
      <tr className="border-b border-border">
        <th className="text-start px-4 py-3 font-semibold text-muted-foreground">Column 1</th>
        <th className="text-start px-4 py-3 font-semibold text-muted-foreground">Column 2</th>
      </tr>
    </thead>
    <tbody>
      {rows.map(row => (
        <tr key={row.id} className="border-b border-border hover:bg-muted/50">
          <td className="px-4 py-3">{row.col1}</td>
          <td className="px-4 py-3">{row.col2}</td>
        </tr>
      ))}
    </tbody>
  </table>
</div>

// Specs
Table:
- text-sm (14px)
- Header: border-b, font-semibold, text-muted-foreground
- Row: border-b, hover:bg-muted/50
- Cell Padding: px-4 py-3 (16px horizontal, 12px vertical)
```

### Empty State

```jsx
<div className="flex flex-col items-center justify-center py-12 text-center">
  <FileText className="w-12 h-12 text-muted-foreground/30 mb-4" />
  <h3 className="text-lg font-semibold mb-2">No items found</h3>
  <p className="text-muted-foreground mb-6">Try adjusting your filters</p>
  <button className="px-4 py-2 bg-primary text-primary-foreground rounded-lg">
    Create First Item
  </button>
</div>

// Specs
Empty State:
- Icon: w-12 h-12, text-muted-foreground/30
- Title: text-lg font-semibold
- Description: text-muted-foreground
- CTA: Primary button
- Padding: py-12 (96px)
- Gap: mb-4, mb-2, mb-6
```

---

## ELEVATION & SHADOWS

### Shadow Scale

```
shadow-none      = none
shadow-sm        = 0 1px 2px 0 rgba(0, 0, 0, 0.05)
shadow-md        = 0 4px 6px -1px rgba(0, 0, 0, 0.1)
shadow-lg        = 0 10px 15px -3px rgba(0, 0, 0, 0.1)
shadow-xl        = 0 20px 25px -5px rgba(0, 0, 0, 0.1)
shadow-2xl       = 0 25px 50px -12px rgba(0, 0, 0, 0.25)

Color-specific shadows:
shadow-primary/20  = Colored shadow with primary at 20% opacity
```

### Shadow Usage

```jsx
// Card (elevated)
<div className="bg-card border border-border rounded-lg shadow-sm">
  Card content
</div>

// Hover effect (increase shadow)
<div className="bg-card rounded-lg shadow-sm hover:shadow-lg transition-shadow">
  Hoverable card
</div>

// Floating button
<div className="fixed bottom-6 right-6 bg-primary text-primary-foreground rounded-full shadow-xl shadow-primary/20">
  Floating button
</div>

// Modal
<div className="bg-card rounded-lg shadow-2xl">
  Modal content
</div>

// Dropdown
<div className="absolute top-full right-0 bg-card rounded-lg shadow-lg border border-border">
  Dropdown content
</div>
```

---

## ANIMATIONS & TRANSITIONS

### Transition Durations

```
duration-75       = 75ms (fast feedback)
duration-100      = 100ms (normal feedback)
duration-150      = 150ms (standard)
duration-200      = 200ms (hover/focus)
duration-300      = 300ms (modal open)
duration-500      = 500ms (page transitions)
```

### Easing Functions

```
ease-linear        = Linear (no acceleration)
ease-in            = Slow start, fast end
ease-out           = Fast start, slow end
ease-in-out        = Slow start and end
```

### Common Animations

```jsx
// Fade in/out
className="opacity-0 hover:opacity-100 transition-opacity duration-200"

// Scale (grow on hover)
className="scale-100 hover:scale-105 transition-transform duration-200"

// Slide up
className="translate-y-2 opacity-0 hover:translate-y-0 hover:opacity-100 transition-all duration-200"

// Smooth color change
className="bg-muted hover:bg-primary text-foreground hover:text-primary-foreground transition-colors duration-200"

// Button click feedback
className="active:scale-95 active:shadow-sm transition-all duration-100"

// Pulse (emphasis)
className="animate-pulse"

// Spinner
className="animate-spin"

// Bounce
className="animate-bounce"
```

### Animation in Practice

```jsx
// Hoverable card
<div className="group p-6 bg-card rounded-lg border border-border shadow-sm hover:shadow-lg hover:scale-102 transition-all duration-200 cursor-pointer">
  <h3 className="font-semibold group-hover:text-primary transition-colors duration-200">
    Card Title
  </h3>
</div>

// Button with feedback
<button className="px-4 py-2 bg-primary text-primary-foreground rounded-lg active:scale-95 hover:shadow-lg transition-all duration-150">
  Click me
</button>

// Expandable section
<div className="max-h-0 overflow-hidden transition-all duration-300 ease-in-out group-open:max-h-96">
  Hidden content
</div>

// Loading indicator
<div className="flex items-center gap-2">
  <div className="w-4 h-4 bg-primary rounded-full animate-pulse" />
  <span>Loading...</span>
</div>
```

---

## RESPONSIVE BREAKPOINTS

### Tailwind Breakpoints

```
Breakpoint  Width     Device
─────────────────────────────────────
(default)   <640px    Mobile (sm)
sm          640px     Small devices
md          768px     Tablet
lg          1024px    Desktop
xl          1280px    Large desktop
2xl         1536px    Ultra-wide
```

### Responsive Strategy

```
Mobile-First:
- Design for mobile first
- Add desktop features with md:, lg:, xl: prefixes
- Avoid max-w-* unless necessary
```

### Common Responsive Patterns

```jsx
// Typography
<h1 className="text-lg md:text-2xl lg:text-3xl">
  Responsive heading
</h1>

// Grid
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {items.map(item => <Card />)}
</div>

// Padding
<div className="p-4 md:p-6 lg:p-8">
  Responsive padding
</div>

// Display
<div className="hidden md:block">
  Desktop only
</div>

<div className="md:hidden">
  Mobile only
</div>

// Flex direction
<div className="flex flex-col md:flex-row gap-4">
  {sections.map(section => <Section />)}
</div>

// Width
<div className="w-full md:w-2/3 lg:w-1/2">
  Responsive width
</div>
```

---

## ACCESSIBILITY

### WCAG 2.1 Level AA Compliance

#### Color Contrast

```
Minimum Ratios:
- Normal text: 4.5:1
- Large text: 3:1
- Graphical elements: 3:1

Examples:
✅ foreground (#0F172A) on background (#FFFFFF) = 17.28:1
✅ primary (#3B82F6) on primary-foreground (#FFFFFF) = 8.59:1
✅ muted-foreground (#64748B) on background (#FFFFFF) = 6.24:1
```

#### Keyboard Navigation

```jsx
// All interactive elements must be keyboard accessible

// Button
<button
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleClick();
    }
  }}
>
  Click me
</button>

// Tab order
<div>
  <button>First (tab index 0)</button>
  <button>Second (tab index 1)</button>
  <input /> {/* Natural tab order */}
</div>

// Focus styles
<button className="focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2">
  Button with focus ring
</button>
```

#### ARIA Labels

```jsx
// Icon button
<button aria-label="Close modal">
  <X className="w-4 h-4" />
</button>

// Alert
<div role="alert" className="bg-destructive-50 text-destructive-700">
  Error message
</div>

// Loading indicator
<div role="status" aria-live="polite" aria-busy="true">
  <div className="animate-spin" />
  Loading...
</div>

// Expanded/collapsed
<button aria-expanded={isOpen} onClick={() => setIsOpen(!isOpen)}>
  Toggle menu
</button>

// Hidden from screen readers
<span aria-hidden="true">→</span>
```

#### Semantic HTML

```jsx
// Use semantic elements
<header>
  <nav>
    <ul>
      <li><a href="/">Home</a></li>
    </ul>
  </nav>
</header>

<main>
  <section>
    <h1>Page Title</h1>
    <article>Content</article>
  </section>
</main>

<footer>
  Footer content
</footer>

// Form accessibility
<form>
  <label htmlFor="email">Email:</label>
  <input id="email" type="email" required />
  <span id="email-hint" className="text-xs text-muted-foreground">
    We'll never share your email
  </span>
</form>
```

---

## DARK MODE

### Color Adjustments

```
Dark Mode Strategy:
- Swap background/foreground
- Reduce contrast on secondary text (lighter gray)
- Use slightly different shadows

Tailwind Dark Mode:
className="dark:bg-dark-background dark:text-dark-foreground"
```

### Common Dark Mode Classes

```jsx
// Background colors
<div className="bg-background dark:bg-slate-950">
  Dynamic background
</div>

// Text colors
<p className="text-foreground dark:text-slate-50">
  Text that adapts to dark mode
</p>

// Border colors
<div className="border border-border dark:border-slate-700">
  Border that adapts
</div>

// Card styling
<div className="bg-card dark:bg-slate-900 border dark:border-slate-700">
  Card in both modes
</div>

// Button hover states
<button className="bg-primary hover:bg-primary-600 dark:hover:bg-primary-500">
  Button
</button>
```

### CSS Variables (Optional)

```css
/* Light Mode */
:root {
  --background: #FFFFFF;
  --foreground: #0F172A;
  --card: #FFFFFF;
  --primary: #3B82F6;
}

/* Dark Mode */
@media (prefers-color-scheme: dark) {
  :root {
    --background: #0F172A;
    --foreground: #F8FAFC;
    --card: #1E293B;
    --primary: #60A5FA;
  }
}
```

---

## RTL SUPPORT

### Arabic (RTL) Layout Patterns

```jsx
// Don't use hardcoded left/right, use start/end

// ✅ Correct
<div className="ps-4 pe-6">  // padding-start / padding-end
  <span className="ms-2">    // margin-start
    Text
  </span>
</div>

// ❌ Avoid
<div className="pl-4 pr-6">  // left/right (breaks in RTL)
  <span className="ml-2">
    Text
  </span>
</div>

// Flexbox direction
<div className="flex flex-row-reverse gap-2">  // Reverses in RTL
  <Icon />
  <span>Label</span>
</div>

// Or use auto-detection
<div className="flex gap-2" dir={isRtl ? "rtl" : "ltr"}>
  <Icon />
  <span>Label</span>
</div>

// Text alignment
<p className="text-start">  // Start: left (LTR) or right (RTL)
  Paragraph
</p>

<p className="text-end">    // End: right (LTR) or left (RTL)
  Paragraph
</p>
```

### RTL Components

```jsx
// Breadcrumb (auto-reverses in RTL)
<nav className="flex gap-2">
  <a href="/">Home</a>
  <ChevronRight className="w-4 h-4 rtl:rotate-180" />
  <a href="/items">Items</a>
</nav>

// Navigation drawer
<div className={isRtl ? "right-0" : "left-0"}>
  Drawer content
</div>

// Sidebar
<aside className={isRtl ? "right-0" : "left-0"}>
  Sidebar
</aside>

// Floating button (opposite corner in RTL)
<button className={isRtl ? "left-6 bottom-6" : "right-6 bottom-6"}>
  Floating action
</button>
```

---

## ICON LIBRARY

### Icons Used (lucide-react)

```
Navigation:
  ChevronRight, ChevronLeft, ChevronDown, ChevronUp
  Menu, X, Home, Search, Settings

Modules/Content:
  Briefcase (Projects), Calendar (Meetings), ShoppingCart (Procurement)
  FileText (Site Reports), HelpCircle (RFIs), AlertCircle (Change Orders)
  TrendingUp (Claims), Folder (Documents), BarChart3 (Reports)
  Users (Administration), Zap (AMAD AI)

Status/Feedback:
  CheckCircle (Success), AlertOctagon (Error), AlertTriangle (Warning)
  Info (Information), Bell (Notifications)

Actions:
  Plus (Add), Edit2 (Edit), Trash2 (Delete), Download (Export)
  Copy (Duplicate), ExternalLink (Open in new), Save, Undo, Redo

Media:
  Image, Video, File, FileType-specific icons
```

### Icon Usage

```jsx
// Icon with size
<Briefcase className="w-4 h-4" />  // Small (16px)
<Briefcase className="w-6 h-6" />  // Medium (24px)
<Briefcase className="w-8 h-8" />  // Large (32px)

// Icon with color
<Briefcase className="w-6 h-6 text-blue-600" />

// Icon in button
<button className="flex items-center gap-2">
  <Plus className="w-4 h-4" />
  Add Item
</button>

// Icon only button (with aria-label)
<button aria-label="Delete">
  <Trash2 className="w-4 h-4" />
</button>

// Icon with rotation (for RTL)
<ChevronRight className="w-4 h-4 rtl:rotate-180" />
```

---

## USAGE EXAMPLES

### Example 1: Module Card (Operations)

```jsx
export function ModuleCard({
  icon: Icon,
  title,
  count,
  status,
  color,
  onClick,
}) {
  return (
    <button
      onClick={onClick}
      className={`group relative p-6 rounded-lg border text-start transition-all duration-200 hover:shadow-lg hover:scale-102 ${color.bg} ${color.border}`}
    >
      <div className="flex items-start justify-between mb-4">
        <Icon className={`w-6 h-6 ${color.text}`} />
      </div>

      <h4 className={`font-semibold text-lg mb-1 ${color.text}`}>
        {title}
      </h4>

      <p className={`text-sm mb-4 ${color.muted}`}>
        {count} {status}
      </p>

      <span className={`text-sm font-medium ${color.link} group-hover:underline`}>
        Open {title} →
      </span>
    </button>
  );
}

// Usage
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  <ModuleCard
    icon={Briefcase}
    title="Projects"
    count={48}
    status="Active · 3 Delayed"
    color={{
      bg: "bg-blue-50 dark:bg-blue-900/20",
      border: "border-blue-200 dark:border-blue-800",
      text: "text-blue-600 dark:text-blue-400",
      muted: "text-blue-700 dark:text-blue-300",
      link: "text-blue-600 dark:text-blue-400",
    }}
    onClick={() => navigate("/projects")}
  />
</div>
```

### Example 2: Data Table

```jsx
export function DataTable({ columns, data, isLoading }) {
  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="overflow-x-auto border border-border rounded-lg">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            {columns.map(col => (
              <th
                key={col.key}
                className="text-start px-4 py-3 font-semibold text-muted-foreground"
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map(row => (
            <tr
              key={row.id}
              className="border-b border-border hover:bg-muted/50 transition-colors"
            >
              {columns.map(col => (
                <td key={col.key} className="px-4 py-3">
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Usage
<DataTable
  columns={[
    { key: "code", label: "Code" },
    { key: "name", label: "Project Name" },
    { key: "status", label: "Status", render: (status) => <Badge>{status}</Badge> },
  ]}
  data={projects}
  isLoading={isLoading}
/>
```

### Example 3: Form Group

```jsx
export function FormGroup({
  label,
  type = "text",
  placeholder,
  error,
  hint,
  required,
  ...props
}) {
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">
        {label}
        {required && <span className="text-destructive ms-1">*</span>}
      </label>

      <input
        type={type}
        placeholder={placeholder}
        className={`w-full px-3 py-2 text-sm border rounded-lg bg-input text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary ${
          error ? "border-destructive" : "border-border"
        }`}
        {...props}
      />

      {error && <p className="text-xs text-destructive">{error}</p>}
      {hint && !error && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

// Usage
<FormGroup
  label="Email"
  type="email"
  placeholder="you@example.com"
  hint="We'll never share your email"
  required
/>
```

---

## DESIGN SYSTEM MAINTENANCE

### When to Update Design Tokens

1. **Color Changes**: Regenerate all affected components
2. **Spacing Changes**: Test responsive layouts
3. **Typography Changes**: Verify readability
4. **Component Additions**: Document with specs above

### Component Checklist

Before adding a new component:

- [ ] Define purpose and use cases
- [ ] Specify dimensions (height, padding, min-width)
- [ ] Define color scheme (light/dark)
- [ ] Create hover/focus/active states
- [ ] Test keyboard accessibility
- [ ] Test screen reader compatibility
- [ ] Document in this Design System
- [ ] Add example usage
- [ ] Create reusable component file

### Component File Structure

```
components/
├── ui/
│   ├── button.tsx
│   ├── input.tsx
│   ├── card.tsx
│   ├── badge.tsx
│   ├── modal.tsx
│   └── ...
├── data-table.tsx
├── form-group.tsx
├── module-card.tsx
└── ...
```

---

## SUMMARY

This design system provides:

✅ **Consistent spacing** (4px base unit)  
✅ **Clear typography** (hierarchical scales)  
✅ **Semantic colors** (brand + status)  
✅ **Reusable components** (button, card, input, etc.)  
✅ **Pattern library** (layouts, forms, tables, empty states)  
✅ **Professional shadows** (elevation hierarchy)  
✅ **Smooth animations** (transitions, durations)  
✅ **Responsive design** (mobile-first breakpoints)  
✅ **WCAG AA accessibility** (colors, keyboard, ARIA)  
✅ **Dark mode support** (automatic color switching)  
✅ **RTL support** (Arabic/RTL layouts)  
✅ **Icon consistency** (lucide-react library)  

**Result**: Professional enterprise platform with consistent, accessible, responsive UI.

Use this as a reference when implementing the UX redesign. All components should follow these specifications for consistency.
