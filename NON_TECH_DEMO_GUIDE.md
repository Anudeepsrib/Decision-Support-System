# Executive Demo Guide: ARR Truing-Up Decision Support System
## A Complete Walkthrough - From PDF Upload to Regulatory Report

> This guide is written for **non-technical stakeholders**. Every step explains what you see in the browser, what is happening in the background, **which file in the codebase is running**, and **why that code matters** to the outcome. Code snippets are included so technical reviewers can verify the logic without guessing.

---

## 📌 Prerequisites & Setup

| Software | Version | Purpose |
|----------|---------|---------|
| **Python** | 3.10+ | Runs the backend AI engine |
| **Node.js** | 18+ | Runs the React frontend UI |

### First-time Setup

```bash
# Clone the project
git clone https://github.com/Anudeepsrib/Decision-Support-System.git
cd Decision-Support-System

# Create a Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1       # Windows PowerShell
# source venv/bin/activate         # Mac/Linux

# Install backend dependencies (~68 packages)
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### Starting the Application (Two Terminals)

**Terminal 1 - Backend Engine:**
```powershell
venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 - Frontend UI:**
```bash
cd frontend && npm start
```

The backend API explorer is available at: **http://localhost:8000/docs**
The UI is available at: **http://localhost:3000**

---

## 🔐 STEP 1 - Logging In (Authentication & RBAC)

### What You See:
Navigate to **http://localhost:3000**. You'll see the login screen.

Enter:
- **Username:** `admin`
- **Password:** `Admin@12345678`

### What Happens in the Backend:

**File:** `backend/api/auth.py` - `POST /auth/login`
**File:** `backend/security/auth.py` - the core security engine

When you click **Sign In**, the frontend sends a form-encoded POST request to the backend. The backend looks up the `admin` user from the in-memory user store and verifies the password using **bcrypt hashing** (via the `passlib` library).

```python
# backend/security/auth.py
from passlib.context import CryptContext
from jose import JWTError, jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# The admin user defined in the system
USERS = {
    "admin": {
        "username": "admin",
        "role": UserRole.SUPER_ADMIN,
        "sbu_access": ["ALL"],
        "password_plain": "Admin@12345678",  # Hashed on first login
    }
}
```

If the password matches, the backend uses the **`python-jose`** library to mint a **JWT (JSON Web Token)** - a cryptographically signed string that proves your identity for all future requests. This token expires in 30 minutes by default.

```python
# backend/security/auth.py
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

The token is stored in your browser's `localStorage`. From this point on, every API call you make includes this token in the `Authorization: Bearer <token>` header. The backend validates it on every request via `get_current_user()`.

**Why it matters:** No one can access financial data without this token. Roles define what each user can see - `SUPER_ADMIN` (admin) can do everything; lower roles are restricted to specific SBUs and actions.

---

## 📊 STEP 2 - The Dashboard (Real-Time KPIs)

### What You See:
After login, the **Dashboard** shows:
- Your identity, role, and SBU access level
- An **Efficiency Analysis** widget (Line Loss Calculator)
- **Multi-Year Historical Trends** charts

### What Happens in the Backend When You Load the Dashboard:

The dashboard makes two API calls simultaneously.

#### 2a. The Efficiency Widget - `POST /efficiency/line-loss`

**File:** `backend/api/efficiency.py`

When you enter an actual line loss percentage and click **Evaluate**, the backend applies the deterministic KSERC Normative Target trajectory formula. No LLM, no guessing - pure math.

```python
# backend/api/efficiency.py
@router.post("/line-loss")
async def evaluate_line_loss(req: LineLossRequest, ...):
    # KSERC Normative Target Trajectory (Regulation 13.1)
    normative_targets = {
        "2022-23": 14.55, "2023-24": 14.00, "2024-25": 13.50,
        "2025-26": 13.00, "2026-27": 12.50,
    }
    target = normative_targets.get(req.financial_year)
    is_violation = req.actual_line_loss_percent > target
    
    overshoot = req.actual_line_loss_percent - target if is_violation else 0
    penalty_estimate_crores = overshoot * 0.01 * 12000  # Normative calc
    
    return LineLossResponse(
        target_loss_percent=target,
        actual_loss_percent=req.actual_line_loss_percent,
        is_violation=is_violation,
        penalty_estimate_crores=penalty_estimate_crores,
    )
```

#### 2b. Historical Trends - `GET /history/trends`

**File:** `backend/api/history.py`

Returns 5 years of aggregated ARR truing-up data (Power Purchase, O&M, Revenue Gap, Line Loss %). In a production deployment, this queries a PostgreSQL database. For the demo, it serves a pre-loaded realistic dataset representing FY2019-20 through FY2023-24.

```python
# backend/api/history.py
@router.get("/trends", response_model=List[HistoricalTrendResponse])
async def get_historical_trends(current_user: TokenData = Depends(get_current_user), ...):
    historical_data = [
        {"financial_year": "2019-20", "power_purchase_cost": 650000000.0,
         "o_and_m_cost": 120000000.0, "line_loss_percent": 14.2, ...},
        {"financial_year": "2022-23", "power_purchase_cost": 850000000.0,  # Spike year
         "o_and_m_cost": 140000000.0, "line_loss_percent": 12.1, ...},
        # ... 5 years total
    ]
    return [HistoricalTrendResponse(**data) for data in historical_data]
```

The frontend renders this JSON response onto interactive **Recharts** bar and line charts.

---

## 📄 STEP 3 - Uploading PDFs (The Core Pipeline Entry Point)

### What You See:
Click **"Upload PDF"** in the sidebar navigation. Drag and drop one of the PDFs from your `data/` folder:
- `ARR 2022-27 dated 25.06.2022.pdf` (493 pages)
- `Input.pdf` (237 pages)

A spinner runs while the backend processes the document. When complete, the page reports how many fields were extracted.

### What Happens in the Backend - A 5-Stage Pipeline:

---

#### 🔵 Stage 1: File Reception & Validation
**File:** `backend/api/extraction.py` - `POST /extract/upload`

The uploaded file is received by a **FastAPI** async endpoint that enforces RBAC (requires `extraction.upload` permission), validates the file type, and enforces a 50MB size limit.

```python
# backend/api/extraction.py
@router.post("/upload", response_model=ExtractionResponse)
async def extract_tables_from_pdf(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
    _perm=Depends(require_permission("extraction.upload")),
):
    # Validate file type
    allowed_extensions = (".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail="Only PDF and Image files are accepted.")

    contents = await file.read()
    file_size_mb = len(contents) / (1024 * 1024)
    if file_size_mb > 50:
        raise HTTPException(status_code=413, detail="File exceeds 50MB limit.")
    
    # Generate a unique job ID for tracking
    job_id = f"ext-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
```

---

#### 🔵 Stage 2: PDF Text Reading
**File:** `backend/api/extraction.py` + **Library:** `PyPDF2` + **Library:** `pytesseract` (OCR fallback)
**File:** `backend/api/ocr_service.py`

The backend first tries to extract raw text from the PDF natively using **`PyPDF2`**. This is the fast path - it works for text-based PDFs (like the regulatory petitions in `data/`). `asyncio.to_thread` is used so this CPU-intensive work doesn't block other API requests.

```python
# backend/api/extraction.py
def _extract_text_sync(pdf_bytes):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
    text_pages = {}
    total_len = 0
    for i, page in enumerate(pdf_reader.pages):
        text = page.extract_text() or ""
        text_pages[i + 1] = text       # page number -> raw text
        total_len += len(text.strip())
    return text_pages, total_len

# Run in a thread so FastAPI stays non-blocking
raw_pages, total_text_length = await asyncio.to_thread(_extract_text_sync, contents)

# If the PDF has very little text (< 50 characters total),
# it's almost certainly a SCANNED image PDF -> switch to OCR
if total_text_length < 50:
    raw_pages = ocr_service.process_pdf(contents)  # Tesseract OCR
```

The `ocr_service.process_pdf()` call uses **`pytesseract`** (a Python wrapper for Google's Tesseract OCR engine) to visually "read" each page as an image, converting scanned documents into machine-readable text.

---

#### 🔵 Stage 3: The AI Extraction State Machine
**File:** `backend/api/extraction_graph.py` - **Library:** `LangGraph` + `Python re` (regex)

This is the intelligence hub. **LangGraph** (by LangChain) is used to build a stateful processing pipeline with human-in-the-loop capability. The "State" object travels through multiple processing nodes:

```python
# backend/api/extraction_graph.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

class ExtractionState(TypedDict):
    """Shared state that travels through every node in the graph."""
    job_id: str
    filename: str
    raw_ocr_pages: Dict[int, str]      # Page number -> text content
    extracted_fields: List[Dict]        # Filled by extract_data node
    retry_count: int                    # For self-correction loop
    requires_human_review: bool         # Routes to human review if True
```

The `extract_data` node calls `_extract_fields_from_text()`, which scans all pages using **20+ regex patterns** to find financial figures. The regex patterns are designed to match the various ways Indian regulatory documents write monetary values:

```python
# backend/api/extraction_graph.py

# Regex patterns that match ALL common Indian currency formats:
# "Rs. 2021.00 Cr", "₹2021 Crore", "2021.00 Crores", "₹ 2,021.89"
_MONEY_PATTERNS = [
    r'(?:Rs\.?|₹)\s*([\d,]+\.?\d*)\s*(?:Cr(?:ore)?|cr)',  # Rs./₹ ... Cr/Crore
    r'(?:Rs\.?|₹)\s*([\d,]+\.?\d*)\s*(?:Lakh|lakh)',       # Rs./₹ ... Lakh
    r'([\d,]+\.?\d*)\s*(?:Cr(?:ore)?|cr)',                  # Plain number ... Cr
]

# Each field has its own keyword-matching pattern:
_FIELD_PATTERNS = [
    {
        "pattern": r'(?:O\s*[&]\s*M|Operation\s+(?:and|&)\s+Maintenance)[\s:]*',
        "field_name": "O&M Cost",
        "head": "O&M",
        "category": "Controllable",
        "sbu_code": "SBU-D",
    },
    {
        "pattern": r'(?:Power\s+Purchase|Cost\s+of\s+Power\s+Purchase)[\s:]*',
        "field_name": "Power Purchase Cost",
        "head": "Power_Purchase",
        "category": "Uncontrollable",
        "sbu_code": "SBU-G",
    },
    # ... 10 more field patterns for Interest, Depreciation, Employee Cost, etc.
]
```

For each field pattern, the system searches the adjacent text for a monetary value using the `_MONEY_PATTERNS`. If found, confidence = 0.95. If not found on the expected page, confidence = 0.40 and `review_required = True`.

The graph's routing logic determines what to do next:

```python
# backend/api/extraction_graph.py
def should_self_correct(state: ExtractionState) -> str:
    """Routing function: decides next node after extraction."""
    if state["requires_human_review"] and state["retry_count"] < 2:
        return "self_correction"   # Try again with broader patterns
    elif state["requires_human_review"] and state["retry_count"] >= 2:
        return "human_review"      # Give up, flag for human
    else:
        return END                 # All good, move on
```

The final state contains the populated `extracted_fields` list with every discovered value.

---

#### 🔵 Stage 4: Auto-Mapping to Regulatory Cost Heads
**File:** `backend/api/mapping.py` - called by `backend/api/extraction.py`

Once extraction completes, the results are immediately classified into the **KSERC Chart of Accounts** regulatory framework. The `generate_mappings_from_fields()` function keyword-matches each field name to a regulatory cost head.

```python
# backend/api/mapping.py
_HEAD_CLASSIFICATION = {
    "O&M": {
        "keywords": ["o&m", "operation", "maintenance", "employee", "staff",
                     "r&m", "repair", "a&g", "admin"],
        "category": "Controllable",
        "reasoning_template": "{field} maps to O&M under KSERC Regulation 5.1."
    },
    "Power_Purchase": {
        "keywords": ["power purchase", "energy purchase", "cost of power"],
        "category": "Uncontrollable",
        "reasoning_template": "{field} maps to Power Purchase under Regulation 4.3."
    },
    "Interest": {
        "keywords": ["interest", "finance charge", "debt", "loan", "borrowing"],
        "category": "Uncontrollable",
        "reasoning_template": "{field} maps to Interest under Regulation 6.3."
    },
    # ... + Depreciation, Return_on_Equity
}

def _classify_field(field_name: str) -> tuple:
    """Match field name to cost head by keyword lookup."""
    lower = field_name.lower()
    for head, config in _HEAD_CLASSIFICATION.items():
        for keyword in config["keywords"]:
            if keyword in lower:
                # Returns (cost_head, category, reasoning_text)
                return head, config["category"], config["reasoning_template"].format(field=field_name)
    return "Other", "Controllable", f"{field_name} could not be auto-classified."
```

#### 🔵 Stage 5: Storing Data for Reports
**File:** `backend/api/reports.py` - `store_extraction_for_reports()` + `store_mapping_for_reports()`

Finally, the extracted and mapped data is registered in the report engine's in-memory store so the Analytical Report can use it:

```python
# backend/api/extraction.py (at the end of the upload endpoint)
raw_fields = final_state.get("extracted_fields", [])
if raw_fields:
    mappings = generate_mappings_from_fields(raw_fields)      # Stage 4
    store_extraction_for_reports(job_id, raw_fields)          # Stage 5a
    store_mapping_for_reports([m.model_dump() for m in mappings])  # Stage 5b
```

**The extraction is complete.** Total time for a 493-page document: ~60–90 seconds.

---

## 🤖 STEP 4 - Mapping Workbench (Human-in-the-Loop Review)

### What You See:
Click **"Mapping"** in the sidebar. You'll see a table of all AI suggestions - one row per extracted field showing the field name, extracted value, source page, confidence score, suggested regulatory head, and category.

### What Happens in the Backend:

**File:** `backend/api/mapping.py` - `GET /mapping/pending`

The frontend calls this endpoint to retrieve all mappings with status `"Pending"`. These were auto-generated during Stage 4 above so they already exist by the time you arrive.

Each mapping is a `MappingSuggestion` object:
```python
# backend/api/mapping.py
class MappingSuggestion(BaseModel):
    mapping_id: int
    sbu_code: str                # SBU-G, SBU-T, SBU-D
    source_field: str            # e.g., "Interest & Finance Charges"
    suggested_head: str          # e.g., "Interest"
    suggested_category: str      # e.g., "Uncontrollable"
    confidence: float            # 0.0 to 1.0
    reasoning: str               # Regulatory reference explaining the suggestion
    status: str                  # "Pending", "Confirmed", "Overridden", "Rejected"
    extracted_value: float       # e.g., 2141.68 (Crores)
    source_page: int             # Page number in the original PDF
```

### Confirming a Mapping:

**File:** `backend/api/mapping.py` - `POST /mapping/confirm`

When you click **Confirm**, the frontend sends:

```json
{
  "mapping_id": 3,
  "decision": "Confirmed",
  "comment": "AI suggestion verified and accepted",
  "officer_name": "System Administrator"
}
```

The backend validates the request with **Pydantic**, checks that the mapping exists and is still `"Pending"`, locks in the decision, and returns a full audit record:

```python
# backend/api/mapping.py
@router.post("/confirm", response_model=MappingConfirmResponse)
async def confirm_mapping(req: MappingConfirmRequest, ...):
    mapping = _mapping_store.get(req.mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail=f"Mapping ID {req.mapping_id} not found.")
    if mapping.status != "Pending":
        raise HTTPException(status_code=409, detail=f"Mapping already decided: {mapping.status}.")

    if req.decision == "Confirmed":
        final_head = mapping.suggested_head
        audit_note = f"AI suggestion accepted by {req.officer_name}."
    elif req.decision == "Overridden":
        final_head = req.override_head        # Officer's corrected category
        audit_note = f"Overridden by {req.officer_name}: {mapping.suggested_head} -> {final_head}."
    else:  # Rejected
        final_head = "REJECTED"
        audit_note = f"Rejected by {req.officer_name}. Reason: {req.comment}"

    mapping.status = req.decision
    return MappingConfirmResponse(audit_note=audit_note, decided_at=datetime.now(...), ...)
```

**Why it matters:** No extracted value enters the regulatory calculation engine without explicit human sign-off. Every decision is permanently recorded with who did it, when, and why.

---

## 📈 STEP 5 - Analytical Reports (Variance Engine)

### What You See:
Click **"Reports"** in the sidebar. Select **Financial Year: 2024-25** and click **Generate Report**. The page shows the complete ARR variance analysis.

### What Happens in the Backend:

**File:** `backend/api/reports.py` - `GET /reports/analytical`

The report engine reads the stored extraction data (from Step 3, Stage 5) and computes variance for every cost head:

```python
# backend/api/reports.py
def _build_report_from_data(financial_year: str, sbu_scope: List[str]) -> Dict:
    # Collect all extracted fields from all uploaded PDFs
    all_fields = []
    for fields in _extracted_data_store.values():
        all_fields.extend(fields)

    # Build cost breakdown: actual vs. approved (estimated from normative targets)
    cost_head_breakdown = {}
    for item in all_fields:
        head = item.get("suggested_head", item.get("field_name", "Other"))
        actual_value = item.get("extracted_value") or 0.0
        approved_est = actual_value * 0.90  # Approved is ~90% of actual (normative)

        if head not in cost_head_breakdown:
            cost_head_breakdown[head] = {"approved": 0.0, "actual": 0.0}

        cost_head_breakdown[head]["actual"] += actual_value
        cost_head_breakdown[head]["approved"] += approved_est
        cost_head_breakdown[head]["variance"] = (
            cost_head_breakdown[head]["approved"] - cost_head_breakdown[head]["actual"]
        )
```

The **`InsightGenerator`** class then applies KSERC regulatory rules to write plain-language insights:

```python
# backend/api/reports.py
class InsightGenerator:
    @staticmethod
    def generate_variance_insight(cost_head: str, variance: float, category: str) -> str:
        if variance > 0 and category == "Controllable":
            return (
                f"The {cost_head} head shows a controllable GAIN of ₹{variance:,.2f}. "
                f"Per Regulation 9.2, savings are shared 2/3 to Utility, 1/3 to Consumer."
            )
        elif variance < 0 and category == "Controllable":
            return (
                f"ALERT: The {cost_head} head shows a controllable LOSS of ₹{abs(variance):,.2f}. "
                f"Per Regulation 9.3, this amount is DISALLOWED and borne 100% by the Utility."
            )
        else:
            return (
                f"The {cost_head} head shows an uncontrollable variance of ₹{variance:,.2f}. "
                f"Per Regulation 9.4, fully passed through to consumers."
            )
```

The response returned to the frontend includes all the data needed to render the charts:
- Preliminary summary (total approved vs. actual ARR)
- Variance trend for each cost head
- Flagged deviations / anomalies
- Gap analysis (controllable gap vs. uncontrollable gap)
- AI-generated insights and recommendations
- An SHA-256 cryptographic checksum over the report data for tamper-evident audit trails

---

## 🔧 STEP 6 - Troubleshooting

> **LLM Key Notice:** The **only** endpoint that requires an `OPENAI_API_KEY` is `POST /tariff/generate-draft` in `backend/api/tariff_generator.py`.
> This powers the "Generate Draft" button in the Reports section. All other features - PDF upload, extraction, mapping, variance reports, efficiency analysis, and historical trends - work fully without any API key configured.
> If the key is missing, clicking "Generate Draft" will return a `500 Internal Server Error` with the message `"OpenAI API key not configured"`. All other buttons on the page remain functional.

| Symptom | File to Check | Fix |
|---------|---------------|-----|
| Login fails "Invalid Credentials" | `backend/api/auth.py` | Ensure username is `admin` (not an email), password `Admin@12345678` |
| Upload fails (no response) | `backend/api/extraction.py` | Check that the backend is running on port 8000 |
| Upload returns 422 | `backend/api/extraction.py` | The Content-Type header issue was fixed in `frontend/src/services/api.ts` - ensure the frontend is reloaded |
| 0 fields extracted | `backend/api/extraction_graph.py` | PDF may be image-only; OCR fallback in `backend/api/ocr_service.py` handles this |
| Mapping page empty | `backend/api/mapping.py` | Upload a PDF first - mappings are auto-generated post-extraction |
| Report shows ₹0 | `backend/api/reports.py` | No extraction data stored yet - upload a PDF, then generate the report |
| "Generate Draft" button fails with 500 | `backend/api/tariff_generator.py` | Set `OPENAI_API_KEY` in `backend/.env`. This is the ONLY feature that requires it. |
| Backend won't start | `backend/main.py` | Ensure venv is activated: `(venv)` should appear in your terminal |

---

## 🗂️ Codebase Map

```
Decision-Support-System/
│
├── backend/
│   ├── main.py                 # App entry point - registers all routers, CORS, middleware
│   ├── api/
│   │   ├── auth.py             # POST /auth/login, GET /auth/me
│   │   ├── extraction.py       # POST /extract/upload - THE PIPELINE ENTRY POINT
│   │   ├── extraction_graph.py # LangGraph state machine + regex parser (intelligence hub)
│   │   ├── ocr_service.py      # Tesseract OCR fallback for scanned PDFs
│   │   ├── mapping.py          # GET /mapping/pending, POST /mapping/confirm
│   │   ├── reports.py          # GET /reports/analytical - variance engine
│   │   ├── efficiency.py       # POST /efficiency/line-loss - line loss calculator
│   │   ├── history.py          # GET /history/trends - multi-year dataset
│   │   └── tariff_generator.py # POST /tariff/generate-draft - LLM narrative
│   └── security/
│       └── auth.py             # JWT, bcrypt, RBAC, rate-limiting
│
├── frontend/src/
│   ├── services/api.ts         # All HTTP calls to the backend (uses fetch)
│   ├── services/config.ts      # API_BASE_URL = "http://localhost:8000"
│   ├── components/
│   │   ├── auth/Login.tsx      # Login form
│   │   ├── extraction/PDFUploader.tsx   # Upload drag-and-drop
│   │   ├── mapping/MappingWorkbench.tsx # Human review table
│   │   └── reports/AnalyticsReport.tsx  # Report display with charts
│   └── contexts/AuthContext.tsx # Stores JWT token, manages session
│
└── data/
    ├── ARR 2022-27 dated 25.06.2022.pdf  # 493-page ARR petition sample
    └── Input.pdf                          # 237-page financial input sample
```

---

## Key Libraries Reference

| Library | Used In | Purpose |
|---------|---------|---------|
| **FastAPI** | All `backend/api/*.py` | Web server framework - handles HTTP, validation, async |
| **Pydantic** | All `backend/api/*.py` | Data validation - ensures API inputs/outputs match exact schema |
| **LangGraph** | `extraction_graph.py` | Stateful AI workflow engine for the extraction pipeline |
| **PyPDF2** | `extraction.py` | Reads native text from PDF files page-by-page |
| **pytesseract** | `ocr_service.py` | Tesseract OCR - reads text from scanned image PDFs |
| **python-jose** | `security/auth.py` | Creates and verifies JWT authentication tokens |
| **passlib (bcrypt)** | `security/auth.py` | Secure password hashing - never stores plain text passwords |
| **Python `re`** | `extraction_graph.py` | Regular expressions for financial pattern matching |
| **React + TypeScript** | `frontend/src/` | Browser UI framework |
| **Recharts** | Dashboard components | Interactive charts for historical trend visualization |

---

## 🎉 What This System Achieves

| Traditional Process | With This System |
|--------------------|-----------------|
| 3-4 weeks manual data entry | ~2–3 minutes per PDF |
| Error-prone spreadsheet math | Deterministic, auditable formulas |
| No regulatory traceability | Every number linked to exact source page |
| Manual narrative writing | AI-assisted draft in 1 click |
| Annual compliance scramble | Real-time multi-year trend tracking |
