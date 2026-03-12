# Security Architecture

## Authentication & RBAC
The system utilizes enterprise-grade JWT (JSON Web Token) authentication to protect dashboard views and APIs.

- **Storage:** Passwords are hashed strictly using `bcrypt` via the `passlib` context. Plaintext passwords never exist in memory post-login.
- **Authorization:** `SecurityManager.decode_token` validates the Bearer token for every protected endpoint.
- **Default Super Admin:** The system currently initiates an in-memory test user: `admin` / `Admin@12345678`. *In production, this must be replaced with Postgres-backed Identity Management.*

## Data Privacy & LLM Opt-in
This system is inherently designed for high-security environments handling strictly confidential purchase orders and reference specifications.

**Rule-Based Isolation (Zero-Trust LLMs):**
- By default, **no data ever leaves your server.**
- The core comparison is executed via `difflib`, numeric tolerance calculation, and `PyPDF2` entirely on local CPU cycles.
- The LLM integration (`_generate_llm_report`) acts exclusively as an opt-in summary generator. If `OPENAI_API_KEY` is not provided in the environment variables, the system guarantees 100% total data privacy.
