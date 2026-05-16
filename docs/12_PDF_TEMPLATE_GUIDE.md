# KSERC Decision Support System — PDF Template Guide

**Purpose:** How the KSERC-style draft order PDF is actually produced, and how to modify formatting safely.

---

## Two Rendering Paths

| Engine | `PDF_ENGINE` value | Implementation | When to use |
|--------|--------------------|----------------|-------------|
| **ReportLab** (default) | `reportlab` | `SimpleDocTemplate`, `Paragraph`, `Table`, `TableStyle` in `pdf_generator.py` | Local demos, CI, most reliable |
| **Playwright** | `playwright` | `kserc_order.html` + `kserc_order.css` rendered via headless Chromium | Pixel-perfect HTML fidelity, future Phase 2 narrative work |

Both paths are required to produce **identical regulatory content** — only the layout engine differs.

---

## ReportLab Path (Current Default)

The code in `pdf_generator.py` builds the document using:

- Custom `ParagraphStyle` objects (Heading1, Heading2, BodyText, TableCell, Small, etc.)
- `Table` + `TableStyle` for all financial tables (alternating row colors, grid, alignment)
- `PageBreak`, `Spacer`, `KeepTogether`
- Header/footer via `onFirstPage` / `onLaterPages` callbacks (page numbers, "DRAFT" watermark)

The visual goal is "Commission order" rather than "modern web dashboard".

---

## HTML + CSS Path (Playwright)

Files:
- `backend/templates/kserc_order.html`
- `backend/templates/kserc_order.css`
- `backend/templates/components/*.html`

The HTML is semantic:
- `<section class="chapter">`
- `<table class="regulatory">`
- `<div class="toc">`
- Signature block with lines for Member, Secretary, etc.

CSS contains KSERC-inspired rules:
- Serif headings
- Justified body text
- Table borders and shading matching historical orders
- Page `@media print` rules
- Watermark and "DRAFT" ribbon

**When using Playwright**, you must have run:
```bash
python -m playwright install chromium
```

---

## What Is Strictly Banned from the Output PDF

The generator contains two enforcement mechanisms:

1. `BANNED_PDF_STRINGS` constant in `pdf_generator.py`
2. `_BANNED_REPORT_PATTERNS` in `report_context.py`

**Never allow the following to appear in the final PDF:**

- `raw_label`, `normalized_label`, `source_page`, `confidence`, `document_type`
- Any extraction debug metadata
- Tariff schedule language: "0 to 100 units", "Single phase", "Three phase", "Fixed Charge", "Energy Charge", "Rs./kVA"
- Placeholder regulatory text: "Documents considered - Part", "Views of the Commission - Part", "Chapter decision - Part", "Stakeholder comments - Part"
- Any invented regulatory citation or number not present in the comparison data

If banned content is detected, the generator either drops the element or raises an error (depending on severity).

---

## Safe Modification Patterns

### Adding a New Column to a Chapter Table

1. Ensure the column exists in the `report_context` data for that chapter (edit `report_context.py`)
2. Add the header in the table header list
3. Add the corresponding `TableStyle` or `<th>` in the template
4. Update any appendix that documents column sources
5. Test with `test_pdf_generation.py` and `test_reference_pdf_fidelity.py`

### Changing Table Styling

- Edit `kserc_order.css` (for Playwright)
- Edit the `TableStyle` list in `pdf_generator.py` (for ReportLab)
- Keep colors muted (blues, grays) — avoid bright modern palettes

### Adding a New Appendix

1. Compute the data in `build_report_context()`
2. Add a new section render function in `pdf_generator.py`
3. Add the appendix title to the TOC
4. Document the appendix in [11_REPORT_GENERATION.md](11_REPORT_GENERATION.md)

### Changing Page Margins or Fonts

- ReportLab: `SimpleDocTemplate(..., leftMargin=1.5*cm, ...)` and `ParagraphStyle(fontName=...)`
- Playwright: `@page { margin: ... }` and `font-family` in CSS

---

## Page Numbering Limitations (Known)

The current ReportLab implementation uses a simple page counter. It does **not** perform a two-pass layout to get perfect "Page X of Y" or accurate TOC page numbers for long documents.

For a production-grade KSERC order, a two-pass or WeasyPrint-style layout engine would be required. The MVP accepts "close enough" page numbers in the TOC.

---

## Do Not Do These Things

- Do **not** add raw `ExtractedRow` dumps "for debugging" into the PDF
- Do **not** increase font sizes or add blank pages to force a particular page count (e.g., "must be 237 pages")
- Do **not** embed the full extraction confidence matrix in the main body — only the appendix
- Do **not** let LLM-generated text bypass the banned-string filter (Phase 2 requirement)

---

## Verification Commands

After any template change:

```bash
# Regenerate a known-good PDF
python scripts/smoke_test.py

# Visual regression (if reference images exist)
pytest test_reference_pdf_fidelity.py -v

# HTML-only preview (useful for Playwright path debugging)
python test_pdf_html_only.py
```

The `output/` directory will contain the new PDF. Compare it visually against previous known-good outputs.

---

**The PDF output is the single most visible artifact of the entire system.** Every change here must be reviewed against the "deterministic + traceable + no hallucination" contract.
