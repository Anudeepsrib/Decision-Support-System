# KSERC Decision Support System — Project Overview

**Audience:** Stakeholders, regulatory officers, new developers, demo presenters

---

## What is "Truing-Up"?

In the Kerala State Electricity Regulatory Commission (KSERC) framework, utilities (KSEB Ltd) submit:

1. **Annual Revenue Requirement (ARR) filings** — projected costs and revenue for the upcoming year.
2. **Truing-Up Petitions** — after the financial year ends, the utility files actual audited figures and "trues up" the difference between what was approved in the ARR Order and what actually occurred.

The **Truing-Up Order** is the Commission's formal determination of:
- How much of the variance is approved, disallowed, or adjusted
- Any revenue gap/surplus that will be recovered from or refunded to consumers in future tariffs
- Regulatory findings on controllable vs. uncontrollable costs, external factors, etc.

This process is highly structured, citation-heavy, and must follow KSERC regulations and the Electricity Act 2003.

---

## Why This System Exists

Manual preparation of a truing-up draft order from two large PDFs (ARR Order + Petition) is extremely time-consuming. Officers must:

- Locate dozens of financial tables across hundreds of pages
- Map line items that use slightly different wording between documents
- Calculate variances (approved vs actual vs claimed)
- Classify items as acceptable, requiring review, or incomplete
- Draft Commission-style narrative with regulatory citations
- Produce a consistent, paginated, professionally formatted PDF

The MVP automates the **mechanical, auditable, deterministic parts** so that human experts can focus on judgment.

---

## What the MVP Automates Today (Phase 1)

| Step | Description | Technology | Deterministic? |
|------|-------------|------------|----------------|
| ARR PDF Upload | Store + trigger extraction | FastAPI + pdfplumber | Yes |
| Petition PDF Upload | Store + trigger extraction | FastAPI + pdfplumber + target tables | Yes |
| Table Extraction | Financial rows with page/table provenance | pdfplumber + caption matching | Yes |
| Canonical Mapping | Raw labels → stable KSERC line items | Rule-based registry + aliases | Yes |
| Variance Comparison | approved vs actual vs claimed | Pure arithmetic (15% threshold) | Yes |
| Decision Classification | ACCEPTABLE / REVIEW_REQUIRED / INCOMPLETE | Deterministic rules + confidence | Yes |
| Officer Review | Record approve/edit/reject + comment | Database + audit trail | Yes |
| Report Context Builder | Chapters 2–7 with full/fallback/missing modes | Python dataclasses | Yes |
| KSERC-style PDF | Title page, TOC, chapters, tables, signature block | ReportLab + HTML templates + CSS | Yes |

**No LLM is invoked anywhere in the current execution path.**

---

## What Remains Human-Reviewed (Correctly)

- Final regulatory approval or adjustment of values
- Determination of "controllable loss" vs external factors (hydrology, force majeure, etc.)
- Drafting of narrative paragraphs that cite specific regulations or prior orders
- Legal conclusions and consumer impact statements
- Any policy or discretionary decisions

The system produces a **high-quality draft** that an officer can edit, not a final order.

---

## Why Deterministic Generation in Phase 1?

- **Auditability**: Every number in the output PDF can be traced back to an exact page and table in the source PDFs.
- **Repeatability**: Same inputs always produce the same comparison and draft.
- **Regulatory safety**: No risk of hallucinated values or invented citations.
- **Officer trust**: The system never "guesses" a number; it only surfaces extracted and mapped data.

Phase 2 will introduce a carefully gated LLM layer **on top of** the deterministic context (see [17_PHASE_2_LLM_PLAN.md](17_PHASE_2_LLM_PLAN.md)).

---

## Current Coverage Reality (Honest Statement)

- **SBU-D (Distribution)**: Strong substantive coverage. Most core cost heads (Power Purchase, O&M, Employee Cost, Interest, Depreciation, RoE, etc.) map reliably when the sample or similar PDFs are used.
- **SBU-G (Generation), SBU-T (Transmission), Energy Sales & T&D Loss, Common Expenses**: Coverage is **conditional**. The extraction pipeline looks for specific table captions defined in `backend/table_targets.py`. If the uploaded PDF contains tables with matching captions, those chapters become "Full" or "Fallback". Otherwise they are reported as "Missing" with the list of attempted target IDs. This is transparent in the UI and in the generated PDF appendix.

This is the expected Phase 1 state. Expanding target table coverage and alias breadth for SBU-G/T is the primary objective of Phase 1.5.

---

## Document Flow Summary

```
ARR Order PDF ──► Upload ──► pdfplumber + Target Tables ──► Canonical Registry
Petition PDF  ──► Upload ──► pdfplumber + Target Tables ──► Canonical Registry
                                                             │
                                                             ▼
                                              Comparison Engine (variance, 15%)
                                                             │
                                                             ▼
                                              Officer Review (approve/edit)
                                                             │
                                                             ▼
                                              Report Context Builder
                                              (Chapters 2-7, coverage modes)
                                                             │
                                                             ▼
                                              PDF Generator (ReportLab)
                                                             │
                                                             ▼
                                              KSERC-style Draft Order PDF
```

All steps after upload are fully automatic until the officer chooses to review flagged items.

---

## Next Steps for the Reader

- Want to run it now? → [03_LOCAL_SETUP.md](03_LOCAL_SETUP.md)
- Want to understand the data model? → [07_DATA_MODEL.md](07_DATA_MODEL.md)
- Preparing a stakeholder demo? → [15_DEMO_SCRIPT.md](15_DEMO_SCRIPT.md) (includes exact honest phrasing)
- Planning Phase 2 LLM work? → [17_PHASE_2_LLM_PLAN.md](17_PHASE_2_LLM_PLAN.md)

This overview is deliberately non-technical. The architecture and implementation documents provide the depth required for engineering work.
