# KSERC Decision Support System — Stakeholder Demo Script (Honest Version)

**Duration:** 8–12 minutes for a full walk-through  
**Audience:** Commission members, utility officers, IT leadership, regulators

---

## Opening (30 seconds)

"Good morning. Today I will demonstrate a **local, deterministic decision-support tool** that helps regulatory officers prepare draft truing-up orders for KSERC.

This is a **Minimum Viable Product**. It performs the mechanical work of extraction, mapping, variance calculation, and document formatting so that officers can focus on judgment. It does **not** replace the Commission, and it does **not** use large language models for any decision or narrative in the current version."

---

## Step 1: Problem Statement (1 minute)

- Show two sample PDFs on screen: `arr_order_test.pdf` (ARR Order) and `petition_test.pdf` (Truing-Up Petition).
- "An officer today must manually locate 50–80 financial line items across 200+ pages, reconcile different wording, calculate variances, classify which need review, and then draft a 30–100 page order."
- "This MVP automates the first 80% of that work deterministically."

---

## Step 2: Upload ARR Order (1 minute)

1. Open http://127.0.0.1:5173
2. Go to **ARR Upload** tab
3. Drag `arr_order_test.pdf`
4. Watch the job status poll until "Extraction completed — X rows"
5. "Notice: the system used pdfplumber to find tables, matched them against our target catalog, and mapped the rows to our canonical KSERC line-item registry. Everything is logged with page and table provenance."

---

## Step 3: Upload Petition (1 minute)

1. Switch to **Petition Upload** tab
2. Upload `petition_test.pdf`
3. Same extraction flow
4. "Now we have both the approved values (from the ARR Order) and the actual/claimed values (from the Petition)."

---

## Step 4: Extraction Results (30 seconds)

- Go to **Extraction** tab
- Show side-by-side row counts
- "Both documents are now in the database with full source traceability."

---

## Step 5: Run Comparison (1 minute)

1. Click **Run Comparison** (or it may have auto-triggered)
2. "The comparison engine just performed pure arithmetic on every canonical line item that existed in both documents."
3. "Variance = Actual (or Claimed fallback) − Approved"
4. "Percentage = Variance / |Approved| × 100"
5. "Threshold: 15%. Items under 15% with good confidence are marked ACCEPTABLE_VARIANCE. Items over 15%, or with missing data, or low extraction confidence, are flagged for officer review."

---

## Step 6: Review the Comparison Dashboard (2 minutes)

- Switch to **Comparison** tab
- Scroll through the table
- Point out SBU column (mostly SBU-D in current sample)
- Show green vs amber rows
- Click one amber row → show the review panel
- "Officer must enter a justification comment. The system will not let you submit without it. This becomes part of the audit trail and appears in the final draft order."
- (Optional) Perform one quick "Approve" action to show the flow

**Honest statement here:**
"Right now the sample PDFs give us strong coverage on SBU-D (Distribution). SBU-G and SBU-T coverage depends on whether the petition PDF contains tables whose captions match our target table catalog. If a chapter has no mapped data, it will appear as 'Missing' in the report — we do not fabricate content."

---

## Step 7: Generate the KSERC-Style Draft Order (1 minute)

1. Go to **Generate** tab
2. Click **Generate KSERC Draft Order**
3. "This is 100% deterministic. No LLM wrote any number or any sentence. The PDF generator consumed only the comparison rows that successfully mapped to our canonical registry."
4. Wait for "Report generated" message
5. Click **Download PDF** or open the preview link

---

## Step 8: Walk Through the Generated PDF (2–3 minutes)

Open the PDF and narrate:

1. **Title page** — "KSERC Truing-Up Order — Financial Year 2024-25 — DRAFT GENERATED FOR REVIEW"
2. **Table of Contents** — note that page numbers are approximate in the MVP
3. **Chapter 5 (SBU-D)** — the main chapter with detailed tables
4. **Variance columns** and decision flags
5. **Appendix: Extraction Coverage Summary** — this is the most important slide for honesty
   - Show the table that lists each chapter: Full / Fallback / Missing
   - "SBU-D is Full. SBU-G may be Full or Fallback. Energy/T&D and Common Expenses are often Missing in the current sample. This appendix tells the officer exactly what data was available and what was not."
6. **Signature block** — placeholder for the three Commission members

**Key talking point:**
"Every number you see has a source page and table reference in the appendix. An officer can go back to the original PDFs and verify in under 60 seconds per line item."

---

## Step 9: Limitations & Phase 2 (1 minute)

"This is a **draft-order generator**, not a final-order generator.

What it does **not** do today:
- It does not make the final regulatory decision — that is still the Commission's job.
- It does not yet have complete target table coverage for SBU-G and SBU-T on every possible petition format.
- It does not use any large language model. All narrative text is deterministic templates.
- It is not connected to any production database or document management system.

Phase 2 (already planned) will introduce a **gated LLM layer** that can draft the explanatory paragraphs for each chapter, but only **after** the deterministic tables are built, and only under strict citation and value validators. The LLM will never be allowed to change a number or invent a regulation."

---

## Step 10: Q&A Prompts (Prepare These Answers)

**Q: "Is this production-ready?"**  
A: "It is demo-ready and developer-extendable. Production readiness (roles, audit logging, deployment, OCR for scanned PDFs, full SBU-G/T coverage) is Phase 3 work."

**Q: "How accurate is the extraction?"**  
A: "On the included sample PDFs, SBU-D line items are reliably extracted and mapped. Real KSEB petitions may require additional target table patterns — that is expected and low-risk to add."

**Q: "What happens if the PDF is scanned?"**  
A: "OCR is supported in the code but disabled by default (`OCR_ENABLED=false`). We would need Tesseract installed and the flag turned on."

**Q: "Can the system hallucinate a number?"**  
A: "No. The only numbers that appear in the PDF are the ones that came out of pdfplumber from the source documents and survived canonical mapping. There is no generative model in the loop."

---

## Closing (15 seconds)

"This MVP proves that the most error-prone and time-consuming parts of truing-up order preparation can be made deterministic, auditable, and fast. The human expert remains firmly in the loop for judgment and final approval.

We are ready to discuss Phase 1.5 (completing SBU-G/T extraction coverage) and the safe architecture for Phase 2 LLM assistance."

---

**Print or bookmark this script.** It is written to be spoken while operating the live system. Never claim capabilities that the smoke test and the generated PDF appendix do not support.
