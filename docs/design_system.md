# Data-Dense Executive Dashboard — Design System

## Core Aesthetic Principles
The Front-end is rigorously optimized for viewing mass quantities of financial extraction data efficiently without scroll-fatigue.

1. **Space Optimization:** Extreme space efficiency through padding reductions and minimized whitespace bridging tabular data displays.
2. **Precision Typography:** Monospaced typefaces (`Fira Code` for digits) to align accounting decimals perfectly. Legible sans-serifs (`Fira Sans`) for overarching descriptions.
3. **Contrast and Legibility:** Deep sophisticated dark modes mixed with specific accent colors to identify system states cleanly without blinding users in low-light office environments.

## Color Tracking Tokens
- **Backgrounds:** `#0f172a` (Slate 900)
- **Surfaces/Cards:** `#1e293b` (Slate 800)
- **Primary Text:** `#f8fafc` (Slate 50) 
- **Muted Text:** `#94a3b8` (Slate 400)
- **Action/Primary Buttons:** `#3b82f6` (Blue 500)
- **Success States (Validation):** `#10b981` (Emerald 500)
- **Destructive/Error States:** `#ef4444` (Red 500)

## Implementation Artifacts
The entire application adopts TailwindCSS natively referencing these variables through `index.css` inside `frontend/src`. Heroicons are utilized natively for all vector graphics seamlessly avoiding bulky PNG/JPG artifacts.
