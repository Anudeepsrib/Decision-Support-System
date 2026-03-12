# Quick Demo Guide: Deterministic Order Comparison

This guide provides the exact steps to demonstrate the zero-hallucination deterministic comparison pipeline.

## 1. Using the Headless CLI

If your stakeholders just want to see raw speed and deterministic JSON outputs, use the `compare.py` script. We've included two sample PDFs in the repository `data/` folder.

```bash
# Make sure you are in the project root with the Python venv activated
python compare.py "data\6YcMQSwV8IjVUpPx77szijItUeQK3UqB6LGPWicu (2).pdf" "data\YXvxOwoHebyxwMFCMT5z3qWOyVJxheLtLuJR4uJP.pdf"
```

**What happens:**
1. The engine strips the text from both PDFs.
2. It uses targeted `re` regex patterns to find headers, dates, and addresses.
3. It parses the line-item tables via multi-space heuristics.
4. It compares the items strictly using `difflib.SequenceMatcher`.
5. Outputs `comparison_result.json` and a plain-text `comparison_report.txt`.

*Note: Since the demo PDFs are generic electrical tariffs rather than identical identical POs, the system will accurately flag the result as a **CRITICAL_DISCREPANCY** with hundreds of missing items.*

## 2. Using the Web UI

To show the beautiful Anomaly Emoji tagging system and confidence rings:

### Start the Servers:
```bash
# Terminal 1 - Inside /backend
uvicorn main:app --reload

# Terminal 2 - Inside /frontend
npm start
```

### Run the Flow:
1. Open **http://localhost:3000**
2. Login as `admin` / `Admin@12345678`
3. Click the **Order Compare** tab in the sidebar navigation.
4. Drag the first PDF from `data/` into the Order box, and the second into the Reference box.
5. Click **Compare Documents**.

**Key UI Elements to Demo:**
- **Anomaly Emojis:** Highlight how the system tags Exact Matches (✅), Mismatches (❌), Missing Items (⚠️), and Extra Items (ℹ️).
- **CSS Distribution Bar:** Hover over the color segments to show the percentage breakdown of the comparison.
- **Risk Assessment Card:** Explain how the deterministic engine hard-codes the risk mapping (e.g., if there are *any* missing items, Risk = HIGH).
- **The Dual Reports:** Show the bottom of the page. The left side is the 100% deterministic text report. The right side is the optional LLM report (which will show "LLM Report Disabled" if you haven't configured an OpenAI API key).
