# Sample PDF for Demo Extraction

This directory contains sample PDF documents for demonstrating the AI extraction pipeline.

## Contents

- `sample_petition.pdf` — Simulated ARR Truing-Up petition (24 pages)
- `sample_audited_accounts.pdf` — Simulated audited financial statements
- `sample_obscured.pdf` — Document with partial obstructions (tests confidence scoring)

## Sample Petition Contents

The sample_petition.pdf simulates a real KSERC petition with:

**Table 38 — Revenue Surplus/Gap:**
- Page 12: Approved O&M: ₹180 Cr
- Page 14: Actual O&M: ₹150 Cr
- Page 16: Variance: +₹30 Cr (Gain)

**Table 39 — Approved ARR & ERC:**
- Page 18: Power Purchase Approved: ₹400 Cr
- Page 19: Power Purchase Actual: ₹450 Cr
- Page 20: Variance: -₹50 Cr (Loss)

**Schedule 12 — Employee Costs:**
- Page 14, Table 2, Cell B4: Salaries & Wages
- Page 14, Table 2, Cell C4: Allowances

**Intentional Issues (for demo):**
- Page 22: Table partially obscured (tests low confidence)
- Page 24: Smudged text (tests anomaly detection)

## Usage

Upload these files via the frontend "Upload PDF" feature to see:
1. Automatic table detection
2. Field extraction with confidence scores
3. Page/table/cell provenance
4. Review flags for obscured areas

## Note

These are simulated documents for demonstration only.
They contain realistic structure but fictitious data.
Safe to delete after demo.
