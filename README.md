<div align="center">

# ⚡ KSERC Truing-Up AI Decision Support System

**Enterprise-Grade Regulatory Decision Platform with Human-in-the-Loop Intelligence**

[![Status](https://img.shields.io/badge/Status-Production_Ready-success?style=for-the-badge&logo=checkmark&color=2E7D32)](https://github.com/Anudeepsrib/Decision-Support-System)
[![Version](https://img.shields.io/badge/Version-3.0.0-blue?style=for-the-badge&logo=semver&color=1565C0)](https://github.com/Anudeepsrib/Decision-Support-System/releases)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=for-the-badge)](LICENSE)

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-005571?style=flat&logo=fastapi)
![React](https://img.shields.io/badge/React-18+-20232A?style=flat&logo=react&logoColor=61DAFB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791?style=flat&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)

**KSERC Compliant | Zero Hallucination | 100% Audit Trail**

[Quick Start](#quick-start) • [Features](#key-features) • [Architecture](#architecture) • [Documentation](#documentation) • [API Reference](#api-reference)

</div>

---

## 🎯 Overview

The **KSERC Truing-Up AI Decision Support System** is a production-grade regulatory platform designed for the **Kerala State Electricity Regulatory Commission (KSERC)**. It automates the generation of Truing-Up Orders under the Multi-Year Tariff (MYT) Framework 2022-27 while ensuring strict compliance with the Electricity Act, 2003.

### What is Truing-Up?

Truing-Up is the regulatory process of reconciling the **Approved Annual Revenue Requirement (ARR)** against **Actual audited expenditure** at the end of each financial year. The Commission must:
- Compare Petition claims vs Approved vs Actual figures
- Apply Gain/Loss Sharing mechanisms per Regulation 9
- Generate legally defensible orders with full justifications

This system transforms weeks of manual spreadsheet analysis into a **3-hour AI-assisted workflow** with mandatory human oversight.

---

## 🚀 Key Features

### 1. 🤖 AI + Human-in-the-Loop Decision Engine

| Decision Mode | Description | Trigger |
|--------------|-------------|---------|
| **[A] AI Auto** | Fully automated approval | Variance < 25%, confidence ≥ 0.85, no external factors |
| **[P] Pending Manual** | Requires officer review | Variance ≥ 25%, external factors detected, low confidence |
| **[M] Manual Override** | Officer overrides AI | Mandatory justification required (min 50 chars) |

### 2. 🔍 External Factor Detection

Automatically detects and flags:
- **Hydrology**: Poor monsoon, drought, flood conditions
- **Power Purchase Volatility**: Fuel price spikes, market volatility
- **Government Mandates**: Policy changes, subsidy adjustments
- **Court Orders**: Legal interventions affecting tariffs
- **CapEx Overruns**: Capital expenditure exceeding 30% threshold
- **Force Majeure**: Natural disasters, pandemics

### 3. 📋 KSERC-Compliant Document Generation

Generates structured Truing-Up Orders with 8 mandatory sections:
1. Introduction
2. Regulatory Framework (Electricity Act 2003, Sections 61, 62, 64)
3. Petition Summary
4. SBU-wise Analysis (SBU-G, SBU-T, SBU-D)
5. Deviations & Findings
6. Commission Decisions
7. Final Order
8. Appendix (Manual Decisions Summary)

**Hard Compliance Rules:**
- ✅ No hallucination of financial values
- ✅ Mandatory justification for all overrides
- ✅ Draft watermark blocks finalization if pending decisions exist
- ✅ Embedded decision markers [A], [M], [P] for audit trail

### 4. 🛡️ Enterprise Security & Audit

- **JWT Authentication** with Role-Based Access Control (RBAC)
- **SHA-256 Checksums** for document integrity
- **Immutable Audit Logs** — Every override tracked with officer identity, timestamp, IP
- **Zero-Hallucination Enforcement** — Actual values require human verification

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRUING-UP PIPELINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│   │  Petition   │    │    ARR      │    │   Actuals   │       │
│   │   PDF       │    │   Orders    │    │   Audited   │       │
│   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘       │
│          │                  │                  │              │
│          ▼                  ▼                  ▼              │
│   ┌─────────────────────────────────────────────────────┐    │
│   │          EXTRACTION LAYER (PyPDF2 + OCR)              │    │
│   │   • Layout-aware table parsing                       │    │
│   │   • Confidence scoring                               │    │
│   │   • Source provenance (page, table, cell refs)     │    │
│   └─────────────────────┬───────────────────────────────┘    │
│                         │                                      │
│                         ▼                                      │
│   ┌─────────────────────────────────────────────────────┐    │
│   │        DECISION MODE CLASSIFIER                     │    │
│   │   • Variance analysis (>25% threshold)               │    │
│   │   • External factor detection                      │    │
│   │   • Confidence evaluation (<0.85 threshold)        │    │
│   └─────────────────────┬───────────────────────────────┘    │
│                         │                                      │
│           ┌─────────────┼─────────────┐                       │
│           ▼             ▼             ▼                       │
│      ┌────────┐    ┌────────┐    ┌────────┐                   │
│      │ AI_AUTO│    │ PENDING│    │ MANUAL │                   │
│      │  [A]   │    │ [P]    │    │OVERRIDE│                   │
│      └────┬───┘    └───┬────┘    └───┬────┘                   │
│           │            │            │                         │
│           │            ▼            │                         │
│           │    ┌──────────────┐    │                         │
│           │    │ Officer Review│    │                         │
│           │    │ + Justification│   │                         │
│           │    └──────────────┘    │                         │
│           │            │            │                         │
│           └────────────┼────────────┘                         │
│                        ▼                                      │
│   ┌─────────────────────────────────────────────────────┐    │
│   │      DOCUMENT GENERATOR (KSERC 8-Section Format)   │    │
│   │   • Draft watermark (if pending decisions)          │    │
│   │   • Justification insertion                       │    │
│   │   • Regulatory clause citations                     │    │
│   └─────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | Python 3.10+, FastAPI | High-performance API server |
| **Frontend** | React 18, TypeScript, Tailwind CSS | Responsive enterprise UI |
| **Database** | PostgreSQL 14+ | Relational data with JSON support |
| **Document Processing** | PyPDF2, Tesseract OCR | PDF text and table extraction |
| **AI/ML** | Custom classifiers (no LLM for core logic) | Decision mode classification |
| **Security** | JWT, bcrypt, RBAC | Enterprise authentication |
| **Deployment** | Docker, Docker Compose | Containerized deployment |

---

## ⚡ Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+
- (Optional) Tesseract OCR for scanned documents

### 1. Clone & Setup

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

# Optional: OpenAI for executive summaries only
# OPENAI_API_KEY=sk-...  # Core logic works 100% offline
```

### 3. Database Migration

```bash
cd backend
alembic upgrade head
```

### 4. Start Development Servers

```bash
# Terminal 1: Backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm start
```

### 5. Access the Application

- **Web UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Admin Login**: `admin` / `Admin@12345678` (change in production)

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | Complete technical implementation details |
| [docs/BEGINNERS_GUIDE.md](docs/BEGINNERS_GUIDE.md) | Plain-English guide for new users |
| [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) | Step-by-step demo scenarios |
| [docs/SECURITY.md](docs/SECURITY.md) | Security architecture & compliance |
| [docs/design_system.md](docs/design_system.md) | UI/UX design principles |
| [docs/PROPOSAL_VS_IMPLEMENTATION.md](docs/PROPOSAL_VS_IMPLEMENTATION.md) | Feature mapping & roadmap |

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

## 🎭 Demo Scenarios

### Scenario 1: AI Auto-Approval (Happy Path)
1. Upload Petition PDF with 2% variance from Approved ARR
2. System classifies as **[A] AI Auto**
3. Decision appears in Final Order automatically

### Scenario 2: External Factor Detection
1. Upload Petition citing "monsoon failure" and 30% variance
2. System detects **Hydrology** external factor
3. Flags as **[P] Pending Manual** for officer review
4. Officer reviews and confirms with justification

### Scenario 3: Manual Override
1. AI recommends **DISALLOW** for controllable loss
2. Officer overrides to **PARTIAL** with 50-char justification
3. System marks **[M] Manual Override** in Appendix
4. Justification embedded verbatim in Final Order

---

## 🧪 Testing

```bash
# Run all tests
cd backend
pytest tests/ -v --tb=short

# Run specific test suites
pytest tests/test_decision_classifier.py -v
pytest tests/test_document_generator.py -v
pytest tests/test_order_comparison.py -v

# With coverage
pytest --cov=backend --cov-report=html
```

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

## 📊 Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Extraction Accuracy | ≥ 90% | ✅ Implemented |
| Decision Alignment | ≥ 85% | ✅ AI + Human Review |
| Audit Traceability | 100% | ✅ SHA-256 + Immutable Logs |
| Zero Hallucination | 0 fabricated values | ✅ Rule Engine Enforcement |
| Order Generation Time | < 3 hours | ✅ (vs. 2 weeks manual) |

---

## ⚖️ Compliance & Regulatory Framework

- **Electricity Act, 2003** — Sections 61, 62, 64
- **KSERC Multi-Year Tariff Regulations, 2021**
- **Regulation 5.1** — O&M Escalation (CPI:WPI 70:30)
- **Regulation 6.3** — Normative Interest (SBI EBLR + 2%)
- **Regulation 7.4** — T&D Loss Target Trajectory
- **Regulation 9.2** — Controllable Gains Sharing (2/3 Utility, 1/3 Consumer)
- **Regulation 9.3** — Controllable Loss Disallowance (100% Utility borne)
- **Regulation 9.4** — Uncontrollable Pass-Through (100% Consumer recovery)

---

## 🤝 Contributing

This is a proprietary system developed for KSERC. For issues or feature requests, please contact:

**Project Maintainer**: [Anudeep Sribhashyam](mailto:anudeep.sribhashyam@example.com)

---

## 📜 License

**Proprietary Software** — All rights reserved. Unauthorized use, reproduction, or distribution is strictly prohibited.

---

<div align="center">

**Built with ❤️ for Kerala State Electricity Regulatory Commission**

*Ensuring Fair, Transparent, and Efficient Tariff Regulation*

</div>
