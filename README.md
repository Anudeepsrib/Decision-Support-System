# Annual Revenue Requirement (ARR) Decision Support System
## Comprehensive End-to-End Stakeholder Guide

![Status](https://img.shields.io/badge/Status-Enterprise_Ready-success?style=for-the-badge&logo=checkmark)
![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)
<br>
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-1C1C1C?style=for-the-badge&logo=openai)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

Welcome to the ARR Decision Support System. This document serves as a complete, plain-language guide covering everything from the underlying business strategy to running a live enterprise deployment.

---

## 1. Requirements — What the Project Needs and Why

**The Challenge:** 
Regulatory agencies, such as the Kerala State Electricity Board (KSEB), analyze vast amounts of financial data submitted by utility companies for establishing Annual Revenue Requirements. Searching through hundreds of PDF pages to extract financial tables, verify the math, and apply rigid regulatory rules is traditionally a slow, error-prone, and highly manual process.

**The Solution:**
We need an intelligent, automated system that acts as a digital assistant to Regulatory Officers. The system must reliably extract data from rigid PDFs, apply regulatory rules mathematically without guessing or making up numbers ("Zero Hallucination"), and ultimately keep a human in control of the final decision. 

**Why it matters:** 
By automating the data entry and basic math checks, the agency significantly reduces the time it takes to review financial claims, minimizes costly human errors, and maintains an auditable trail of every decision made.

---

## 2. Features — System Breakdown & Business Value

- **Automated AI Data Extraction:**
  - *What it does:* Uses artificial intelligence to "read" PDF reports and extract specific financial tables natively into the system.
  - *Value:* Saves hours of manual data transcription and prevents copy-paste errors.

- **Human-in-the-Loop Mapping Workbench:**
  - *What it does:* Pauses the AI process to show the extracted numbers to a human user. The user can review, correct, or approve the numbers before any financial calculations occur.
  - *Value:* Builds trust. The AI is purely an assistant; the human remains the final authority and auditor.

- **Deterministic Rule Engine (The Math Checker):**
  - *What it does:* Runs the exact mathematical formulas required by regulatory law (e.g., KSERC MYT Framework) on the structured, human-approved data.
  - *Value:* Guarantees 100% mathematical accuracy. The AI never guesses the final financial outcome; hardcoded strict logic calculators do.

- **Intelligent Anomaly Detection:**
  - *What it does:* Scans the incoming data against historical baselines to flag unusual spikes in costs (like a sudden historical 50% jump in Power Purchase pricing).
  - *Value:* Instantly highlights suspicious data naturally, directing the human auditor's attention exactly where it's needed most efficiently.

- **Data-Dense Executive Dashboard:**
  - *What it does:* Displays the final accepted vs. rejected costs in a clean, comprehensive digital interface.
  - *Value:* Provides immediate, digestible insights to executives and stakeholders without needing to read a 100-page report.

---

## 3. Implementation Overview

How is the solution actually built? Imagine an automated factory assembly line with three main stations:

1. **The Brain (Backend AI Pipeline):** When a user uploads a PDF, the system's "Brain" reads the document. If it gets confused, it attempts to self-correct. Once it extracts the data, it pauses the assembly line.
2. **The Inspection Station (Frontend User Interface):** The system alerts the human worker. The human reviews the data on a clean, digital dashboard, fixes any typos the AI might have made, and hits "Approve".
3. **The Strict Calculator (Rule Engine):** Once approved, the data flows into a strict calculator. The calculator applies the heavy regulatory math and spits out the final approved budgets and variance reports. 

Everything is securely saved to a digital filing cabinet (the database) so the history of the document can be audited years later via an Audit Trail.

---

## 4. Software & Dependencies (Plain Language)

To build this modern assembly line securely, we use specific industry-standard tools:

- **React & TailwindCSS (The "Look and Feel"):** These are the tools used to build the website you click on. They ensure the dashboard is fast, interactive, and looks highly professional on any screen.
- **FastAPI (The "Traffic Cop"):** This framework handles all the data traveling between the user's screen and the server. It manages speed, scale, and ensures data is routed quickly and securely.
- **PostgreSQL (The "Digital Filing Cabinet"):** A highly secure, enterprise-grade database that permanently stores user profiles, historical financial records, and every audit report securely.
- **LangGraph & LangSmith (The "AI Managers"):** These tools manage the AI operations. *LangGraph* creates the step-by-step workflow for the AI to follow, ensuring it knows when to pause for human review. *LangSmith* acts as a security camera, recording every single decision the AI makes so we can trace its internal logic if something goes wrong.
- **Docker (The "Shipping Container"):** Docker wraps all the code, settings, and tools into a tidy isolated box. This ensures the software runs identically on any computer or cloud server in the world, preventing the classic "it works on my machine" problem.

---

## 5. Environment Configuration

Before the system can boot up, it needs a set of digital keys and instructions. These are stored in hidden configuration files called `.env` (Environment Variables). 

### Where to put them
You need to create a `.env` file inside the `backend/` folder and another `.env` file in the `frontend/` folder.

### What goes inside `backend/.env`
```env
# The environment setting: "development" for testing on your laptop, "production" for the live internet.
ENVIRONMENT=development

# Database Connection: Tells the backend exactly where the PostgreSQL filing cabinet is located natively.
DATABASE_URL=postgresql+asyncpg://dss_user:dss_pass@localhost:5432/arr_dss

# AI Keys: Your private passwords to use OpenAI's brain and LangSmith's tracking cameras securely.
OPENAI_API_KEY=sk-your-private-key-here
LANGCHAIN_API_KEY=lsv2_your-private-key-here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=arr_dss_pipeline
```
*Note: Never share these keys or post them online!*

### What goes inside `frontend/.env`
```env
# Tells the internet browser where exactly to send data to reach the backend traffic cop operations.
VITE_API_URL=http://localhost:8000
```

---

## 6. Demo Guide

If you need to show the system to a client or stakeholder, follow these simple steps to start a local demonstration entirely on your laptop:

**Step 1: Start the Backend (The Engine)**
1. Open your computer's **Terminal** (on Mac, search for "Terminal"; on Windows, search for "Command Prompt").
2. Tell the Terminal to go into the backend folder by typing this exactly and pressing Enter: 
   ```bash
   cd backend
   ```
3. Activate the secure Python workspace so the engine knows what tools to use:
   - On Windows, type: `venv\Scripts\activate`
   - On Mac/Linux, type: `source venv/bin/activate`
4. Start the engine securely by typing: 
   ```bash
   uvicorn main:app --reload
   ```
   *(Leave this Terminal window open! It is quietly running the engine in the background.)*

**Step 2: Start the Frontend (The User Interface)**
1. Open a **brand new** Terminal window (do not close the first one).
2. Tell this new Terminal to go into the frontend folder:
   ```bash
   cd frontend
   ```
3. Start drawing the website by typing: 
   ```bash
   npm run dev
   ```

**Step 3: Run the Demonstration**
1. Open your everyday web browser (like Chrome or Edge) and type `http://localhost:5173` into the top address bar.
2. **Show the Upload:** You will see the ARR Dashboard. Upload a sample KSEB PDF document here.
3. **Show Human-in-the-Loop:** Navigate to the "Mapping Workbench" screen. Show your stakeholders how the AI extracted the numbers from the PDF. Crucially, demonstrate manually changing one number to prove the human has ultimate control.
4. **Show the Results:** Click "Approve" and navigate to the Main Dashboard to show the final, highly accurate mathematical outputs.

---

## 7. Production Deployment (Going Live)

When it is time to move the system off your laptop and onto the live internet for real users, we use **Docker**. Docker is like a universal shipping container—it packages our entire factory up so it runs perfectly on any company server in the world.

**Step 1: Prepare the Live Server**
Ensure the live company server (like AWS, Azure, or your internal IT server) has **Docker** and **Docker Compose** installed. (Your IT team can do this in one click).

**Step 2: Transfer Files and Setup Keys**
Copy this entire project folder to the live server. Create your `.env` password files exactly as described in Section 5. 
*Important:* Only change `ENVIRONMENT=development` to `ENVIRONMENT=production` in the backend so the system knows it is live. Ensure you replace `sk-your-private-key-here` with your actual, real passwords from OpenAI!

**Step 3: Build and Launch**
Open the server's Terminal. Ensure you are inside the main, top-level project folder (where the `docker-compose.yml` file is located). Type this single command:

```bash
docker-compose up --build -d
```

**Step 4: What this single command does autonomously:**
1. It reads the master blueprint (`docker-compose.yml`).
2. It builds the secure PostgreSQL database locally.
3. It installs all the Python tools and boots up the `run_prod.py` script. This script automatically checks how powerful the server is and scales the engine to run as fast as biologically possible.
4. It builds the React website so users can log in.
5. It ties everything together into a secure network. 
6. The `-d` at the end of the command tells the system to run "detached"—meaning you can safely close your Terminal window and the software will stay online forever.

The Decision Support System is now live, robust, and running securely for enterprise consumption!

---

## 8. Further Reading (Documentation)

For deeper insights into the project's sub-systems, refer to our comprehensive manuals located in the `docs/` directory:

- [`docs/BEGINNERS_GUIDE.md`](./docs/BEGINNERS_GUIDE.md) - Understanding the regulatory context and core features.
- [`docs/DEMO_GUIDE.md`](./docs/DEMO_GUIDE.md) - How to run demo data payloads and sandbox the AI logic.
- [`docs/SECURITY.md`](./docs/SECURITY.md) - Deep dive into RBAC, authentication logic, and rate-limiting protocols.
- [`docs/design_system.md`](./docs/design_system.md) - UI design principles, aesthetic standards, and color tokens.
