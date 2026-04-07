# Security Architecture

*Enterprise-Grade Security for Regulatory Decision Systems*

**Version:** 3.1.0 | **Updated:** April 6, 2026  
*Now with Demo Mode security considerations*

---

## Overview

The KSERC Truing-Up Decision Support System implements defense-in-depth security principles to protect sensitive regulatory data, ensure audit integrity, and maintain compliance with government IT standards. The system features dual-mode operation with distinct security profiles for production and demo environments.

---

## 🎭 Demo Mode Security Architecture

### Security Isolation

The system maintains strict security separation between demo and production modes:

| Security Aspect | Demo Mode | Production Mode |
|-----------------|-----------|------------------|
| **Authentication** | Auto-login as Demo Admin | Full JWT authentication required |
| **Authorization** | All permissions bypassed | Strict RBAC enforced |
| **Data Source** | Pre-seeded demo data only | Real regulatory data |
| **Audit Trail** | Marked `[DEMO MODE]` | Production audit logs |
| **Network Security** | Same controls as production | Full security controls |

### Demo Mode Safety Features

```python
# Demo mode security checks
if is_demo_mode():
    # Auto-login with demo user
    # Bypass permission checks
    # Use demo data only
    # Mark all audit entries
```

### Security Guarantees

- ✅ **No Production Data Exposure** - Demo mode cannot access production database
- ✅ **No Authentication Bypass in Production** - Demo auto-login only active when `DEMO_MODE=true`
- ✅ **Clear Demo Indicators** - All demo outputs watermarked and marked
- ✅ **Environment Isolation** - Requires explicit configuration change to switch modes

---

## Authentication & Authorization

### JWT-Based Authentication

The system utilizes JSON Web Tokens (JWT) for stateless, scalable authentication:

- **Token Format**: Bearer tokens with HS256 algorithm
- **Token Lifetime**: 30 minutes (configurable)
- **Refresh Mechanism**: Sliding window with 7-day refresh tokens
- **Storage**: Client-side httpOnly cookies (XSS protection)

```python
# Token Structure
{
  "sub": "officer@kserc.gov.in",
  "role": "regulatory_officer",
  "permissions": ["decisions.read", "decisions.write"],
  "iat": 1712345678,
  "exp": 1712347478
}
```

### Role-Based Access Control (RBAC)

| Role | Permissions | Typical User |
|------|-------------|--------------|
| `super_admin` | Full system access | IT Administrator |
| `regulatory_officer` | decisions.read, decisions.write, orders.generate | Commission Officers |
| `senior_auditor` | mapping.confirm, decisions.read | Audit Team Lead |
| `data_entry_agent` | extraction.upload, mapping.read | Utility Data Entry |
| `readonly_analyst` | All read operations | External Consultants |

### Password Security

- **Hashing Algorithm**: bcrypt with 12 rounds
- **Password Policy**:
  - Minimum 12 characters
  - At least one uppercase, lowercase, digit, special character
  - No dictionary words
  - 90-day rotation recommended

---

## Data Protection

### Database Security

- **Encryption at Rest**: AES-256 for PostgreSQL data files
- **Encryption in Transit**: TLS 1.3 for all connections
- **Connection Pooling**: PgBouncer with prepared statement caching
- **Backup Encryption**: GPG-encrypted daily snapshots

### Document Security

- **PDF Processing**: All processing happens in-memory; no persistent storage
- **Checksum Verification**: SHA-256 for document integrity
- **Watermarking**: Draft orders marked with "DRAFT — DO NOT PUBLISH"
- **Access Logs**: Every document access logged with officer ID and timestamp

### Sensitive Data Handling

| Data Type | Protection Method | Retention |
|-----------|-------------------|-----------|
| Officer passwords | bcrypt hashing | N/A |
| Justification texts | Encrypted at rest | 7 years |
| Audit logs | Append-only, checksummed | 10 years |
| Financial figures | Encrypted, versioned | 7 years |
| IP addresses | Anonymized after 90 days | 90 days |

---

## Audit & Compliance

### Immutable Audit Trail

Every action is recorded in the `OverrideAuditLog` table:

```python
{
  "action_type": "OVERRIDE",  # OVERRIDE, EDIT, GENERATE
  "entity_type": "AIDecision",
  "entity_id": 12345,
  "officer_name": "officer@kserc.gov.in",
  "field_changed": "decision",
  "old_value": "APPROVE",
  "new_value": "PARTIAL",
  "change_reason": "Detailed justification text...",
  "ip_address": "192.168.1.100",
  "session_id": "sess_abc123",
  "checksum": "sha256_hash_for_integrity",
  "created_at": "2024-03-31T14:30:00Z"
}
```

### Audit Log Features

- **Append-Only**: No deletes or updates permitted
- **Cryptographic Integrity**: Each entry hashed with SHA-256
- **Chain Verification**: Each entry references previous entry hash
- **Export**: Tamper-evident PDF exports for compliance reviews

### Compliance Standards

| Standard | Implementation |
|----------|----------------|
| **Electricity Act 2003** | Regulatory clauses embedded in code |
| **KSERC IT Security Policy** | JWT, bcrypt, RBAC compliance |
| **Indian IT Act 2000** | Data protection, audit logs |
| **ISO 27001** | Access control, encryption, monitoring |

---

## Network Security

### API Security

- **Rate Limiting**: 100 requests/minute per IP, 1000 per user
- **CORS**: Whitelist-based origin validation
- **Security Headers**:
  ```
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  X-XSS-Protection: 1; mode=block
  Strict-Transport-Security: max-age=31536000
  Content-Security-Policy: default-src 'self'
  ```

- **Input Validation**: Pydantic models with strict type checking
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries

### Zero-Trust Architecture

1. **Never Trust, Always Verify**: Every request authenticated and authorized
2. **Least Privilege**: Users have minimum necessary permissions
3. **Micro-segmentation**: Backend services isolated by function
4. **Continuous Monitoring**: All access logged and analyzed

---

## LLM Security (Optional Feature)

### Zero-Trust LLM Integration

**Core Principle**: No data leaves your server for core functionality.

| Component | Local/Offline | External API |
|-----------|-------------|--------------|
| PDF Text Extraction | ✅ PyPDF2 | ❌ |
| Table Parsing | ✅ Python regex | ❌ |
| Decision Classification | ✅ Rule engine | ❌ |
| Variance Calculation | ✅ Python arithmetic | ❌ |
| Document Generation | ✅ HTML templates | ❌ |
| Executive Summary | ✅ Pre-coded | ⚠️ Optional OpenAI |

### LLM Data Handling (If Enabled)

If `OPENAI_API_KEY` is configured:
- **Data Sent**: Only final, verified comparison results (no raw PDF content)
- **Purpose**: 3-paragraph executive summary only
- **No Training**: Data not used for model training per OpenAI Enterprise terms
- **Opt-In**: System works 100% without API key

---

## Incident Response

### Security Event Classification

| Severity | Examples | Response Time |
|----------|----------|---------------|
| **Critical** | Unauthorized admin access, data breach | Immediate |
| **High** | Failed login attempts, suspicious API calls | 1 hour |
| **Medium** | Permission violations, anomalous patterns | 4 hours |
| **Low** | Minor policy violations | 24 hours |

### Response Procedures

1. **Detection**: Automated alerts via email/SMS
2. **Containment**: Immediate account lockout, IP blocking
3. **Investigation**: Audit log analysis, forensic data collection
4. **Recovery**: Password resets, token revocation
5. **Documentation**: Incident report with timeline and remediation

---

## Deployment Security

### Production Checklist

- [ ] Change default `admin` credentials
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure PostgreSQL SSL connections
- [ ] Set up firewall rules (allow only 80, 443, 22)
- [ ] Disable debug mode (`DEBUG=false`)
- [ ] Rotate JWT secret key
- [ ] Enable audit log shipping to SIEM
- [ ] Configure automated backups
- [ ] Set up log aggregation (ELK/Loki)
- [ ] Enable intrusion detection (Fail2ban)

### Docker Security

```dockerfile
# Non-root user
USER 1000:1000

# Read-only filesystem
read_only: true

# No new privileges
no_new_privileges: true

# Resource limits
mem_limit: 2g
cpus: 2
```

---

## Security Testing

### Automated Security Checks

```bash
# Dependency vulnerability scan
pip-audit --requirement requirements.txt

# Static code analysis
bandit -r backend/

# Secret detection
git-secrets --scan

# Container scanning
trivy image kserc-dss:latest
```

### Penetration Testing

- **Frequency**: Annual third-party assessment
- **Scope**: Web application, APIs, infrastructure
- **Deliverables**: Vulnerability report, remediation plan

---

## Contact & Reporting

**Security Team**
- Email: security@kserc-dss.gov.in
- Phone: +91-XXX-XXXXXXXX (24/7 hotline)

**Report a Vulnerability**
Please email security@kserc-dss.gov.in with:
- Description of vulnerability
- Steps to reproduce
- Potential impact assessment
- Suggested remediation (if any)

We follow responsible disclosure and aim to respond within 48 hours.

---

<div align="center">

**Security is not a feature — it's a foundation.**

</div>
