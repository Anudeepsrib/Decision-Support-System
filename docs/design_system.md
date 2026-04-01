# Design System & UI/UX Guide

*Visual Language for KSERC Truing-Up Decision Support System*

---

## Design Philosophy

The interface is designed for **high-stakes regulatory decision-making** under time pressure. Every visual element prioritizes:

1. **Clarity**: Zero ambiguity in decision status
2. **Efficiency**: Minimal clicks to complete tasks
3. **Trust**: Visual cues reinforcing system reliability
4. **Authority**: Professional appearance befitting regulatory commission

---

## Color System

### Primary Palette

| Color | Hex | Usage |
|-------|-----|-------|
| **Navy Blue** | `#1e3a6e` | Header, primary buttons, navigation |
| **Royal Blue** | `#2c5282` | Active states, links, icons |
| **Sky Blue** | `#93c5fd` | Accent highlights, hover states |
| **White** | `#ffffff` | Backgrounds, cards |
| **Slate Gray** | `#f0f4f8` | Page backgrounds, sections |

### Decision Mode Colors

| Mode | Background | Border | Text |
|------|------------|--------|------|
| **[A] AI Auto** | `#E8F5E9` | `#4CAF50` | `#2E7D32` |
| **[P] Pending** | `#FFF3E0` | `#FF9800` | `#EF6C00` |
| **[M] Manual Override** | `#FFEBEE` | `#F44336` | `#C62828` |

### Semantic Colors

| Purpose | Color | Hex |
|---------|-------|-----|
| Success | Green | `#4CAF50` |
| Warning | Amber | `#FF9800` |
| Error | Red | `#F44336` |
| Info | Blue | `#2196F3` |
| External Factor | Orange | `#F57C00` |
| High Variance | Red | `#C62828` |

---

## Typography

### Font Stack

```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
```

### Type Scale

| Element | Size | Weight | Line Height |
|---------|------|--------|-------------|
| Page Title | 24px | 700 (Bold) | 1.2 |
| Section Header | 18px | 600 (Semibold) | 1.3 |
| Card Title | 16px | 600 (Semibold) | 1.4 |
| Body Text | 14px | 400 (Regular) | 1.6 |
| Small Text | 12px | 400 (Regular) | 1.5 |
| Caption | 11px | 500 (Medium) | 1.4 |
| Data/Numbers | 14px | 600 (Semibold) | 1.2 |

---

## Components

### 1. Decision Cards

**Pending Decision Card:**
```
┌─────────────────────────────────────────┐
│ [O&M]                     [P] Pending   │  ← Header with badge
│ Approved: ₹145 Cr | Actual: ₹148 Cr     │  ← Values
│ Variance: 2.1%                          │  ← Variance
│ AI: APPROVE (92% confidence)            │  ← AI recommendation
│ ⚠️ External: Hydrology                  │  ← Warning (if any)
└─────────────────────────────────────────┘
```

**Reviewed Decision Card:**
```
┌─────────────────────────────────────────┐
│ [Power Purchase]            ✓ Reviewed  │  ← Header with status
│ Final: PARTIAL                          │  ← Officer decision
│ ₹450 Cr approved of ₹480 Cr claimed     │  ← Final value
└─────────────────────────────────────────┘
```

### 2. Decision Mode Badges

| Badge | Style |
|-------|-------|
| [A] AI Auto | Green background, green border, green text |
| [P] Pending | Orange background, orange border, orange text |
| [M] Manual Override | Red background, red border, red text |

### 3. Progress Indicator

```
Progress: 65%                    13 / 20 reviewed
████████████████████░░░░░░░░░░░░░░░░
Pending: 7 | External Factors: 2 | High Variance: 1
```

**Visual specs:**
- Progress bar height: 8px
- Border radius: 4px
- Fill: Linear gradient from `#4CAF50` to `#8BC34A`
- Animation: Smooth 0.3s transition on update

### 4. Form Elements

**Review Form Panel:**
```
┌─────────────────────────────────────────┐
│ Review Decision                         │
├─────────────────────────────────────────┤
│ AI ANALYSIS (Read-Only)                 │
│ ─────────────────────────────────────  │
│ Cost Head: Power Purchase              │
│ AI Recommendation: PARTIAL             │
│ Confidence: 78%                        │
│ Justification: Variance approaching...   │
│ Regulatory Basis: Regulation 9.4      │
├─────────────────────────────────────────┤
│ OFFICER DECISION                        │
│ ─────────────────────────────────────  │
│ Final Decision: [APPROVE ▼]            │
│ Approved Value: [₹450,000,000.00]      │
│ Justification: [_________________]   │
│              [_________________]       │
│ External Factor: [Hydrology ▼]         │
│                                         │
│ [Cancel]        [Submit Decision]       │
└─────────────────────────────────────────┘
```

### 5. Order Preview

**Draft Watermark:**
- Text: "DRAFT — PENDING REVIEW"
- Rotation: -45 degrees
- Position: Center of page
- Style: 72px font, red (#F44336), 15% opacity
- Only appears when `has_pending_decisions=true`

### 6. Navigation

**Top Navigation Bar:**
- Height: 60px
- Background: Linear gradient (navy to royal blue)
- Logo: Left-aligned with KSERC branding
- User Card: Right-aligned with role badge
- Role Badge Colors:
  - Super Admin: Light blue background
  - Regulatory Officer: Light green background
  - Senior Auditor: Light yellow background
  - Data Entry Agent: Light cyan background
  - Readonly Analyst: Light purple background

**Sidebar Navigation:**
- Width: 240px (collapsible to 64px)
- Active Item: Blue left border, light blue background
- Icons: 20px, consistent with labels

---

## Layout Principles

### Manual Decisions Workbench

```
┌─────────────────────────────────────────────────────────┐
│ Header: Manual Decisions Workbench    [SBU Selector ▼] │
├─────────────────────────────────────────────────────────┤
│ Progress: 65% ████████████████░░░░  13/20 reviewed     │
│ Pending: 7 | External: 2 | High Variance: 1             │
├──────────────────────────┬────────────────────────────┤
│                          │                            │
│  PENDING DECISIONS (7)   │    REVIEW FORM             │
│  ┌──────────────────┐   │    ┌────────────────────┐  │
│  │ [O&M]   [P]      │   │    │ Review Decision    │  │
│  │ ₹145 Cr → ₹148   │   │    │ ─────────────────  │  │
│  │ AI: APPROVE      │   │    │ AI Analysis...     │  │
│  └──────────────────┘   │    │ ─────────────────  │  │
│  ┌──────────────────┐   │    │ Your Decision...   │  │
│  │ [Power] [P] ⚠️   │   │    │ [Submit]           │  │
│  │ External: Hydro  │◄──┼────│                    │  │
│  └──────────────────┘   │    └────────────────────┘  │
│                          │                            │
│  REVIEWED (13)          │                            │
│  ┌──────────────────┐   │                            │
│  │ [Interest] ✓    │   │                            │
│  │ Final: DISALLOW │   │                            │
│  └──────────────────┘   │                            │
│                          │                            │
└──────────────────────────┴────────────────────────────┘
```

### Responsive Breakpoints

| Breakpoint | Width | Layout Changes |
|------------|-------|----------------|
| Desktop XL | ≥1400px | Full 2-column workbench |
| Desktop | 1024-1399px | Slightly compressed |
| Tablet | 768-1023px | Stacked layout, collapsible nav |
| Mobile | <768px | Single column, hamburger menu |

---

## Icons & Visual Indicators

### Status Icons

| Icon | Meaning | Unicode |
|------|---------|---------|
| ✅ | Exact Match / Approved | U+2705 |
| ❌ | Mismatch / Disallowed | U+274C |
| ⚠️ | Warning / Pending Review | U+26A0 |
| ℹ️ | Information / Extra Item | U+2139 |
| 🚨 | Critical Alert | U+1F6A8 |
| ✓ | Reviewed / Confirmed | U+2713 |
| 🎉 | All Complete | U+1F389 |

### External Factor Icons

| Factor | Icon |
|--------|------|
| Hydrology | 🌧️ Rain cloud |
| Power Purchase | ⚡ Lightning |
| Government | 🏛️ Building |
| Court | ⚖️ Scales |
| CapEx | 💰 Money with wrench |
| Force Majeure | 🌪️ Tornado |

---

## Animation & Interactions

### Micro-interactions

**Card Hover:**
- Border color: `#ddd` → `#2196F3`
- Box shadow: `0 2px 4px rgba(0,0,0,0.1)`
- Transition: `all 0.2s ease`

**Button States:**
```
Primary Button:
- Default: Blue background, white text
- Hover: Darker blue, subtle shadow
- Active: Even darker, inset shadow
- Disabled: Light blue, no pointer events
- Loading: Spinner animation, text hidden
```

**Progress Bar:**
- Fill animation: 0.3s ease-out
- Color pulse on completion

### Page Transitions

```css
/* Fade-in on route change */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.page-transition {
  animation: fadeIn 0.25s ease;
}
```

---

## Accessibility

### WCAG 2.1 Compliance

- **Color Contrast**: All text meets 4.5:1 ratio minimum
- **Focus Indicators**: 2px blue outline on all interactive elements
- **Screen Readers**: ARIA labels on all icons and interactive elements
- **Keyboard Navigation**: Full tab navigation support
- **Reduced Motion**: Respect `prefers-reduced-motion` media query

### ARIA Labels

```html
<button aria-label="Submit decision for Power Purchase review">
  Submit Decision
</button>

<div role="progressbar" aria-valuenow="65" aria-valuemin="0" aria-valuemax="100">
  Progress: 65%
</div>

<span aria-label="External factor: Hydrology detected">
  ⚠️ Hydrology
</span>
```

---

## Design Tokens

### Spacing Scale

| Token | Value | Usage |
|-------|-------|-------|
| `space-xs` | 4px | Tight spacing, icon gaps |
| `space-sm` | 8px | Component internal padding |
| `space-md` | 16px | Card padding, form gaps |
| `space-lg` | 24px | Section gaps |
| `space-xl` | 32px | Page sections |
| `space-2xl` | 48px | Major divisions |

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `radius-sm` | 4px | Buttons, inputs |
| `radius-md` | 6px | Cards, panels |
| `radius-lg` | 8px | Modals, large containers |
| `radius-full` | 9999px | Pills, badges |

### Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle depth |
| `shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | Cards, panels |
| `shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)` | Modals, dropdowns |

---

<div align="center">

**Design with Purpose. Build with Precision.**

</div>
