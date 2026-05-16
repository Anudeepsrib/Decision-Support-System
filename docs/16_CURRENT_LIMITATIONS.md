# KSERC Decision Support System — Current Limitations (Honest Assessment)

**Date of this assessment:** Current `mvp-demo` branch  
**Purpose:** Prevent over-promising to stakeholders, regulators, or Phase 2 engineers.

---

## 1. LLM / AI Narrative — Completely Absent

- **Fact:** `prompts.py` contains only deterministic string templates. No OpenAI, Anthropic, or local LLM call exists anywhere in the runtime path.
- **Evidence:** `test_ai_safety.py` asserts that no generative model is invoked.
- **Consequence:** All explanatory text in the PDF is formulaic. Phase 2 is required for natural-language Commission-style paragraphs.

**Do not say:** "The AI writes the order."  
**Correct statement:** "The system deterministically assembles the tables and basic variance statements. Human officers draft the regulatory narrative."

---

## 2. SBU-G / SBU-T / Energy / Common Expenses Coverage Is Conditional

- Target table detection (`table_targets.py`) and canonical aliases exist for these chapters.
- However, **actual coverage depends entirely on whether the uploaded PDF contains tables whose captions match the catalog**.
- In the included sample PDFs:
  - SBU-D: Substantive / reliable
  - SBU-G: Partial (some targets match)
  - SBU-T, Energy/T&D, Common Expenses: Frequently "Missing" or "Fallback only"

**In the generated PDF appendix you will see explicit "Missing" rows.** This is working as designed.

**Do not claim:** "Full multi-SBU automation."  
**Correct statement:** "Strong SBU-D coverage today. SBU-G/T expansion is the primary goal of Phase 1.5."

---

## 3. No Final Regulatory Authority

- The system produces a **draft** only (`is_draft=true`, watermark "DRAFT GENERATED FOR REVIEW").
- No workflow exists to "finalize" and remove the draft status.
- The Commission still makes every legal and financial determination.

---

## 4. No OCR by Default

- `OCR_ENABLED=false`
- Scanned/image-based PDFs will have poor or zero extraction unless the flag is enabled and Tesseract is installed and in PATH.
- Most current test PDFs are text-extractable.

---

## 5. PDF Layout Limitations

- Table of Contents page numbers are approximate (no two-pass layout in ReportLab path).
- The system does not attempt to produce 200+ page historical-style orders by padding content.
- Complex multi-page table continuations can sometimes be fragmented.

---

## 6. No Production Security / Auth / Audit Logging

- JWT and user models exist in skeleton form but are bypassed in `DEMO_MODE=true`.
- No role-based access control (officer vs senior vs admin).
- Audit trail (`/api/audit`) exists but is basic (no cryptographic chaining or tamper-evidence yet).
- File upload has size and type checks but is not hardened for a public-facing deployment.

---

## 7. No Multi-User or Collaboration Features

- Single local SQLite DB.
- No locking, no concurrent review sessions, no comment threading.

---

## 8. Extraction Is Caption-Sensitive

- A table titled "ARR&ERC of SBU-G" may be detected while "ARR and ERC of SBU G" may not, depending on exact pattern.
- Real-world KSEB petitions will require additional `TargetTable` entries. This is expected engineering work, not a bug.

---

## 9. No Automated Regression for Real Petitions

- The fidelity tests (`test_reference_pdf_fidelity.py`) only protect against regressions on the included sample PDFs.
- There is no corpus of 50 real anonymized petitions with ground-truth mappings yet.

---

## 10. Frontend State Limitations

- Viewing extraction for ARR overwrites the petition extraction object in React state (UI lists still show both documents).
- No "save draft review" across browser refresh without completing the full flow.

---

## 11. No Integration With External Systems

- No connection to KSERC's document management system, e-filing portal, or email workflow.
- Output PDF must be manually downloaded and uploaded elsewhere.

---

## 12. Performance

- Extraction of a 200-page petition can take 30–90 seconds on a typical laptop (pdfplumber is CPU-bound).
- Not optimized for concurrent users.

---

## What the MVP *Does* Reliably Do (Counter-Balance)

- End-to-end deterministic flow from two PDFs to a formatted draft order
- Strong SBU-D coverage with full provenance
- Transparent "Missing" / "Fallback" reporting for other SBUs
- Officer review with mandatory justification
- SHA-256 integrity on generated PDFs
- Zero hallucinated numbers (by design)
- Local, air-gapped capable (no external API calls required)

---

## How to Use This Document

- Before any stakeholder meeting, the presenter must read this document and the demo script together.
- Any claim not supported by the smoke test + the Extraction Coverage appendix in the generated PDF is out of scope for the current MVP.

**This document will be updated with each phase completion.** Phase 1.5 will remove or narrow several of the SBU coverage items above.
