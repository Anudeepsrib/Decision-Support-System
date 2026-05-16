# KSERC Decision Support System — Roadmap

---

## Phase 1 — Current MVP (Completed on `mvp-demo` branch)

**Goal:** Prove the end-to-end deterministic pipeline from two PDFs to a KSERC-style draft order.

**Delivered:**
- Two-PDF upload (ARR Order + Truing-Up Petition)
- pdfplumber extraction + target table detection (`table_targets.py`)
- Full canonical registry with strong SBU-D coverage
- Deterministic 15% variance comparison engine
- Officer review workflow with mandatory justification
- Report context builder with Full / Fallback / Missing chapter modes
- ReportLab (default) + optional Playwright PDF generation
- Transparent Extraction Coverage appendix in every generated PDF
- Local SQLite + FastAPI + Vite React frontend
- Complete smoke test and unit test suite
- Zero LLM in the execution path

**Status:** Demo-ready for stakeholders who understand the coverage limitations.

---

## Phase 1.5 — Extraction Completeness (Next Immediate Work)

**Goal:** Make SBU-G, SBU-T, Energy/T&D, and Common Expenses coverage reliable on real KSEB petitions, not just the sample PDFs.

**Planned Deliverables:**
- Expand `TARGET_TABLE_CATALOG` with additional caption patterns observed in actual petitions (10–20 new targets)
- Improve alias breadth in `canonical_registry.py` for generation and transmission line items (O&M sub-heads, auxiliary consumption, fuel cost, intra-state transmission charges, etc.)
- Better multi-page table continuation handling
- Enhanced Energy Sales & T&D Loss extraction (often critical for truing-up orders)
- Common Expenses / corporate allocation mapping
- Updated test PDFs or anonymized real-petition fixtures
- Improved coverage dashboard in the UI (percentage of expected line items mapped per SBU)
- "Source Traceability Appendix" that lists every canonical item with its exact (page, table) origin from both documents

**Success Metric:** On a representative set of 5–10 real (anonymized) petitions, ≥ 85% of the line items that appear in the historical manual orders are successfully extracted and mapped without manual intervention.

**Timeline:** 4–8 weeks of focused engineering.

---

## Phase 2 — Safe LLM Narrative Layer

**Goal:** Allow the system to draft the explanatory paragraphs and "Commission's Analysis" sections while preserving 100% determinism on all numbers, citations, and regulatory conclusions.

**Key Work (see [17_PHASE_2_LLM_PLAN.md](17_PHASE_2_LLM_PLAN.md) for full spec):**
- Prompt registry + versioned system prompts
- Structured JSON output mode from the LLM
- Numeric integrity validator (round-trip number extraction and comparison)
- Citation whitelist validator (`regulatory_citations.py`)
- SBU and mapping consistency validator
- Missing-data caveat auto-injection
- Officer review UI that shows "LLM-proposed" vs "Deterministic base" side-by-side with mandatory acceptance step
- Full audit logging of every LLM call, raw response, validator result, and officer edit
- Kill switch (`LLM_ENABLED=false` by default)
- Support for both commercial APIs and local models (Ollama / vLLM) for air-gapped deployments

**Non-Goals (Never):**
- LLM changes any value in the tables
- LLM invents citations
- LLM bypasses officer review
- LLM used for any decision classification

**Success Metric:** At least 5 real draft orders produced with LLM assistance where every validator passed and the officer accepted or edited the narrative, with zero regulatory or factual errors attributable to the model.

---

## Phase 3 — Production Hardening & Deployment

**Goal:** Turn the validated local tool into a secure, multi-user, auditable system suitable for actual KSERC regulatory workflow.

**Major Work Items:**
- Full authentication (JWT + possibly OIDC integration with existing KSERC identity provider)
- Role-based access control (Regulatory Officer, Senior Officer, Admin, Viewer)
- Cryptographically tamper-evident audit log (hash-chained entries, periodic root hash publication)
- Production-grade document storage (S3-compatible or on-prem DMS with retention policies)
- Hardened file upload (virus scanning, stricter size/type, content disarm & reconstruction)
- Performance optimization (caching, parallel extraction where safe, background worker queue)
- Comprehensive regression suite against a growing corpus of real (anonymized) petitions
- Visual regression testing for generated PDFs
- CI/CD pipeline (GitHub Actions or equivalent) with mandatory smoke test + security scans
- Deployment runbooks (Docker/K8s, secrets management, monitoring, alerting)
- User training materials and administrator guide
- Legal / regulatory sign-off on the use of LLM assistance (if Phase 2 is active)

**Non-Functional Requirements:**
- Support for air-gapped / offline installations (local LLM + no external dependencies)
- Sub-30-second extraction for typical 150–250 page petitions on server-class hardware
- 99.5%+ uptime target once deployed

---

## Phase 4 (Vision) — Advanced Capabilities (Out of Scope for Current Planning)

- Automated "pre-draft" recommendations for revenue gap allocation
- Integration with tariff model / consumer impact simulator
- Multi-year truing-up batch processing
- Stakeholder comment ingestion and automatic summarization
- Machine learning for alias suggestion (still gated by human confirmation into the canonical registry)
- Public portal for non-confidential order search and download

---

## Dependency Between Phases

- Phase 1.5 should be largely complete before serious Phase 2 work begins (otherwise the LLM will be drafting around too many "Missing" chapters).
- Phase 2 must have its full validator stack and officer-in-the-loop UI before any production use.
- Phase 3 can begin in parallel with late Phase 2, but production deployment should wait for both to stabilize.

---

## How to Propose Changes to This Roadmap

1. Open an issue with the label `roadmap`.
2. Reference the specific phase and success metric.
3. Include impact on determinism, auditability, and officer workload.
4. All roadmap changes require review by the technical architect + regulatory liaison.

---

**This document, together with the limitations document, forms the public contract of what the system is and is not.** Update it transparently as each phase is completed.
