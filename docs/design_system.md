# Front-end Design System

## Core Aesthetic Principles
The `OrderComparison.tsx` UI is rigorously optimized for visually triaging structural data comparisons instantly under pressure. The layout was heavily upgraded utilizing tailwind primitives.

1. **Space Optimization:** Extreme space efficiency dividing the screen into left (Order Document) and right (Reference Document) hemispheres seamlessly.
2. **Instant Visual Triage (Emojis):** The visual system deploys heavy Anomaly Emojis for zero-latency human comprehension of the discrepancy tables.
   - ✅ **Match:** Verified items.
   - ❌ **Mismatch:** Identified mismatches between documents (fails difflib/numeric tolerances).
   - ⚠️ **Missing:** Items identified in the order document not found in the reference document.
   - ℹ️ **Extra:** Spurious items found in the reference document not claimed in the order document.
   - 🚨 **Risk / Alert:** Highlighting severe confidence drops.

3. **Contrast and Legibility:** Deep sophisticated dark modes (`slate-900`) mixed with precise border coloring. 
   - Strict red backgrounds (`#ef4444`) trigger actively behind any `MISMATCH` table rows, ensuring humans physically cannot miss discrepancies.
   - Emerald borders frame absolute matches.
   - Yellow frames highlight partial omissions.

## Implementation Artifacts
The entire application adopts TailwindCSS natively. A custom SVG Confidence Ring dynamically renders circle circumferences calculated mathematically from the Confidence Metric output array. CSS-only distribution bars chart absolute findings.
