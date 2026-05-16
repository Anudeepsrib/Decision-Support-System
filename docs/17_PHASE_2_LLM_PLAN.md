# KSERC Decision Support System — Phase 2 LLM Integration Plan (Safe Architecture)

**Status:** Planning document only. Zero LLM code exists in the current MVP.

---

## Core Safety Principle

**The LLM must never be the source of truth for any numeric value, regulatory citation, SBU assignment, or legal conclusion.**

The deterministic pipeline (pdfplumber → canonical registry → comparison engine → report_context) remains the single source of truth. The LLM is a **narrative polish layer** that operates **on top of** an already validated context.

---

## What the LLM May Be Allowed to Do (Phase 2)

1. Draft the "Commission's Analysis and Findings" paragraph for each chapter, using the deterministic table data + officer review comments as input.
2. Summarize stakeholder objections (if those are later extracted or entered).
3. Improve transitions between chapters and suggest clearer wording for variance explanations.
4. Generate a plain-language "Key Outcomes" executive summary (subject to officer approval).
5. Propose regulatory citations from a **whitelisted, version-controlled** set of KSERC regulations and Electricity Act sections (never free-form generation).

---

## What the LLM Must NEVER Be Allowed to Do

| Forbidden Action | Why | Enforcement Mechanism |
|------------------|-----|-----------------------|
| Change any approved / actual / claimed / variance value | Violates traceability | Value validator layer rejects any numeric delta |
| Invent a regulatory citation or quote | Regulatory malpractice | Citation validator only accepts IDs from a controlled registry |
| Re-assign a line item to a different SBU | Breaks canonical contract | Mapping validator (LLM output cannot override canonical_id) |
| Decide "approve" or "disallow" on its own | Removes human accountability | Officer review step remains mandatory |
| Generate content when source data is missing | Hallucination risk | LLM prompt must include the "Missing" coverage flags; generation is skipped or heavily caveated for missing chapters |
| Output different numbers in the narrative than in the tables | Inconsistency | Post-generation diff check against report_context numbers |

---

## Proposed Phase 2 Pipeline Architecture

```
1. Deterministic Foundation (already built)
   ├─ Upload → Extraction (pdfplumber + targets)
   ├─ Canonical Mapping (registry)
   ├─ Comparison (15% rules + provenance)
   ├─ Officer Review (mandatory comments)
   └─ build_report_context() → validated JSON context
            │
            ▼
2. LLM Narrative Draft Layer (NEW in Phase 2)
   ├─ Prompt builder (context + officer reviews + allowed citation list)
   ├─ LLM call (OpenAI/Anthropic/local with strict system prompt)
   ├─ Raw LLM output captured for audit
   └─ Output: proposed narrative blocks
            │
            ▼
3. Validation & Guardrail Layer (CRITICAL — must be deterministic)
   ├─ Numeric Integrity Validator (all numbers in LLM text must match context)
   ├─ Citation Validator (every citation must be in the whitelisted set)
   ├─ SBU Consistency Validator
   ├─ Missing-Data Caveat Injector (auto-adds "Data not available for SBU-T..." where coverage=Missing)
   └─ If ANY validator fails → reject the LLM draft, fall back to deterministic template
            │
            ▼
4. Officer Review Queue (enhanced)
   ├─ Officer sees: deterministic tables + LLM-proposed narrative side-by-side
   ├─ "Accept LLM draft", "Edit", or "Reject and write manually"
   ├─ All edits logged with officer identity
   └─ Final approved narrative + tables → report_context v2
            │
            ▼
5. PDF Renderer (unchanged architecture)
   └─ Uses the final validated context (whether LLM was used or not)
```

---

## Technical Guardrails (Must Be Implemented)

1. **Prompt Registry** — All system prompts version-controlled in the repo. No ad-hoc prompts in production.
2. **Temperature = 0.0 or 0.1** — Maximum determinism from the model.
3. **Structured Output / JSON mode** — Force the LLM to return a JSON schema with explicit fields rather than free text.
4. **Citation Registry** — A new Python module `regulatory_citations.py` containing every allowed regulation string. LLM output is diffed against it.
5. **Post-Generation Diff** — A deterministic function that extracts every number from the LLM narrative and asserts equality (within rounding tolerance) with the corresponding value in `report_context`.
6. **Audit Log** — Every LLM call, raw response, validator result, and officer decision is written to an immutable audit table.
7. **Kill Switch** — `LLM_ENABLED=false` in environment (default false until Phase 2 is complete and audited).

---

## Data Contract Extension

`report_context` will gain a new optional section:

```json
{
  "narrative_drafts": {
    "chapter_5_sbu_d": {
      "llm_proposed": "...",
      "llm_model": "gpt-4o-2024-08",
      "llm_prompt_version": "narrative-v1.3",
      "validator_passed": true,
      "officer_decision": "accepted_with_edits",
      "final_text": "..."
    }
  }
}
```

The PDF generator will render the `final_text` (or fall back to the deterministic template if the section is absent).

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM changes a number subtly ("12,450" → "12.45 thousand") | Medium | Critical (regulatory) | Numeric validator + round-trip extraction test |
| LLM invents a plausible-sounding but non-existent regulation | Low (with good prompt) | Critical | Citation whitelist only |
| Officer blindly accepts LLM draft | High (human factors) | High | UI must show "LLM-assisted — review required" banner + mandatory re-read timer |
| Model deprecation / cost explosion | Medium | Operational | Abstract behind a `LLMProvider` interface; support local models (Ollama, vLLM) |
| Prompt injection via uploaded PDF text | Low (current architecture) | High | Sanitize all text that goes into the LLM prompt; never pass raw PDF text |

---

## Phase 2 Entry Criteria (Before Any Code Is Written)

1. Phase 1.5 SBU-G/T extraction coverage is demonstrably improved (more target tables passing on real petitions).
2. The deterministic pipeline has been stable for at least one full quarter of internal use.
3. A written regulatory opinion or internal memo exists stating that LLM-assisted drafting is acceptable provided the guardrails above are in place.
4. Budget and model access (or local GPU) are approved.
5. The validation layer is implemented and has 100% unit test coverage before the first LLM call is ever made in the main branch.

---

## Phase 2 Exit Criteria (Ready for Phase 3 Production)

- LLM narrative is used in at least 5 real draft orders with officer sign-off.
- Zero validator failures in production logs.
- Full audit trail reviewed and accepted by internal audit / legal.
- Cost per order is acceptable and predictable.
- Fallback to pure deterministic mode remains one environment variable flip away.

---

**This plan exists so that when Phase 2 work begins, the team does not have to rediscover the safety boundaries.** The current MVP is deliberately LLM-free precisely so that the deterministic foundation can be trusted before any generative layer is added.
