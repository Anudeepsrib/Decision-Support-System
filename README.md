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


## Directory Structure

- `/config/`: Externalized yaml configuration files setting framework-agnostic rules.
- `/src/`: Deterministic TypeScript modules, maintaining strict typings.
- `/output/`: Audit Object outputs, strictly formatting JSON tracing.
