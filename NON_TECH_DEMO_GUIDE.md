# Executive Demo Guide: ARR Truing-Up Decision Support System

Welcome to the **ARR Truing-Up Decision Support System** (DSS). This application is designed to modernize and automate the review of Annual Revenue Requirement (ARR) petitions using AI, ensuring strict compliance with KSERC MYT Framework 2022-27.

This guide provides a step-by-step walkthrough for non-technical stakeholders to experience the system's core capabilities.

---

## 🚀 1. Starting the Application

To view the demonstration, you need to ensure the application is running. Open two terminal/command prompt windows in the project folder and run the following commands:

**Terminal 1 (Backend Server):**
```bash
# Windows
$env:DEBUG="true"; .\venv\Scripts\python.exe -m uvicorn backend.main:app --reload

# Mac/Linux
export DEBUG="true" && venv/bin/uvicorn backend.main:app --reload
```

**Terminal 2 (Frontend Interface):**
```bash
cd frontend
npm start
```
*Your web browser will automatically open to `http://localhost:3000`.*

---

## 🔐 2. Accessing the System

We have provisioned a demo "Regulatory Officer" account with full access to the system. 
When the login screen appears, use the following credentials:

* **Email:** `regulatory.officer@kserc.gov.in`
* **Password:** `TempPass123!`

*Notice the professional, premium branding. The system enforces Role-Based Access Control, ensuring different users (Auditors, Analysts) only see what they are authorized to see.*

---

## 📊 3. The Dashboard (Command Center)

Upon logging in, you will land on the **Dashboard**. This is the executive overview providing a snapshot of regulatory compliance.

**Key Features to Notice:**
* **Welcome Card:** Confirms your role and access level (e.g., Access to SBU-G, SBU-T, SBU-D).
* **Efficiency Analysis Module:** Allows you to quickly test Transmission & Distribution (T&D) line loss. 
  * *Try this:* Enter "11.50" (Target) in the actual loss box and click "Evaluate". You will see a green success message. Now enter "12.20" — the system will instantly format to a red alert, cite the regulatory clause, and estimate a penalty in Crores.
* **Historical Trends:** Scroll down to see interactive, multi-year charts tracking Approved vs. Actual costs and the Net Revenue Gap trajectory.

---

## 📄 4. Ingesting Petitions (PDF Uploader)

Next, we will simulate receiving a massive, unstructured PDF petition from a utility company.

1. Click **Upload PDF** in the top navigation bar.
2. Open your computer's file explorer and navigate to the `data/demo_files/` folder inside this project.
3. Drag and drop the file named **`1_True_Up_Petition_SBU_D_FY25.pdf`** into the upload zone.
4. *What happens:* Behind the scenes, the AI engine is reading the document, bypassing standard text extraction, and intelligently identifying key financial metrics amidst paragraphs of text and complex tables.

---

## 🤖 5. Validating AI Intelligence (Mapping Workbench)

Now, we check the AI's work. The system does not silently alter data; it operates as an "Assistant," requiring human confirmation.

1. Click **Mapping Workbench** in the top navigation bar.
2. Here, you see the "Pending AI Suggestions" extracted from the petition you just uploaded.
3. **Key Features to Notice:**
   * **Confidence Scores:** The AI assigns a percentage score to how confident it is in its extraction.
   * **Traceability:** It tells you exactly *where* it found the number (e.g., "Page 12, Table 1").
   * **Standardization:** It maps raw, messy text (e.g., "Rs. 180.00 Cr") securely into the standardized KSERC Chart of Accounts database.
4. Click the **Confirm** (Checkmark) button on a few mappings to officially lock them into the regulatory ledger.

---

## 📈 6. The Final Deliverable (Analytical Reports)

The ultimate goal of the system is to drastically reduce the time it takes to generate the final regulatory order.

1. Click **Reports** in the top navigation bar.
2. Select **Financial Year: 2024-25** and click **Generate Report**.
3. **Key Features to Notice:**
   * **Instant Variance Calculation:** The system immediately compares the newly uploaded "Actual" figures against the MYT "Approved" baseline and calculates the exact net variance (e.g., -3.00 Cr).
   * **Anomaly Detection:** It flags severe deviations that require manual auditing.
   * **Automated Insights & Recommendations:** Read the text boxes under "AI Insights." The system has automatically applied complex regulatory logic (e.g., "Per Regulation 9.2, savings are shared 2/3 to Utility..."). It writes the initial draft of the regulatory narrative for you.

---

### 🎉 Conclusion
You have just experienced a workflow that traditionally takes weeks of manual data entry, PDF scrubbing, and spreadsheet calculation. The **ARR Truing-Up DSS** has reduced it to a matter of clicks, dramatically increasing speed, accuracy, and regulatory confidence.
