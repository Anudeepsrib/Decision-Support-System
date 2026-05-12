# KSERC Decision Support System — MVP

A clean, demo-ready MVP for KSERC Truing-Up Order generation. Upload ARR orders and petition PDFs, extract financial tables, compare approved vs actual values, review flagged items, and generate KSERC-style draft orders.

## 🚀 Quick Start

### Option 1: macOS Local Development (Recommended)

#### First-time Setup:
```bash
# Clone and navigate to project
git clone <repository-url>
cd Decision-Support-System

# One-time setup (installs system dependencies)
./setup-mac.sh
```

#### Start the MVP:
```bash
# One-command startup
./start-mvp-mac.sh

# Or use Makefile
make start    # Start both services
make backend  # Start only backend
make frontend # Start only frontend
```

### Option 2: Manual Startup
```bash
# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup frontend
cd frontend && npm install && cd ..

# Start backend (Terminal 1)
source venv/bin/activate
cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Start frontend (Terminal 2)
cd frontend
npm run dev
```

### Option 3: Docker (Optional)
```bash
docker-compose up --build
```

## 📱 Access Points

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                  React Frontend                  │
│  Upload → Extract → Compare → Review → Generate │
└─────────────────────┬───────────────────────────┘
                      │ REST API
┌─────────────────────▼───────────────────────────┐
│              FastAPI Backend                      │
│  /api/upload  /api/extract  /api/compare         │
│  /api/review  /api/generate  /api/audit          │
└──────┬──────────────┬───────────────────────────┘
       │              │
  ┌────▼────┐   ┌─────▼─────┐
  │ SQLite  │   │ File Store│
  │ (DB)    │   │ (uploads/ │
  │         │   │  outputs/)│
  └─────────┘   └───────────┘
```

## 📋 Features

### Core Workflow
1. **Document Upload**: Upload ARR orders and truing-up petitions (PDF)
2. **Table Extraction**: Automatic extraction of financial tables using pdfplumber
3. **Data Normalization**: Map extracted rows to canonical KSERC cost heads
4. **Variance Comparison**: Compare approved vs actual vs claimed values
5. **Officer Review**: Review flagged items with variance ≥ 15%
6. **Order Generation**: Generate KSERC-style draft orders with DRAFT watermark

### API Endpoints
- `POST /api/documents/upload` — Upload PDFs
- `GET /api/extraction/{doc_id}` — Get extraction results
- `POST /api/comparison/run` — Run comparison
- `POST /api/review/{comp_id}` — Submit officer review
- `POST /api/generate` — Generate PDF order
- `GET /api/audit` — Get audit trail

### Frontend Pages
1. **Upload Page**: Drag-and-drop PDF upload
2. **Extraction Page**: View extracted tables with confidence scores
3. **Comparison Page**: Side-by-side variance analysis
4. **Review Page**: Officer review interface
5. **Preview Page**: Generated order preview

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: ORM with SQLite database
- **pdfplumber**: PDF table extraction
- **WeasyPrint**: HTML-to-PDF generation
- **Pydantic**: Data validation

### Frontend
- **React 19**: Modern UI framework
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool
- **Tailwind CSS**: Utility-first styling
- **Lucide React**: Beautiful icons

### Infrastructure
- **SQLite**: Zero-config database
- **Docker Compose**: Container orchestration
- **Nginx**: Frontend serving

## 📊 Demo Data

The MVP includes realistic KSERC financial data:
- Power Purchase Cost variations
- Employee Cost differences
- O&M expense fluctuations
- Transmission & Distribution costs
- Sample variance scenarios for testing

## 🔧 Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
# Database
DATABASE_URL=sqlite:///./kserc_dss.db

# AI (Optional)
OPENAI_API_KEY=your_key_here

# Demo Mode
ENVIRONMENT=demo
```

## 📁 Project Structure

```
Decision-Support-System/
├── backend/                    # FastAPI backend
│   ├── app.py                  # Main application
│   ├── api.py                  # REST API routes
│   ├── models.py               # SQLAlchemy models
│   ├── database.py             # SQLite setup
│   ├── extractor.py            # PDF extraction
│   ├── comparison.py           # Variance engine
│   ├── normalizer.py           # Data normalization
│   ├── pdf_generator.py        # KSERC PDF generation
│   ├── schemas.py              # Pydantic schemas
│   ├── seed_data.py            # Demo data
│   └── prompts.py              # AI prompts
├── frontend/                   # Vite + React
│   ├── src/                    # React components
│   ├── package.json            # Dependencies
│   ├── tailwind.config.js      # Tailwind config
│   └── vite.config.ts          # Vite config
├── data/                       # Sample data
├── output/                     # Generated files
├── requirements.txt            # Python dependencies
├── docker-compose.yml          # Docker setup
└── README-MVP.md              # This file
```

## 🎯 MVP Scope

### Included
- ✅ PDF upload and storage
- ✅ Table extraction with confidence scoring
- ✅ Data normalization and variance calculation
- ✅ Officer review workflow
- ✅ KSERC-style PDF generation
- ✅ Audit trail
- ✅ Demo data seeding

### Simplified (vs Full System)
- 🔄 SQLite instead of PostgreSQL + Redis
- 🔄 Demo mode authentication (no JWT)
- 🔄 Direct pdfplumber extraction (no LangGraph)
- 🔄 Docker Compose only (no K8s)
- 🔄 Basic AI integration (optional OpenAI)

## 🚦 Getting Started Guide

1. **Clone the repository**
2. **Run the startup script** (`.\start-mvp.bat` on Windows)
3. **Open browser** to http://localhost:3000
4. **Upload sample PDFs** from the `data/` directory
5. **Review extraction results** and proceed through workflow
6. **Generate draft order** with final decisions

## 📞 Support

For issues or questions:
- Check the API docs at http://localhost:8000/docs
- Review the health endpoint at http://localhost:8000/health
- Check logs in the terminal output

---

**Note**: This is an MVP demonstration. For production deployment, additional security, scaling, and monitoring features would be required.
