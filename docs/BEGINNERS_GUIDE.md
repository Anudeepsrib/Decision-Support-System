# Beginner's Guide: KSERC Truing-Up Decision Support System

*A Plain-English Introduction for Regulatory Officers and Auditors*

---

## What is this system?

Imagine being a **Regulatory Officer** at KSERC who needs to review dozens of Truing-Up Petitions every year. Each petition contains hundreds of financial line items claiming deviations from the Approved Annual Revenue Requirement (ARR). Manually comparing Petition claims vs Approved vs Actual figures across thousands of rows in spreadsheets is exhausting, expensive, and error-prone.

This system acts as an **AI-powered regulatory assistant** that:
1. **Reads** Petition PDFs and extracts structured financial data
2. **Compares** Petition vs Approved ARR vs Actual audited figures
3. **Classifies** each deviation as AI Auto-Approved **[A]**, Pending Manual Review **[P]**, or requiring Manual Override **[M]**
4. **Generates** KSERC-compliant Truing-Up Orders with embedded justifications

---

## The "Zero Hallucination" Rule

Many AI tools simply ask chatbots to "analyze these documents." The problem? Large Language Models (LLMs) hallucinate. They might accidentally read ₹3.15 Crore as ₹3.50 Crore because they guess probabilities, not doing precise mathematical calculations.

**This system is built from the ground up to avoid LLM hallucination entirely.**

### How it works without guessing:

1. **PDF Text Extraction**: It strips raw computer text character-for-character directly from PDFs using deterministic algorithms
2. **Table Parsing**: Uses mathematical heuristics to split financial tables into structured data
3. **Variance Calculation**: Computes deviations using precise arithmetic (no estimates)
4. **Decision Classification**: Applies strict rule-based logic:
   - Variance > 25%? → **[P] Pending Manual**
   - External factor detected? → **[P] Pending Manual**
   - Confidence < 85%? → **[P] Pending Manual**
   - Otherwise → **[A] AI Auto**

**The result:** You can run the same documents through the system 1,000 times and get the exact same classification every time, guaranteed.

---

## The Human-in-the-Loop Workflow

The system doesn't replace officers—it **empowers** them:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Upload    │────▶│  AI Analysis │────▶│   Review    │
│    PDF      │     │ + Classify   │     │  Decisions  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
                    ▼                          ▼                          ▼
              ┌─────────┐              ┌─────────────┐              ┌─────────────┐
              │ [A] Auto│              │  [P] Pending │              │ [M] Override │
              │Approved │              │   Review     │              │  Reviewed   │
              └────┬────┘              └──────┬──────┘              └──────┬──────┘
                   │                         │                          │
                   │                         ▼                          ▼
                   │                ┌─────────────┐              ┌─────────────┐
                   │                │ Officer     │              │ Officer     │
                   │                │ Reviews +   │              │ Reviews +   │
                   │                │ Justifies   │              │ Justifies   │
                   │                └──────┬──────┘              └──────┬──────┘
                   │                       │                          │
                   └───────────────────────┴──────────────────────────┘
                                           │
                                           ▼
                                   ┌─────────────┐
                                   │ Final Order │
                                   │ Generated   │
                                   │ (8 Sections)│
                                   └─────────────┘
```

---

## The Interface

When you log into the system, you'll see three main work areas:

### 1. **Dashboard**
- Overall statistics: Total petitions, pending decisions, completion rates
- SBU-wise breakdown: SBU-G (Generation), SBU-T (Transmission), SBU-D (Distribution)
- Recent activity and notifications

### 2. **Manual Decisions Workbench** (`/decisions`)
This is where officers spend most of their time:

**Left Panel - Decision Queue:**
- Pending decisions grouped by SBU
- Each card shows:
  - Cost Head (O&M, Power Purchase, Interest, etc.)
  - Variance percentage
  - AI recommendation (Approve/Partial/Disallow)
  - External factor warnings (⚠️ Hydrology, ⚠️ Power Purchase Volatility)
  - Decision mode badge ([A], [P], or [M])

**Right Panel - Review Form:**
- AI Analysis summary (read-only)
- Your Decision dropdown (Approve/Partial/Disallow)
- Approved Value input
- **Justification Text** (mandatory for overrides)
- External Factor category selection
- Regulatory references (Electricity Act section, KSERC Regulation)

**Progress Tracking:**
- Visual progress bar showing % of decisions reviewed
- "3 of 12 reviewed" counter
- Batch navigation (Next Pending button)

### 3. **Order Preview** (`/orders`)
- HTML preview of the generated Truing-Up Order
- 8 sections fully formatted
- Decision markers [A], [M], [P] visible
- Justifications embedded verbatim
- Draft watermark (if pending decisions remain)
- Download as PDF option

---

## Key Concepts to Understand

### SBU (Strategic Business Unit)
The Kerala power sector is divided into three SBUs:
- **SBU-G**: Generation (power plants, hydro, solar)
- **SBU-T**: Transmission (high-voltage lines, substations)
- **SBU-D**: Distribution (last-mile delivery to consumers)

Each SBU has separate ARR calculations and Truing-Up processes.

### Cost Heads
Major categories of expenditure:
- **O&M (Operations & Maintenance)**: Staff salaries, repairs, admin — **Controllable**
- **Power Purchase**: Buying electricity from other producers — **Uncontrollable**
- **Interest**: Loan interest payments — **Uncontrollable**
- **Depreciation**: Asset value reduction — **Controllable**
- **ROE (Return on Equity)**: Profit margin for shareholders — **Controllable**

### Controllable vs. Uncontrollable
- **Controllable**: The utility is responsible for managing these costs efficiently. If they overspend, the excess is **disallowed** (borne by utility).
- **Uncontrollable**: Market-driven or regulatory-mandated costs. Variances are **passed through** to consumers via tariff adjustments.

### Decision Modes Explained

| Mode | Marker | What it means | Officer Action |
|------|--------|---------------|----------------|
| **AI Auto** | [A] | AI is confident (≥85%), variance is low (<25%), no external factors | No action needed; auto-approved |
| **Pending Manual** | [P] | AI detected high variance, external factor, or low confidence | Officer must review and decide |
| **Manual Override** | [M] | Officer explicitly overrode AI recommendation | Justification mandatory and stored |

### External Factors
Conditions outside the utility's control that justify higher costs:
- **Hydrology**: Poor monsoon reducing hydro generation
- **Power Purchase Volatility**: Sudden fuel price spikes
- **Government Mandate**: New policy requiring additional infrastructure
- **Court Order**: Legal requirement affecting operations
- **CapEx Overrun**: Capital project costs exceeding 30% of approved budget
- **Force Majeure**: Natural disasters, pandemics, wars

---

## Example Workflow

### Scenario: O&M Cost Review

**The Situation:**
- Approved O&M for FY 2024-25: ₹145 Crore
- Petition claims: ₹150 Crore (+3.4% variance)
- Actual audited: ₹148 Crore

**AI Analysis:**
- Variance: +2.1% (below 25% threshold)
- Confidence: 92% (high)
- No external factors detected
- **Classification: [A] AI Auto → APPROVE**

**Officer Action:**
- No review needed; automatically approved
- Appears in Final Order with [A] marker

---

### Scenario: Power Purchase with External Factor

**The Situation:**
- Approved Power Purchase: ₹420 Crore
- Petition claims: ₹450 Crore (+7.1% variance)
- Actual audited: ₹480 Crore (+14.3% variance)
- Petition cites: "Monsoon failure led to reduced hydro generation, requiring expensive short-term market purchases"

**AI Analysis:**
- Variance: 14.3% (below threshold, but high)
- Confidence: 78% (moderate)
- **External Factor Detected: Hydrology**
- **Classification: [P] Pending Manual**

**Officer Action:**
1. Reviews AI analysis in workbench
2. Examines external factor evidence (monsoon data, hydro generation logs)
3. Decides: **PARTIAL approval** of ₹450 Crore (not full ₹480 Crore)
4. Enters justification:
   > "The Commission acknowledges the hydrological deficit cited by the petitioner. However, the utility could have mitigated costs through better bilateral contracting. Partial approval granted under Regulation 9.4."
5. Marks external factor: **Hydrology**
6. References: **Regulation 9.4** (Uncontrollable Pass-Through)

**Result:**
- Decision marked **[M] Manual Override** in Final Order
- Justification appears verbatim in Section 6
- Audit trail records: Officer ID, timestamp, IP address

---

## Tips for Officers

### Writing Good Justifications

**Minimum Requirements:**
- At least 20 characters for all decisions
- At least 50 characters if overriding AI recommendation

**Best Practices:**
1. **State the facts**: "The petition claims ₹X, approved was ₹Y, actual is ₹Z"
2. **Cite the regulation**: "Per Regulation 9.X..."
3. **Explain the reasoning**: "The Commission finds that..."
4. **Reference external factors** (if applicable): "Due to [factor]..."

**Example Good Justification:**
> "The petition claims ₹480 Crore for Power Purchase against approved ₹420 Crore. The Commission notes the external factor of deficient monsoon (65% of normal rainfall) reducing hydro availability. However, the utility failed to demonstrate adequate bilateral contracting to mitigate costs. Per Regulation 9.4, partial pass-through of ₹30 Crore is approved, disallowing ₹30 Crore excess."

### When to Override AI

**Valid reasons to override:**
- New information not in the petition (e.g., post-filing court order)
- AI missed critical context (e.g., known infrastructure damage)
- Policy changes affecting the decision

**Always provide detailed justification for overrides.**

---

## Glossary

| Term | Definition |
|------|------------|
| **ARR** | Annual Revenue Requirement — the approved budget for a utility |
| **Truing-Up** | Year-end reconciliation of approved vs actual costs |
| **MYT** | Multi-Year Tariff — the 5-year regulatory framework |
| **SBU** | Strategic Business Unit (G=Generation, T=Transmission, D=Distribution) |
| **O&M** | Operations and Maintenance costs |
| **PPA** | Power Purchase Agreement |
| **CapEx** | Capital Expenditure (infrastructure investments) |
| **RPO** | Renewable Purchase Obligation |
| **Gain/Loss Sharing** | Mechanism to share savings/overspend between utility and consumers |
| **Pass-Through** | Costs allowed to be recovered via tariff adjustments |

---

## Getting Help

**Technical Support:**
- Email: support@kserc-dss.gov.in
- Phone: +91-XXX-XXXXXXXX (9 AM - 6 PM IST)

**User Manual:**
- Full documentation: `/docs` folder in repository
- API reference: http://localhost:8000/docs (when running locally)

**Training:**
- Video tutorials: [Internal Portal Link]
- Monthly workshops: Contact KSERC IT Cell

---

## Wrap Up

This Decision Support System transforms weeks of manual spreadsheet analysis into a **3-hour AI-assisted workflow** while ensuring:

✅ **Zero hallucination** — All calculations are deterministic  
✅ **Full compliance** — KSERC regulations embedded in logic  
✅ **Complete audit trail** — Every decision tracked and traceable  
✅ **Officer empowerment** — AI handles routine cases, officers focus on complex decisions  

**Your role:** Review AI recommendations, apply regulatory judgment, and ensure fair outcomes for utilities and consumers.

---

<div align="center">

**KSERC Truing-Up DSS — Empowering Regulatory Excellence**

</div>
