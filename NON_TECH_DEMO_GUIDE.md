# Executive Demo Guide: ARR Truing-Up Decision Support System

Welcome to the **ARR Truing-Up Decision Support System** (DSS). This application is designed to modernize and automate the review of Annual Revenue Requirement (ARR) petitions using AI, ensuring strict compliance with the KSERC MYT Framework 2022-27.

This guide provides a complete, step-by-step walkthrough for **non-technical stakeholders** to set up the environment from scratch and experience every core capability of the system.

---

## 📌 Prerequisites

Before you begin, please ensure the following software is installed on your computer. If any of these are missing, ask your IT team to install them — it takes under 5 minutes.

| Software | Minimum Version | How to Check | Download Link |
|----------|----------------|--------------|---------------|
| **Python** | 3.10 or higher | `python --version` | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18 or higher | `node --version` | [nodejs.org](https://nodejs.org/) |
| **Git** | Any recent version | `git --version` | [git-scm.com](https://git-scm.com/) |

> **Tip:** On Windows, open **Command Prompt** or **PowerShell** to run these check commands. On Mac, open the **Terminal** app.

---

## 🛠️ 1. Environment Setup (First-Time Only)

This section only needs to be done **once** when you first download the project. It creates an isolated Python workspace and installs all required libraries.

### Step 1.1 — Clone the Repository

If you haven't already downloaded the project, open a terminal and run:

```bash
git clone https://github.com/Anudeepsrib/Decision-Support-System.git
cd Decision-Support-System
```

### Step 1.2 — Create a Python Virtual Environment

A virtual environment keeps the project's Python packages separate from your system Python. This prevents conflicts with other software.

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
.\venv\Scripts\activate
```

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

> **How do I know it worked?** You will see `(venv)` appear at the beginning of your terminal prompt. This confirms you are inside the virtual environment.

### Step 1.3 — Install Python Dependencies

With the virtual environment active (you should see `(venv)` in your prompt), install all backend packages:

```bash
pip install -r requirements.txt
```

This installs ~68 packages including FastAPI (web server), PyPDF2/pdfplumber (PDF reading), scikit-learn/pandas (data processing), and all security libraries. It may take 2-5 minutes depending on your internet speed.

### Step 1.4 — Install Frontend Dependencies

Now install the React frontend packages:

```bash
cd frontend
npm install
cd ..
```

This downloads the React UI framework, Recharts (interactive charts), Axios (API calls), and other interface libraries into the `frontend/node_modules/` folder.

### Step 1.5 — Configure Environment Variables

The application needs a small configuration file to know how to connect to services.

1. Copy the example environment file:
   ```bash
   copy .env.example backend\.env        # Windows
   cp .env.example backend/.env          # Mac/Linux
   ```
2. Open `backend/.env` in any text editor and fill in your actual API keys:
   - **`OPENAI_API_KEY`** — Your private OpenAI API key (for AI-powered extraction and tariff generation).
   - **`SECRET_KEY`** — Any random 32+ character string (for securing login tokens).
   - Leave all other values at their defaults for local demo use.

> ⚠️ **Security Warning:** Never share your `.env` file or commit it to Git. It contains private API keys.

### Step 1.6 — Generate Demo PDF Files (Optional)

The project includes 3 pre-built sample PDFs in `data/demo_files/`. If they are missing or you want to regenerate them, run:

```bash
pip install reportlab
python generate_demo_data.py
```

This creates three realistic regulatory PDFs:
| File | Description | SBU |
|------|-------------|-----|
| `1_True_Up_Petition_SBU_D_FY25.pdf` | Truing-Up Petition (Distribution) | SBU-D |
| `2_Audited_Financials_SBU_G_FY25.pdf` | Statutory Audit Report (Generation) | SBU-G |
| `3_Transmission_Loss_Report_FY25.pdf` | Line Loss Compliance Report (Transmission) | SBU-T |

---

## 🚀 2. Starting the Application

Every time you want to run the demo, you need to start **two servers** — the backend (engine) and the frontend (visual interface). Open **two separate terminal windows** in the project's root folder.

### Terminal 1 — Backend Server (The Engine)

Activate the virtual environment first, then start the server:

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
$env:DEBUG="true"; python -m uvicorn backend.main:app --reload
```

**Windows (Command Prompt):**
```cmd
.\venv\Scripts\activate
set DEBUG=true && python -m uvicorn backend.main:app --reload
```

**Mac / Linux:**
```bash
source venv/bin/activate
export DEBUG="true" && uvicorn backend.main:app --reload
```

> **What does `--reload` do?** It automatically restarts the backend when code changes are detected. This is useful for development but not needed for presentations.

✅ **Success indicator:** You will see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

You can verify the backend is healthy by opening [http://localhost:8000/docs](http://localhost:8000/docs) in your browser — this shows the interactive API documentation.

### Terminal 2 — Frontend Interface (The UI)

In a **separate** terminal window:

```bash
cd frontend
npm start
```

✅ **Success indicator:** Your default web browser will automatically open to **`http://localhost:3000`**. You will see the login screen.

> **Note:** If the browser doesn't open automatically, manually navigate to [http://localhost:3000](http://localhost:3000).

---

## 🔐 3. Logging In

The system enforces **Role-Based Access Control (RBAC)**, meaning different users see different features based on their role. For the full demo experience, use the **Regulatory Officer** account:

| Field | Value |
|-------|-------|
| **Email** | `regulatory.officer@kserc.gov.in` |
| **Password** | `DemoPass123!` |

This account has **full access** to all three Strategic Business Units (SBU-G, SBU-T, SBU-D) and all system features.

### Other Available Demo Accounts

| Email | Password | Role | Access Level |
|-------|----------|------|-------------|
| `auditor@utility.com` | `DemoPass123!` | Senior Auditor | SBU-D only |
| `data.entry@utility.com` | `DemoPass123!` | Data Entry Agent | SBU-D only (upload-focused) |
| `analyst@utility.com` | `DemoPass123!` | Readonly Analyst | All SBUs (view-only) |

> **Demo Tip:** To showcase the security model, log in as the Auditor in a separate incognito window and show how they cannot access SBU-G or SBU-T data. This demonstrates data isolation.

---

## 📊 4. The Dashboard (Command Center)

Upon logging in, you will land on the **Dashboard**. This is the executive overview providing a real-time snapshot of regulatory compliance across all SBUs.

### Key Features to Demonstrate:

**a) Welcome Card**
- Confirms your authenticated identity, role, and which SBUs you have access to (e.g., "Access to SBU-G, SBU-T, SBU-D").
- Demonstrates that the system is aware of your permissions.

**b) Efficiency Analysis Module (Line Loss Calculator)**
- This is an interactive widget that evaluates Transmission & Distribution (T&D) line loss against the KSERC normative trajectory.
- **Live Demo Steps:**
  1. In the "Actual Loss %" input box, enter **`11.50`** (the target value).
  2. Click **"Evaluate"**.
  3. ✅ A **green success message** appears — the utility is within compliance.
  4. Now change the value to **`12.20`** and click **"Evaluate"** again.
  5. 🔴 The system instantly switches to a **red alert**, cites the specific regulatory clause, and calculates the estimated **penalty in Crores (₹)** that the utility would face.
- **Why this matters:** This takes an analyst hours to manually calculate — the system does it in milliseconds with full regulatory traceability.

**c) Multi-Year Historical Trends**
- Scroll down to see interactive **Recharts** line/bar graphs tracking:
  - **Approved vs. Actual ARR** costs over multiple financial years.
  - **Net Revenue Gap** trajectory (surplus or deficit over time).
- **Demo Tip:** Hover over the charts to see exact values for each year. This helps stakeholders instantly understand cost trends without reading 100-page reports.

---

## 📄 5. Ingesting Petitions (PDF Uploader)

Now we simulate receiving a massive, unstructured PDF petition from a utility company — the core use case of the system. In this step, we will dive under the hood to see exactly how the backend code processes the documents.

### Steps in the UI:

1. Click **"Upload PDF"** in the top navigation bar.
2. Open your computer's file explorer and navigate to the `data/` folder inside this project.
3. **Drag and drop** the file named **`ARR 2022-27 dated 25.06.2022.pdf`** into the upload zone.
4. Watch the progress indicator as the AI engine processes the 400+ page document.

### What Happens Behind the Scenes (The Backend Flow):

When you drop the PDF into the browser, a complex orchestration of **Python** backend code is triggered. Here is the exact flow:

#### Step A: Receiving the File (`backend/api/extraction.py`)
The frontend sends the file to the FastAPI backend endpoint `POST /extract/upload`. 
The backend handles the upload asynchronously and assigns it a unique Job ID.

#### Step B: Reading the PDF (`backend/api/ocr_service.py` & `PyPDF2`)
The system first attempts to extract the raw text from the PDF using the `PyPDF2` library. This is extremely fast but only works if the PDF has a native text layer (i.e., it wasn't scanned from a physical piece of paper).
If the PDF is a scanned image, the system falls back to **Tesseract OCR** (Optical Character Recognition) via the `pytesseract` library to visually "read" the text from the images.

#### Step C: The Extraction State Machine (`backend/api/extraction_graph.py` & `LangGraph`)
The core intelligence lives in a **LangGraph** state machine. LangGraph is a framework for building cyclical, agentic workflows. 
The system defines a `State` object that holds the raw text pages and a list of `ExtractedField` objects.

```python
# From backend/api/extraction_graph.py
class ExtractionState(TypedDict):
    raw_ocr_pages: List[str]
    extracted_fields: List[Dict[str, Any]]
    requires_human_review: bool
    retry_count: int
```

The state machine runs through the text page-by-page. We use **Regular Expressions (Regex)** (via the standard Python `re` library) to intelligently hunt for specific financial patterns, rather than relying blindly on an LLM.

```python
# From backend/api/extraction_graph.py
# Example of the Regex Engine hunting for O&M Costs
def _extract_fields_from_text(pages: List[str]) -> List[Dict[str, Any]]:
    # ... setup ...
    patterns = {
        "O&M Cost": [
            r"O\s*&\s*M\s*(?:Expenses|Cost)?\s*[\:\-]?\s*(?:Rs\.?|₹)?\s*([\d\,\.]+)\s*(?:Cr\.?|Lakh)?",
            r"Operation and Maintenance.*?(?:Rs\.?|₹)?\s*([\d\,\.]+)"
        ],
        # ... other cost heads ...
    }
```

#### Step D: Confidence Scoring & Flagging
For every number found, the system assigns a **confidence score**. 
- If it confidently extracts a value like ₹2,021.00 Crore for Total ARR, it scores it at `0.95` (95%).
- If the regex engine cannot find a specific cost head in the context it expects, it outputs `N/A` and flags the field as `requires_human_review = True`. 

```python
# From backend/api/extraction_graph.py
if best_val is not None:
    fields.append({
        "field_name": head,
        "extracted_value": best_val,
        "source_page": best_page,
        "confidence_score": 0.95,
        "review_required": False
    })
else:
    # Flag for human review if nothing found
    fields.append({
        "field_name": head,
        "extracted_value": None,
        "source_page": None,
        "confidence_score": 0.40, 
        "review_required": True
    })
```

#### Step E: Auto-Populating Mappings (`backend/api/mapping.py`)
Once the LangGraph pipeline finishes, the `backend/api/extraction.py` endpoint takes the extracted fields and automatically sends them to the **Mapping Workbench**.
The backend intelligently classifies each field (e.g., mapping "Employee Cost" to the "O&M" regulatory cost head and marking it as a "Controllable" expense).

```python
# From backend/api/extraction.py
# Auto-populate the mapping workbench and store data for reports
raw_fields = final_state.get("extracted_fields", [])
if raw_fields:
    mappings = generate_mappings_from_fields(raw_fields)
    store_extraction_for_reports(job_id, raw_fields)
    store_mapping_for_reports([m.model_dump() for m in mappings])
```

By the time the loading spinner on your screen stops, this entire pipeline has processed hundreds of pages, extracted the math, flagged the anomalies, and mapped the data to the regulatory framework!

---

## 🤖 6. Validating AI Intelligence (Mapping Workbench)

This is the **Human-in-the-Loop** stage — the heart of the system's "zero-hallucination" policy. The AI does not silently alter data; it operates as an assistant, requiring explicit human confirmation before any data enters the regulatory calculation engine.

### Steps:

1. Click **"Mapping Workbench"** in the top navigation bar.
2. You will see the **"Pending AI Suggestions"** — data the AI extracted from uploaded petitions.

### Key Features to Highlight:

**a) Confidence Scores**
- Each extracted value shows a percentage confidence score.
- High-confidence items (85%+) are typically correct but still require human sign-off.
- Low-confidence items (<70%) are flagged with a warning — these **must** be manually reviewed.

**b) Source Traceability**
- Every value includes its provenance: exactly which **page**, **table**, and **cell** it was extracted from (e.g., "Page 12, Table 1, Cell C4").
- This allows the auditor to open the original PDF and verify the AI's reading.

**c) Standardization**
- The AI maps raw, messy text values (e.g., "Rs. 180.00 Cr") into the standardized **KSERC Chart of Accounts** database categories (e.g., "O&M (Controllable)", "Power_Purchase (Uncontrollable)").

**d) Confirm or Override**

| Action | When to Use | What Happens |
|--------|-------------|--------------|
| ✅ **Confirm** (Checkmark) | AI suggestion is correct | Value is locked into the regulatory ledger |
| ✏️ **Override** | AI misclassified a value | Human corrects the category; a mandatory comment is required |
| ❌ **Reject** | Extracted value is wrong | Value is discarded; logged for audit trail |

**e) Live Demo — Override Scenario:**
- Find a mapping with lower confidence (e.g., 67%).
- Click **Override** and change the category (e.g., from "O&M" to "Admin").
- Add a comment: *"Legal fees include regulatory compliance work — reclassifying as Admin per Regulation 7.2"*.
- Click **Submit**. Notice that every override is permanently logged with a timestamp, user identity, original value, new value, and mandatory comment.

> **Why this matters:** This proves to regulators that no data enters the system without human authorization. The audit trail is immutable — it can be reviewed years later for compliance verification.

---

## 📈 7. Generating Analytical Reports

The ultimate goal of the system — reducing weeks of manual calculation to a single click.

### Steps:

1. Click **"Reports"** in the top navigation bar.
2. Select **Financial Year: 2024-25**.
3. Optionally select a specific SBU filter, or leave it blank to see all SBUs.
4. Click **"Generate Report"**.

### What the Report Shows:

**a) Instant Variance Calculation**
- The system immediately compares the AI-extracted **"Actual"** figures (confirmed by the human in Step 6) against the MYT **"Approved"** baseline.
- It computes the exact **net variance** in Crores (e.g., "₹-30.00 Cr, -1.2%").

**b) Regulatory Disposition Rules**
- The **Deterministic Rule Engine** automatically applies the correct KSERC mathematical formulas:
  - **Controllable gains** (e.g., O&M savings): Shared 2/3 to Utility, 1/3 to Consumer (per Regulation 9.2).
  - **Uncontrollable losses** (e.g., Power Purchase spikes): 100% pass-through to consumers (per Regulation 9.4).
  - **Controllable losses**: Automatically disallowed — the utility bears the full cost.
- The AI **never guesses** these numbers. They are calculated by hardcoded strict logic.

**c) Anomaly Detection**
- The system flags **severe deviations** that require manual auditing (e.g., a sudden 50% jump in Power Purchase costs from the previous year).
- These are highlighted with warning icons and threshold breach indicators.

**d) AI-Generated Insights & Recommendations**
- Scroll down to the **"AI Insights"** section. The system writes the initial draft of a regulatory narrative:
  > 💡 *"The O&M head for SBU-D shows a controllable GAIN of ₹30 Crores. This represents efficient management of controllable factors. Per Regulation 9.2, savings are shared 2/3 to Utility, 1/3 to Consumer."*
  
  > ⚠️ *"ALERT: Power Purchase for SBU-G shows an uncontrollable LOSS of ₹50 Crores due to market price spikes. Fully passed through per Regulation 9.4."*

**e) Tariff Draft Generation (LLM-Powered)**
- Scroll to the **"Regulatory Executive Draft"** section.
- Click **"Generate Draft"** to invoke the GPT-4o-mini language model.
- The system auto-generates a 3-paragraph regulatory narrative based on the computed variances.
- **Crucially, the human can edit this draft text before saving** — the AI assists, the human decides.

---

## 🔧 8. Troubleshooting Common Issues

### Backend won't start

| Symptom | Solution |
|---------|----------|
| `python: command not found` | Ensure Python 3.10+ is installed and added to your system PATH. Try `python3` instead of `python`. |
| `ModuleNotFoundError` | You forgot to activate the virtual environment. Run `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Mac/Linux) first. |
| `Address already in use (port 8000)` | Another process is using port 8000. On Windows, run `netstat -ano | findstr :8000` to find and stop it. |
| `pip install` fails | Ensure you have internet access. If behind a corporate proxy, configure pip with `pip install --proxy http://proxy:port -r requirements.txt`. |

### Frontend won't start

| Symptom | Solution |
|---------|----------|
| `npm: command not found` | Ensure Node.js 18+ is installed. Download from [nodejs.org](https://nodejs.org/). |
| Build errors after `npm start` | Delete `node_modules` and reinstall: `cd frontend && rmdir /s /q node_modules && npm install` (Windows) or `cd frontend && rm -rf node_modules && npm install` (Mac/Linux). |
| Blank page in browser | Check that the backend is running on port 8000. The frontend proxies API calls to `http://localhost:8000`. |

### Login issues

| Symptom | Solution |
|---------|----------|
| "Invalid credentials" | Double-check: email is `regulatory.officer@kserc.gov.in`, password is `DemoPass123!` (case-sensitive, with exclamation mark). |
| "Network Error" | Ensure the backend server (Terminal 1) is running. Check the terminal for error messages. |
| Page stuck on "Loading..." | Clear your browser's `localStorage`: open DevTools (F12) → Application → Local Storage → Clear All. Then refresh. |

---

## 🗂️ 9. Project Structure Reference

For those who want to understand where things live:

```
Decision-Support-System/
├── backend/                    # Python FastAPI server
│   ├── main.py                 # Application entry point (routes, middleware, CORS)
│   ├── api/                    # All API route handlers
│   │   ├── auth.py             # Login, JWT tokens, RBAC
│   │   ├── extraction.py       # PDF upload & AI data extraction
│   │   ├── mapping.py          # Human-in-the-loop mapping workbench
│   │   ├── reports.py          # Report generation & variance analysis
│   │   ├── tariff_generator.py # LLM-powered tariff draft generation
│   │   ├── efficiency.py       # Line loss & T&D efficiency analysis
│   │   ├── history.py          # Multi-year historical trend data
│   │   ├── kserc_scraper.py    # Live KSERC regulatory portal sync
│   │   └── ocr_service.py      # Tesseract OCR fallback for scanned PDFs
│   ├── engine/                 # Deterministic rule engine (strict math)
│   ├── security/               # JWT, rate limiting, security headers
│   ├── demo/                   # Demo data fixtures & initialization scripts
│   └── tests/                  # Automated test suite
├── frontend/                   # React TypeScript UI
│   └── src/
│       ├── App.tsx             # Main router (Dashboard, Upload, Mapping, Reports)
│       ├── components/         # UI components (auth, dashboard, extraction, mapping, reports)
│       ├── contexts/           # React authentication context
│       └── services/           # API service layer (Axios)
├── data/demo_files/            # Sample PDF petitions for demo
├── docs/                       # Extended documentation
│   ├── BEGINNERS_GUIDE.md      # Regulatory context & core features
│   ├── DEMO_GUIDE.md           # Technical demo scenarios (6 detailed walkthroughs)
│   ├── SECURITY.md             # RBAC, authentication, rate-limiting deep dive
│   └── design_system.md        # UI design tokens & aesthetic standards
├── requirements.txt            # Python package dependencies (68 packages)
├── .env.example                # Template for environment variables
├── docker-compose.yml          # One-command production deployment
└── generate_demo_data.py       # Script to regenerate sample PDFs
```

---

## 🎉 Conclusion

You have just experienced a workflow that traditionally takes **weeks** of manual data entry, PDF scrubbing, and spreadsheet calculation. The **ARR Truing-Up Decision Support System** has reduced it to a matter of clicks, dramatically increasing speed, accuracy, and regulatory confidence.

### What Makes This System Enterprise-Grade:

- ✅ **Zero-Hallucination Policy** — The AI assists, the human decides. No unverified data enters calculations.
- ✅ **Full Audit Trail** — Every action (extraction, confirmation, override, report generation) is permanently logged with timestamps, user identity, and checksums.
- ✅ **Role-Based Security** — JWT authentication with SBU-level data isolation. Different roles see different capabilities.
- ✅ **Deterministic Math** — The rule engine uses hardcoded KSERC MYT formulas. It never guesses financial outcomes.
- ✅ **Production-Ready Architecture** — Asynchronous processing, in-memory caching, route-level code splitting, rate limiting, and Docker containerization.

For deeper technical details, see the [`docs/`](./docs/) directory.
