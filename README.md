<div align="center">
  <img src="frontend/public/dss_logo.png" alt="KSERC DSS Logo" width="150" style="border-radius: 20%; margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  
  <h1 style="margin-top: 0;">KSERC Decision Support System ⚡</h1>
  
  <p><b>"AI-Assisted Regulatory Decisions. Zero Hallucination. 100% Audit Trail. Demo Mode Available."</b></p>
  
  <p>An enterprise-grade, Human-in-the-Loop AI platform for generating KSERC Truing-Up Orders under the Multi-Year Tariff Framework 2022-27. Features dual-mode operation: Production mode for regulatory use and Demo mode for frictionless demonstrations.</p>

  <p>
    <a href="https://github.com/Anudeepsrib/Decision-Support-System">
      <img src="https://img.shields.io/github/stars/Anudeepsrib/Decision-Support-System?style=for-the-badge&logo=github" alt="GitHub stars" />
    </a>
    <a href="https://github.com/Anudeepsrib/Decision-Support-System">
      <img src="https://img.shields.io/github/forks/Anudeepsrib/Decision-Support-System?style=for-the-badge&logo=github" alt="GitHub forks" />
    </a>
    <a href="https://github.com/Anudeepsrib/Decision-Support-System/blob/main/LICENSE">
      <img src="https://img.shields.io/github/license/Anudeepsrib/Decision-Support-System?style=for-the-badge" alt="License" />
    </a>
  </p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/FastAPI-0.100+-005571?style=flat&logo=fastapi" alt="FastAPI" />
    <img src="https://img.shields.io/badge/React-18+-20232A?style=flat&logo=react&logoColor=61DAFB" alt="React" />
    <img src="https://img.shields.io/badge/PostgreSQL-14+-336791?style=flat&logo=postgresql&logoColor=white" alt="PostgreSQL" />
    <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white" alt="Docker" />
  </p>

  <p>
    <a href="#-core-features">Features</a> •
    <a href="#-quick-start">Quick Start</a> •
    <a href="#%EF%B8%8F-tech-stack">Tech Stack</a> •
    <a href="#-architecture">Architecture</a> •
    <a href="#-api-reference">API Reference</a> •
    <a href="#-demo-mode">Demo Mode</a>
  </p>
  
  <a href="https://github.com/Anudeepsrib/Decision-Support-System">
    <img src="https://github-readme-stats.vercel.app/api/pin/?username=Anudeepsrib&repo=Decision-Support-System&theme=radical&show_owner=true" alt="Readme Card" />
  </a>
</div>

---

## ⚡ What is Truing-Up?

Truing-Up is the regulatory process of reconciling the **Approved Annual Revenue Requirement (ARR)** against **Actual audited expenditure** at the end of each financial year. The Commission must compare petition claims, apply gain/loss sharing mechanisms per Regulation 9, and generate legally defensible orders with full justifications.

**This system transforms weeks of manual spreadsheet analysis into a 3-hour AI-assisted workflow with mandatory human oversight.**

---

## 🛡️ Compliance & Auditability Promise

Every decision made within this platform is traceable, justifiable, and legally defensible.

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>🚫 Zero Hallucination</h3>
      <p>Financial values are never fabricated. The rule engine enforces that all actual figures require human verification before entering any order.</p>
    </td>
    <td width="50%" valign="top">
      <h3>🔒 Enterprise Security</h3>
      <p>JWT Authentication with Role-Based Access Control (RBAC). SHA-256 checksums ensure document integrity across the entire pipeline.</p>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>📜 Immutable Audit Trail</h3>
      <p>Every override is permanently tracked with officer identity, timestamp, IP address, and full justification. Nothing is ever silently changed.</p>
    </td>
    <td width="50%" valign="top">
      <h3>⚖️ KSERC Regulatory Compliance</h3>
      <p>Full alignment with the Electricity Act 2003 (Sections 61, 62, 64) and KSERC MYT Regulations 2021 including gain/loss sharing mechanisms.</p>
    </td>
  </tr>
</table>

---

## ✨ Core Features

<table>
  <tr>
    <td width="33%" valign="top">
      <b>🤖 AI + Human-in-the-Loop</b><br/>
      Three decision modes: <b>[A] AI Auto</b> for low-variance items, <b>[P] Pending</b> for flagged items requiring officer review, and <b>[M] Manual Override</b> with mandatory justification.
    </td>
    <td width="33%" valign="top">
      <b>🔍 External Factor Detection</b><br/>
      Automatically detects hydrology events, power purchase volatility, government mandates, court orders, CapEx overruns, and force majeure conditions.
    </td>
    <td width="33%" valign="top">
      <b>📋 8-Section Order Generation</b><br/>
      Generates structured KSERC Truing-Up Orders with regulatory citations, SBU-wise analysis, deviation findings, and embedded decision markers.
    </td>
  </tr>
  <tr>
    <td width="33%" valign="top">
      <b>📄 Intelligent Extraction</b><br/>
      Layout-aware PDF parsing with confidence scoring and source provenance tracking (page, table, cell references) for every extracted value.
    </td>
    <td width="33%" valign="top">
      <b>🎛️ Manual Decision Workbench</b><br/>
      A dedicated officer workspace for reviewing flagged items, submitting justifications, and overriding AI recommendations with full audit logging.
    </td>
    <td width="33%" valign="top">
      <b>🐳 Production-Ready Deployment</b><br/>
      Fully containerized with Docker Compose. Includes PostgreSQL persistence, health checks, and a production deployment checklist.
    </td>
  </tr>
</table>

---

## 🚀 Quick Start

Get the platform running locally in under 10 minutes.

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- (Optional) Tesseract OCR for scanned document support

### 1. Clone & Bootstrap

```bash
git clone https://github.com/Anudeepsrib/Decision-Support-System.git
cd Decision-Support-System

# Backend setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd frontend
npm install
cd ..
```

### 2. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
DATABASE_URL=postgresql://user:pass@localhost/kserc_dss
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Demo Mode Configuration
DEMO_MODE=false                    # Set to 'true' for demo mode
REACT_APP_DEMO_MODE=false         # Frontend demo flag
DEMO_CASE_ID=demo-case-001        # Demo case identifier

# Optional: OpenAI for executive summaries only
# OPENAI_API_KEY=sk-...  # Core logic works 100% offline
```

### 3. Database Migration

```bash
cd backend
alembic upgrade head
```

### 4. Launch

Launch two terminal windows to start the backend engine and frontend interface.

**Terminal 1 — Backend API Server:**
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — React Frontend:**
```bash
cd frontend
npm start
```

### 5. Access the Application

| Endpoint | URL |
|----------|-----|
| **Web UI** | [http://localhost:3000](http://localhost:3000) |
| **API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **Admin Login** | `admin` / `Admin@12345678` (change in production) |
| **Demo Mode** | Set `DEMO_MODE=true` in `.env` and restart |

---

## 🎭 Demo Mode

The system features a dual-mode architecture for both production use and frictionless demonstrations:

### 🎬 Demo Mode Features

When `DEMO_MODE=true`, the system provides:
- **🚀 Auto-logged demo user** - No authentication required
- **📊 Pre-seeded demo data** - Sample case with realistic financial data
- **⚡ Automated decisions** - All `PENDING_MANUAL` auto-converted to `MANUAL_OVERRIDE`
- **📝 Auto-generated justifications** - Marked `[AUTO-GENERATED IN DEMO MODE]`
- **� Draft-only PDF generation** - Demo watermark: "DEMO MODE — NOT FOR REGULATORY USE"
- **🔓 Bypassed validations** - No blocking validation gates
- **🎨 Demo UI indicators** - Banner and info panels showing demo status

### 🏭 Production Mode Features

When `DEMO_MODE=false` (default):
- **🔐 Full authentication** - JWT with role-based access control
- **📋 Manual data input** - No auto-seeded data
- **⚖️ Strict validations** - All regulatory rules enforced
- **📄 Full PDF generation** - Both DRAFT and FINAL modes available
- **🚫 Blocking rules** - FINAL PDF blocked if pending decisions exist
- **📝 Manual justifications** - Required for all overrides

### 🔄 Switching Modes

```bash
# Enable Demo Mode
echo "DEMO_MODE=true" >> .env
echo "REACT_APP_DEMO_MODE=true" >> frontend/.env

# Disable Demo Mode (Production)
sed -i 's/DEMO_MODE=true/DEMO_MODE=false/' .env
sed -i 's/REACT_APP_DEMO_MODE=true/REACT_APP_DEMO_MODE=false/' frontend/.env

# Restart services after changing mode
# Backend: Ctrl+C and restart uvicorn
# Frontend: Ctrl+C and restart npm start
```

### 📖 Demo Guide

For complete demo scenarios and scripts, see:
- [Demo Guide](demo_guide.md) - Quick demo scenarios
- [Complete Demo Guide](docs/DEMO_GUIDE.md) - Detailed walkthrough

---

## �🛠️ Tech Stack

<table>
  <tr>
    <th width="50%">Frontend (React SPA)</th>
    <th width="50%">Backend (Decision Engine)</th>
  </tr>
  <tr>
    <td valign="top">
      <ul>
        <li><b>Framework:</b> React 18 + TypeScript</li>
        <li><b>Styling:</b> Tailwind CSS</li>
        <li><b>Build:</b> Create React App</li>
        <li><b>Language:</b> TypeScript</li>
      </ul>
    </td>
    <td valign="top">
      <ul>
        <li><b>API:</b> FastAPI (Python 3.10+)</li>
        <li><b>Database:</b> PostgreSQL 14+</li>
        <li><b>AI/ML:</b> Custom Decision Classifiers</li>
        <li><b>Security:</b> JWT + bcrypt + RBAC</li>
      </ul>
    </td>
  </tr>
  <tr>
    <th width="50%">Document Processing</th>
    <th width="50%">Infrastructure</th>
  </tr>
  <tr>
    <td valign="top">
      <ul>
        <li><b>PDF Extraction:</b> PyPDF2</li>
        <li><b>OCR:</b> Tesseract (optional)</li>
        <li><b>Table Parsing:</b> Layout-aware engine</li>
        <li><b>Integrity:</b> SHA-256 checksums</li>
      </ul>
    </td>
    <td valign="top">
      <ul>
        <li><b>Containers:</b> Docker + Docker Compose</li>
        <li><b>Migrations:</b> Alembic</li>
        <li><b>Orchestration:</b> Kubernetes (k8s)</li>
        <li><b>Monitoring:</b> Prometheus / Grafana</li>
      </ul>
    </td>
  </tr>
</table>

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     TRUING-UP PIPELINE                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │  Petition   │    │    ARR      │    │   Actuals   │        │
│   │   PDF       │    │   Orders    │    │   Audited   │        │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘        │
│          │                  │                   │               │
│          ▼                  ▼                   ▼               │
│   ┌──────────────────────────────────────────────────────┐     │
│   │          EXTRACTION LAYER (PyPDF2 + OCR)             │     │
│   │   • Layout-aware table parsing                       │     │
│   │   • Confidence scoring                               │     │
│   │   • Source provenance (page, table, cell refs)        │     │
│   └─────────────────────┬────────────────────────────────┘     │
│                         │                                       │
│                         ▼                                       │
│   ┌──────────────────────────────────────────────────────┐     │
│   │        DECISION MODE CLASSIFIER                      │     │
│   │   • Variance analysis (>25% threshold)               │     │
│   │   • External factor detection                        │     │
│   │   • Confidence evaluation (<0.85 threshold)          │     │
│   └─────────────────────┬────────────────────────────────┘     │
│                         │                                       │
│           ┌─────────────┼─────────────┐                        │
│           ▼             ▼             ▼                        │
│      ┌────────┐    ┌────────┐    ┌────────┐                    │
│      │ AI_AUTO│    │ PENDING│    │ MANUAL │                    │
│      │  [A]   │    │  [P]   │    │OVERRIDE│                    │
│      └────┬───┘    └───┬────┘    └───┬────┘                    │
│           │            │             │                          │
│           │            ▼             │                          │
│           │    ┌──────────────┐      │                          │
│           │    │ Officer Review│     │                          │
│           │    │+ Justification│     │                          │
│           │    └──────────────┘      │                          │
│           │            │             │                          │
│           └────────────┼─────────────┘                          │
│                        ▼                                        │
│   ┌──────────────────────────────────────────────────────┐     │
│   │      DOCUMENT GENERATOR (KSERC 8-Section Format)     │     │
│   │   • Draft watermark (if pending decisions)           │     │
│   │   • Justification insertion                          │     │
│   │   • Regulatory clause citations                      │     │
│   └──────────────────────────────────────────────────────┘     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Decision Modes

The system classifies every line item into one of three decision modes based on variance, confidence, and external factors.

| Mode | Label | Trigger Criteria | Action |
|------|-------|------------------|--------|
| **AI Auto** | `[A]` | Variance < 25%, confidence ≥ 0.85, no external factors | Fully automated approval |
| **Pending Manual** | `[P]` | Variance ≥ 25%, external factors detected, low confidence | Requires officer review |
| **Manual Override** | `[M]` | Officer overrides AI recommendation | Mandatory justification (min 50 chars) |

---

## 🔌 API Reference

### Core Endpoints

#### Document Comparison
```http
POST /api/compare/upload
Content-Type: multipart/form-data

order_file: <PDF>
reference_file: <PDF>
```

#### Manual Decisions (Human-in-the-Loop)
```http
GET    /api/manual-decisions/workbench/{sbu_code}
POST   /api/manual-decisions/submit
GET    /api/manual-decisions/progress
POST   /api/manual-decisions/ai-draft-justification
```

#### Order Generation
```http
POST   /api/orders/generate
GET    /api/orders/validate/{order_id}
POST   /api/orders/finalize/{order_id}
GET    /api/orders/{order_id}/preview
```

#### Mapping Workbench
```http
GET    /api/mapping/pending
POST   /api/mapping/generate
POST   /api/mapping/confirm
```

---

## ⚙️ Configuration

Your instance can be customized via the `.env` file:

```env
# Database Connection
DATABASE_URL=postgresql://user:pass@localhost/kserc_dss

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Optional: AI-assisted executive summaries
# OPENAI_API_KEY=sk-...

# Core decision logic is fully offline — no external AI dependency
```

---

## 📊 Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| **Extraction Accuracy** | ≥ 90% | ✅ Implemented |
| **Decision Alignment** | ≥ 85% | ✅ AI + Human Review |
| **Audit Traceability** | 100% | ✅ SHA-256 + Immutable Logs |
| **Zero Hallucination** | 0 fabricated values | ✅ Rule Engine Enforcement |
| **Order Generation Time** | < 3 hours | ✅ (vs. 2 weeks manual) |

---

## 🚢 Deployment

### Docker (Recommended)

```bash
# Build and start all services
docker-compose up --build

# Or detached mode
docker-compose up -d
```

### Production Checklist

- [ ] Change default admin credentials
- [ ] Configure PostgreSQL with SSL
- [ ] Set up Redis for caching (optional)
- [ ] Enable HTTPS/TLS termination
- [ ] Configure backup strategy
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Enable audit log rotation
- [ ] Configure CORS for production domain

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | Complete technical implementation details |
| [Beginner's Guide](docs/BEGINNERS_GUIDE.md) | Plain-English guide for new users |
| [Demo Guide](docs/DEMO_GUIDE.md) | Step-by-step demo scenarios |
| [Quick Demo Guide](demo_guide.md) | Fast demo scenarios for presentations |
| [Security Architecture](docs/SECURITY.md) | Security architecture & compliance |
| [Design System](docs/design_system.md) | UI/UX design principles |
| [Demo vs Production Validation](docs/DEMO_VALIDATION_REPORT.md) | Complete validation report for dual-mode system |

---

## ⚖️ Regulatory Framework

This platform is built for strict compliance with Indian electricity regulation:

- **Electricity Act, 2003** — Sections 61, 62, 64
- **KSERC Multi-Year Tariff Regulations, 2021**
  - **Regulation 5.1** — O&M Escalation (CPI:WPI 70:30)
  - **Regulation 6.3** — Normative Interest (SBI EBLR + 2%)
  - **Regulation 7.4** — T&D Loss Target Trajectory
  - **Regulation 9.2** — Controllable Gains Sharing (2/3 Utility, 1/3 Consumer)
  - **Regulation 9.3** — Controllable Loss Disallowance (100% Utility borne)
  - **Regulation 9.4** — Uncontrollable Pass-Through (100% Consumer recovery)

---

## ⚠️ Disclaimer
**Regulatory Decision Support Only:** This platform is a decision-support tool designed to assist regulatory officers. It does **not** replace the legal authority of the Commission. All final decisions carry legal weight only when approved and signed by authorized KSERC officers.

---

<div align="center">
  <p>Built with ❤️ for the Kerala State Electricity Regulatory Commission</p>
  <p><i>Ensuring Fair, Transparent, and Efficient Tariff Regulation</i></p>
</div>
