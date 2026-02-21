# AI-Based Decision Support System for ARR Truing-Up

A compliance-grade analytics engine for the Power Utility Sector, transitioning from a deterministic rule-based MVP to an AI-augmented predictive system.

## Concept to Execution

The Decision Support System (DSS) is built to evaluate Annual Revenue Requirements (ARR) through a regulatory lens. The core execution priority is **Regulatory Correctness and Traceability**. 
Every output generates a JSON metadata object asserting the specific regulatory clause applied.

### Phase Delineation

#### Phase 1: Deterministic Compliance Engine (Current)
- **Objective:** Build a high-fidelity, audit-ready computation engine based on the 30.06.2025 Truing-Up Order reasoning.
- **Core Components:**
  - **Variance Analysis:** Evaluates Controllable vs. Uncontrollable cost variances.
  - **Sharing Mechanism:** Implements the 1/3 (Consumer) and 2/3 (Utility) sharing logic for controllable savings.
  - **Normative Caps:** Connects configuration rules (like CPI:WPI weights) to execution.
  - **Auditability:** Robust `Output` JSON traces for every computed regulation.

#### Phase 2: AI-Augmented Intelligence (Future)
- **Objective:** Layer predictive and automated AI onto the deterministic rules.
- **Integration Modules:**
  1. *NLP Petition Parsing* (LLM extraction of unstructured PDFs).
  2. *Anomaly Detection* (Isolation Forests for financial spikes).
  3. *Predictive ARR* (LSTM/ARIMA modeling for sales).
  4. *Procurement Optimization* (Linear Programming for PPA balancing).

## System Architecture Blueprint

The Phase 1 architecture leverages a **Modular Hook Pattern**. The Rule Engine is deliberately decoupled from data sourcing, allowing Phase 2 AI models to seamlessly inject validated inputs and anomalies.

```mermaid
flowchart TD
    %% Styling
    classDef core fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef data fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    classDef ai fill:#fff8e1,stroke:#f57f17,stroke-width:2px,stroke-dasharray: 5 5;
    classDef audit fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px;

    %% Data Layer
    subgraph DataSourcing [Data Layer]
        DB[(PostgreSQL<br>15-min Block Data)]:::data
        PDF[Unstructured PDFs<br>& Audited Accounts]:::data
    end

    %% Phase 2 AI Hooks (Inputs)
    subgraph AI_Input [Phase 2: AI Input Hooks]
        NLP[NLP Petition Parsing<br><font size=1>Extracts data from PDFs</font>]:::ai
        Predictive[Predictive ARR<br><font size=1>LSTM/ARIMA Forecasting</font>]:::ai
    end

    %% Phase 1 Rule Engine
    subgraph Phase1 [Phase 1: Deterministic Engine]
        Config{{regulatory_config.yaml<br>Normative Caps & Rules}}:::core
        Engine[Gain / Loss Sharing Module<br><font size=1>Variance Analysis & Normative Caps</font>]:::core
    end

    %% Phase 2 AI Hooks (Validation)
    subgraph AI_Validation [Phase 2: AI Validation Hooks]
        Anomaly[Anomaly Detection<br><font size=1>Isolation Forests</font>]:::ai
        Optim[Procurement Optimization<br><font size=1>Linear Programming</font>]:::ai
    end

    %% Output Layer
    subgraph Outputs [Output Layer]
        Trace[Audit Trail JSON<br><font size=1>Regulation Trace & Logic</font>]:::audit
    end

    %% Relationships
    DB --> Engine
    PDF --> NLP
    NLP -.->|Structured Extracted Data<br>(Hook)| Engine
    Predictive -.->|Forecasted Sales/Demand<br>(Hook)| Engine

    Config --> Engine
    
    Engine --> Anomaly
    Anomaly -.->|Red-Flag Alerts<br>(Hook)| Trace
    
    Engine --> Optim
    Optim -.->|Optimized Mix<br>(Hook)| Trace

    Engine --> Trace
```

## Running the Demonstration

To execute the Phase 1 Rule Engine with sample data:

1. **Install Dependencies:**
   Ensure Node.js is installed. From the project root, run:
   ```bash
   npm install
   ```

2. **Run the Demo:**
   Execute the demonstration script which loads the config, instantiates the engine, and processes sample scenarios:
   ```bash
   npx tsx src/demo.ts
   ```

This will run three discrete scenarios simulating Gains, Losses, and AI anomaly flagging, outputting the respective Audit JSON traces to your console.

## Phase 2: AI-Augmented Workflow

The DSS is designed to foster **AI-Human Collaboration**. Every AI suggestion can be overridden by the regulatory officer, with AI acting strictly as a co-pilot.

### Module A: RAG System Prompt (Phase 3 Hardened)
When processing unstructured PDF Petitions (e.g., the 30.06.2025 KSERC Order), the LLM utilizes this strict Few-Shot prompt to prevent hallucination:

```text
You are a Senior Regulatory Compliance Auditor extracting financial data for the ARR Truing-Up Phase. 
Analyze the provided KSERC PDF petition containing the "Approved vs. Actual" variance tables.

CRITICAL RULE: Zero tolerance for hallucination. If a value is missing or ambiguous, you MUST return null and set the `review_required` flag to true.

Extraction Guidelines:
1. Map figures strictly to this JSON format:
   { "head": "<O&M|Power_Purchase|Interest>", "category": "<Controllable|Uncontrollable>", "approved": <number|null>, "actual": <number|null>, "review_required": <boolean> }

FEW-SHOT EXAMPLES:
---
Input: "The Commission approved Rs. 500 Cr for Power Purchase but the licensee incurred Rs. 510 Cr."
Output: { "head": "Power_Purchase", "category": "Uncontrollable", "approved": 5000000000, "actual": 5100000000, "review_required": false }
---
Input: "O&M limits were set at 150 Cr. Actual records missing from Pg 4."
Output: { "head": "O&M", "category": "Controllable", "approved": 1500000000, "actual": null, "review_required": true }
---
```

### Module B: The "Red-Flag" Engine
A Scikit-Learn `IsolationForest` continuously monitors datasets (like 15-minute power purchase blocks). Sudden spikes exceeding historical standard deviations trigger an anomaly flag. 
- *Crucially, every flag generates a **Reasoning Block*** explaining why the data point was marked as an outlier (e.g., "The analyzed price instance (12.5) is an outlier outside the 95th percentile boundary").

### Demo User Journey
1. **Upload:** User drops the Unstructured PDF Petition into the Dashboard.
2. **Extraction & RAG:** The LLM parses the PDF, rendering a "Regulatory Fact-Sheet". The UI displays **Confidence Scores** next to every extracted value.
3. **Prudence Check:** `AnomalyDetection.py` scans the structured data.
4. **Validation view:** User reviews the **Comparative Heatmap** (Approved vs. Actual vs. AI-Predicted trends). Any "Red-Flags" are highlighted with Reasoning Blocks. Evaluator confirms or overrides the AI findings.
5. **Phase 1 Execution:** The structured data passes through the Deterministic Engine, slicing variances via the 2/3:1/3 logic.
6. **Draft Generation:** The LLM-powered **Draft Generator** produces the final Truing-Up Statement draft, generating KSERC-standard Annexure Tables dynamically via Excel exports perfectly synced to computations.

## Live KSERC Deployment Validation Checklist

Before deployment to the KSERC production server, the following data-integrity architectures must be verified:

1. **Row-Level Security (RLS) & Multi-Tenant DBs:** The database schema must rigidly separate Discom data via PostgreSQL RLS policies to prevent petition leakage.
2. **Role-Based Access Control (RBAC):** Distinct permissions between `Data_Entry_Agent` (AI ingestion triggers) and `Regulatory_Officer` (Draft overwrite and final submission rights).
3. **Rule Versioning Engine:** The `regulatory_config.yaml` must support chronological versioning. If "Order 30.06.2025" is applied to older 2023 petitions, the system explicitly flags "Regulatory Conflict Mismatch".
4. **Adversarial & Null-State Handlers:** Ensure deterministic engines gracefully reject malformed AI typings (e.g., preventing floating point integer overflow exploits in the 2/3 Sharing split).
5. **Immutable Audit Trails:** Final Draft generations and human-overrides are burned into a WORM (Write Once, Read Many) log asserting the exact Phase 1 logic traces.

## Directory Structure

- `/config/`: Externalized yaml configuration files setting framework-agnostic rules.
- `/src/`: Deterministic TypeScript modules, maintaining strict typings.
- `/output/`: Audit Object outputs, strictly formatting JSON tracing.
