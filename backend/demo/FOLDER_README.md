# Demo Data for ARR Truing-Up DSS

## Contents

- `fixtures/` — Database seed data (JSON)
- `sample_pdfs/` — Sample PDF documents for extraction demo
- `scripts/` — Demo initialization and reset scripts
- `data/` — Sample ARR data and audit records
- `.env.demo` — Demo environment configuration

## Usage

See `DEMO_GUIDE.md` in the project root for complete instructions.

## Quick Start

```bash
# Initialize demo data
python demo/scripts/init_demo.py

# Start backend with demo config
cd backend && uvicorn main_secure:app --reload --env-file ../demo/.env.demo

# Start frontend (in new terminal)
cd frontend && npm start
```

## Demo Credentials

| Username | Password | Role | Access |
|----------|----------|------|--------|
| `regulatory.officer@kserc.gov.in` | `DemoPass123!` | Regulatory Officer | All SBUs |
| `auditor@utility.com` | `DemoPass123!` | Senior Auditor | SBU-D only |
| `data.entry@utility.com` | `DemoPass123!` | Data Entry Agent | SBU-D only |
| `analyst@utility.com` | `DemoPass123!` | Readonly Analyst | All SBUs |

## Demo Scenarios

1. **PDF Upload & Extraction** — Upload `sample_petition.pdf`
2. **Mapping Workbench** — Review 8 pending AI suggestions
3. **Report Generation** — Generate FY 2024-25 analytical report
4. **Variance Analysis** — View controllable/uncontrollable gaps

## Cleanup

To remove all demo data:
```bash
python demo/scripts/cleanup_demo.py
rm -rf demo/
```

**Note:** This folder is completely self-contained and safe to delete after demo.
