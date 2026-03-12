# Deterministic Document Comparison System
## Zero-Hallucination Order & Reference Comparator

![Status](https://img.shields.io/badge/Status-Enterprise_Ready-success?style=for-the-badge&logo=checkmark)
![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)
<br>
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)

Welcome to the **Deterministic Document Comparison System**. This system provides a 100% rule-based, reproducible, zero-hallucination pipeline for comparing Order PDFs against Reference PDFs to detect anomalies, missing items, and financial discrepancies.

---

## 1. System Objective

The core objective of this system is to remove the unreliability and hallucination risks associated with Large Language Models (LLMs) when processing rigid financial or supply chain documents. 

Instead of asking an AI to "compare these two documents," this system strictly extracts, normalizes, and mathematically compares data using Python standard libraries (`re`, `difflib`, `datetime`), ensuring that the same two documents will **always** produce the exact same variance report.

## 2. Core Features

- **Rule-Based Extraction Engine:** 
  Utilizes targeted regex patterns to extract Order Numbers, Dates, Customer Names, and structured Line Items from unformatted PDF text.
- **Table Parsing Heuristics:**
  Intelligently splits table rows using multi-space and tab delimiters to isolate product names from quantities, unit prices, and total prices.
- **Deterministic Field Matching:**
  - **Exact Matching:** For hard identifiers like Order Numbers and normalized Dates.
  - **Fuzzy Mathing (`difflib`):** For Customer Names (threshold >= 0.70) and Shipping Addresses.
  - **Item Resolution:** Maps line items between the Order and Reference documents using a strictly calibrated `0.80` string similarity threshold.
- **Mathematical Variance Engine:**
  Highlights quantity mismatches and flags unit price derivations strictly beyond a ±1.0% tolerance.
- **Deterministic Confidence Scoring:**
  A mathematical formula calculates extraction confidence (0-100%) by penalizing "NOT_FOUND" fields and unmatched items, entirely bypassing arbitrary LLM confidence guessing.
- **Headless CLI & Rich UI:**
  Run heavy batch comparisons headlessly via `compare.py` or interact with the beautiful React frontend featuring Anomaly Emojis (✅❌⚠️🚨) and interactive CSS distribution charts.

## 3. Architecture & Tech Stack

- **Backend:** Python + FastAPI
- **Extraction & Logic:** `PyPDF2`, `re`, `difflib`, `dateutil`
- **Optional Reporting:** `langchain-openai` (Isolated specifically for generating a human-readable summary if an API key is provided).
- **Frontend:** React + Tailwind CSS + Recharts
- **Deployment:** Ready for Docker containerization.

---

## 4. Run the Application Local Demo

### 4.1 CLI Headless Execution
You can run the core pipeline without starting the web servers:
```bash
python compare.py path/to/order.pdf path/to/reference.pdf
```
This produces three files:
1. `comparison_result.json`
2. `comparison_report.txt` (Deterministic Report)
3. `comparison_report_llm.txt` (Optional, if `OPENAI_API_KEY` is set)

### 4.2 Web User Interface
Start the backend API and the frontend UI in two separate terminals.

**Terminal 1 (Backend):**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm install
npm start
```

### 4.3 Navigating the UI
1. Open `http://localhost:3000` in your browser.
2. Login with the default credentials:
   - **User:** `admin`
   - **Password:** `Admin@12345678`
3. Navigate to the **Order Compare** tab in the sidebar.
4. Drag and drop your Order and Reference PDFs to instantly see the deterministic comparison and anomaly visualization.

---

## 5. Security & Optional LLM Setup

**No LLM Required for Core Logic**
The system is built to run 100% offline and deterministically. However, if you would like a short 3-paragraph executive summary generated at the bottom of the comparison report:

1. Create a `backend/.env` file.
2. Add your key: `OPENAI_API_KEY=sk-...`

If the key is missing or invalid, the system gracefully disables the LLM route and relies exclusively on the generated plain-text deterministic report.
