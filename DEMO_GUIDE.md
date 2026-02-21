# 🎬 ARR Truing-Up DSS — Complete Demo Guide

**Version:** 1.0.0 | **Last Updated:** February 21, 2026

This guide walks you through a complete demonstration of the Decision Support System using the included demo data.

---

## 📋 Prerequisites

Before starting the demo, ensure you have:

- **Python 3.10+** installed
- **Node.js 18+** installed
- **Git** for cloning

---

## 🚀 Quick Start (5 minutes)

### Step 1: Initialize Demo Data

```bash
cd demo
python scripts/init_demo.py
```

You'll see demo credentials and sample data loaded.

### Step 2: Start the Backend

```bash
# From project root
cd backend
uvicorn main_secure:app --reload --env-file ../demo/.env.demo
```

Backend will start at: `http://localhost:8000`

### Step 3: Start the Frontend

Open a **new terminal**:

```bash
# From project root
cd frontend
npm install  # First time only
npm start
```

Frontend will start at: `http://localhost:3000`

### Step 4: Login

Use any of these demo credentials:

| Username | Password | Role | What to Demo |
|----------|----------|------|--------------|
| `regulatory.officer@kserc.gov.in` | `DemoPass123!` | Regulatory Officer | Full approval workflow |
| `auditor@utility.com` | `DemoPass123!` | Senior Auditor | Mapping verification |
| `data.entry@utility.com` | `DemoPass123!` | Data Entry Agent | PDF upload |
| `analyst@utility.com` | `DemoPass123!` | Readonly Analyst | View-only access |

---

## 🎭 Demo Scenarios

### Scenario 1: PDF Upload & AI Extraction

**Actor:** Data Entry Agent

1. Login as `data.entry@utility.com`
2. Click **"Upload PDF"** in navigation
3. Drag and drop `demo/sample_pdfs/sample_petition.pdf`
4. Watch the AI extract 12 fields with confidence scores
5. Observe the extraction metadata (page numbers, table indices, cell references)

**Key Points to Highlight:**
- 15-second processing time for 24-page document
- Automatic table detection (Table 38, Table 39)
- Confidence scoring (95% for clear text, 42% for obscured areas)
- Source provenance tracking

---

### Scenario 2: Mapping Workbench (Human-in-the-Loop)

**Actor:** Senior Auditor

1. Login as `auditor@utility.com`
3. Click **"Mapping Workbench"**
4. You'll see 8 pending AI suggestions:

| ID | Source Field | AI Suggestion | Confidence | Your Action |
|----|-------------|---------------|------------|-------------|
| 1 | Employee Salaries | O&M (Controllable) | 95% | ✅ Confirm |
| 2 | Long Term PPA | Power_Purchase (Uncontrollable) | 98% | ✅ Confirm |
| 3 | IEX Spot Purchase | Power_Purchase (Uncontrollable) | 92% | ✅ Confirm |
| 4 | Line Maintenance | O&M (Controllable) | 88% | ✅ Confirm |
| 5 | Interest on Loan | Interest (Uncontrollable) | 96% | ✅ Confirm |
| 6 | Coal Procurement | Power_Purchase (Uncontrollable) | 94% | ✅ Confirm |
| 7 | Transmission O&M | O&M (Controllable) | 85% | ✅ Confirm |
| 8 | Legal Fees | O&M (Controllable) | 67% | ⚠️ Override → Admin (Controllable) |

5. For Item #8 (low confidence), click **Override**
6. Change to **"Admin"** category
7. Add comment: *"Legal fees include regulatory compliance work — reclassifying as Admin per Regulation 7.2"*
8. Click **Submit**

**Key Points to Highlight:**
- Zero-hallucination enforcement: No unverified data enters Rule Engine
- Audit trail: Every override is logged with mandatory comments
- Confidence thresholds: Low-confidence items (<70%) require manual review

---

### Scenario 3: Report Generation & Variance Analysis

**Actor:** Regulatory Officer

1. Login as `regulatory.officer@kserc.gov.in`
2. Click **"Reports"**
3. Select Financial Year: **2024-25**
4. Leave SBU filter empty (show all)
5. Click **"Generate Report"**

**Expected Results:**

```
Approved ARR: ₹2,500.00 Cr
Actual ARR:   ₹2,530.00 Cr
Net Variance:  -₹30.00 Cr (-1.2%)
```

**Variance Breakdown:**

| Cost Head | Category | Approved | Actual | Variance | Disposition |
|-----------|----------|----------|--------|----------|-------------|
| O&M (SBU-D) | Controllable | ₹180 Cr | ₹150 Cr | +₹30 Cr (Gain) | 2/3 Utility, 1/3 Consumer |
| Power_Purchase (SBU-D) | Uncontrollable | ₹400 Cr | ₹450 Cr | -₹50 Cr (Loss) | 100% Pass-through |
| Power_Purchase (SBU-G) | Uncontrollable | ₹800 Cr | ₹850 Cr | -₹50 Cr (Loss) | 100% Pass-through |
| O&M (SBU-T) | Controllable | ₹60 Cr | ₹55 Cr | +₹5 Cr (Gain) | 2/3 Utility, 1/3 Consumer |

**AI Insights Displayed:**

> 💡 **Insight 1:** The O&M head for SBU-D shows a controllable GAIN of ₹30 Crores. This represents efficient management of controllable factors. Per Regulation 9.2, savings are shared 2/3 to Utility, 1/3 to Consumer.

> ⚠️ **Insight 2:** ALERT: Power Purchase for SBU-G shows an uncontrollable LOSS of ₹50 Crores due to market price spikes. Fully passed through per Regulation 9.4.

6. Scroll down to **"Regulatory Recommendations"**

> 🔍 **Recommendation:** PASS-THROUGH REVIEW: 2 uncontrollable items show significant negative variance. Verify market price justification documentation for FY 2024-25.

**Key Points to Highlight:**
- 70:30 CPI:WPI inflation calculation
- 2/3 - 1/3 gain sharing mathematics
- Automatic disallowance of controllable losses
- Year-wise T&D loss trajectory (15.5% → 13.5%)

---

### Scenario 4: SBU Isolation Demo

**Actor:** Regulatory Officer (cross-SBU view)

1. Stay logged in as `regulatory.officer@kserc.gov.in`
2. Generate report for **SBU-D only**
3. Note the data scope is limited to Distribution

**Now switch to:**

4. Open incognito window
5. Login as `auditor@utility.com` (SBU-D access only)
6. Try to access SBU-G data — **Access Denied**

**Key Points to Highlight:**
- Row-Level Security in PostgreSQL
- JWT tokens include SBU access claims
- Strict data isolation between Generation, Transmission, Distribution

---

### Scenario 5: Audit Trail Verification

**Actor:** Any role

1. After completing Scenarios 2-4
2. Go to **Reports** → **Audit Trail** tab
3. View immutable logs showing:
   - Who confirmed each mapping
   - Timestamp with checksum
   - Regulatory clause applied
   - Input data snapshot (for reproducibility)

Example entry:
```json
{
  "timestamp": "2026-02-21T14:32:15Z",
  "checksum": "a1b2c3d4e5f6...",
  "officer": "auditor@utility.com",
  "action": "mapping_override",
  "mapping_id": 8,
  "from": "O&M (Controllable)",
  "to": "Admin (Controllable)",
  "comment": "Legal fees include regulatory compliance work...",
  "regulatory_reference": "Regulation 7.2"
}
```

---

## 📊 Demo Data Summary

### Users (4 accounts)
- 1 Super Admin (not used in demo)
- 1 Regulatory Officer (full access)
- 1 Senior Auditor (SBU-D only)
- 1 Data Entry Agent (SBU-D only)
- 1 Readonly Analyst (all SBUs)

### ARR Data (7 components)
- SBU-D: 3 components (O&M, Power_Purchase, Interest)
- SBU-G: 2 components (O&M, Power_Purchase)
- SBU-T: 2 components (O&M, Depreciation)

### Pending Mappings (8 items)
- Mix of high confidence (85%+) and one low confidence (67%)
- All major cost heads represented
- Includes edge case (Legal Fees ambiguity)

### Sample PDF
- 24 pages of simulated audited financials
- 12 extractable data fields
- Mixed quality (some smudged/obscured areas)

---

## 🔧 Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.10+

# Install dependencies
pip install -r requirements.txt

# Check port availability
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows
```

### Frontend won't start
```bash
# Clear node_modules
cd frontend
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 18+
```

### Login fails
- Ensure backend is running on port 8000
- Check `.env.demo` is loaded (CORS origins)
- Try clearing browser localStorage

---

## 🧹 Cleanup (After Demo)

To remove all demo data:

```bash
# Delete demo folder
rm -rf demo/

# Clear demo database
rm demo/arr_dss_demo.db

# Reset frontend
rm -rf frontend/node_modules
```

---

## 💡 Pro Tips for Live Demo

1. **Practice the flow** — Run through all scenarios once before presenting
2. **Use Regulatory Officer account** — Shows all features
3. **Highlight the "Red Flag"** — Legal Fees low confidence is a good teaching moment
4. **Show the math** — Click into variance details to show 2/3 - 1/3 calculation
5. **Demonstrate security** — Show SBU isolation with two browsers
6. **End with audit trail** — Proves immutability and compliance

---

## 📞 Support

If you encounter issues during demo:

1. Check `demo/TROUBLESHOOTING.md`
2. Review API logs at `http://localhost:8000/docs`
3. Contact: support@utility.com

---

**🎉 You're ready to demo! Start with Scenario 1 above.**
