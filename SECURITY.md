# Enterprise Security Documentation

## ARR Truing-Up Decision Support System — Security Guide

**Version:** 1.0.0  
**Last Updated:** February 21, 2026  
**Classification:** Internal Use Only

---

## Table of Contents

1. [Security Overview](#security-overview)
2. [Authentication & Authorization](#authentication--authorization)
3. [RBAC (Role-Based Access Control)](#rbac-role-based-access-control)
4. [API Security](#api-security)
5. [Data Protection](#data-protection)
6. [Rate Limiting & DDoS Protection](#rate-limiting--ddos-protection)
7. [Security Headers](#security-headers)
8. [Deployment Security](#deployment-security)
9. [Incident Response](#incident-response)
10. [Compliance](#compliance)

---

## Security Overview

The ARR Truing-Up DSS implements enterprise-grade security to protect:
- **Regulatory Data:** Financial data subject to KSERC oversight
- **SBU Partitioning:** Strict isolation between Generation, Transmission, and Distribution
- **Audit Integrity:** Tamper-proof audit trails with cryptographic checksums

### Security Layers

```
┌─────────────────────────────────────────┐
│  Layer 1: Network Security (HTTPS/TLS)  │
├─────────────────────────────────────────┤
│  Layer 2: Rate Limiting & DDoS          │
├─────────────────────────────────────────┤
│  Layer 3: Authentication (JWT + MFA)    │
├─────────────────────────────────────────┤
│  Layer 4: RBAC Authorization            │
├─────────────────────────────────────────┤
│  Layer 5: SBU Data Isolation           │
├─────────────────────────────────────────┤
│  Layer 6: Audit & Logging              │
└─────────────────────────────────────────┘
```

---

## Authentication & Authorization

### JWT Token Structure

Access tokens contain:
```json
{
  "sub": "user@domain.com",
  "role": "regulatory_officer",
  "permissions": ["mapping.confirm", "audit.read"],
  "sbu_access": ["SBU-D", "SBU-G"],
  "exp": 1708454400,
  "type": "access"
}
```

### Token Lifecycle

1. **Login:** Username/password → Access + Refresh tokens
2. **Access:** Bearer token in Authorization header
3. **Refresh:** Refresh token → New access token
4. **Logout:** Client discards tokens (server-side revocation list)

### Password Policy

- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character
- Bcrypt hashing with salt
- MFA supported (TOTP)

---

## RBAC (Role-Based Access Control)

### Role Hierarchy

| Role | Description | Key Permissions |
|------|-------------|---------------|
| **Super Admin** | System administrator | Full access (`*`) |
| **Regulatory Officer** | Final approval authority | `mapping.confirm`, `reports.generate_final`, `data.read_all_sbus` |
| **Senior Auditor** | Review and override | `mapping.override`, `extraction.upload`, `reports.generate_draft` |
| **Data Entry Agent** | Document upload | `extraction.upload`, `mapping.read` |
| **Readonly Analyst** | View reports | `reports.read` |
| **Audit Viewer** | View audit trails | `audit.read` |

### SBU Access Control

Users are assigned to specific SBUs:
- `SBU-G`: Generation data only
- `SBU-T`: Transmission data only  
- `SBU-D`: Distribution data only
- `ALL`: Cross-SBU access (restricted to Regulatory Officers)

Example access check:
```python
if not can_access_sbu(user.sbu_access, target_sbu="SBU-D"):
    raise HTTPException(status_code=403, detail="SBU access denied")
```

---

## API Security

### Protected Endpoints

| Endpoint | Required Permission | Rate Limit |
|----------|-------------------|------------|
| `/auth/login` | None | 5/minute |
| `/extract/upload` | `extraction.upload` | 10/minute |
| `/mapping/confirm` | `mapping.confirm` | 10/minute |
| `/reports/analytical` | `reports.generate_draft` | 50/minute |

### Brute Force Protection

- 5 failed login attempts → 15-minute lockout
- IP-based tracking with X-Forwarded-For support
- Automatic lockout reset after duration

### Request Validation

All requests validated for:
- Content-Type (JSON/multipart)
- Content-Length (max 50MB for uploads)
- Required headers (Authorization for protected routes)

---

## Data Protection

### Encryption at Rest

- **Database:** PostgreSQL with SSL/TLS
- **Sensitive Fields:** AES-256 encryption
- **Files:** Encrypted storage with virus scanning
- **Backups:** Encrypted with separate keys

### Encryption in Transit

- **TLS 1.3** minimum
- **HSTS** enabled (max-age=31536000)
- **Perfect Forward Secrecy** (ECDHE)
- Certificate pinning recommended

### SBU Data Isolation

Every database record includes `sbu_code`:
```sql
-- PostgreSQL Row-Level Security
CREATE POLICY sbu_isolation ON arr_components
    USING (sbu_code = current_setting('app.current_sbu')::SBUType);
```

---

## Rate Limiting & DDoS Protection

### Rate Limit Tiers

| Endpoint Type | Limit | Window |
|--------------|-------|--------|
| Authentication | 5 | 60 seconds |
| Upload | 10 | 60 seconds |
| Sensitive Ops | 10 | 60 seconds |
| API General | 1000 | 60 seconds |
| Default | 100 | 60 seconds |

### Response Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 45
Retry-After: 45
```

### IP Filtering

- Whitelist: Allowed IPs only (if configured)
- Blacklist: Blocked IPs (abuse tracking)
- Geo-blocking: Optional country restrictions

---

## Security Headers

All responses include:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

---

## Deployment Security

### Environment Variables

Required `.env` configuration:
```bash
# Critical: Change in production!
SECRET_KEY=your-256-bit-secret-key-minimum-32-characters

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# Redis (rate limiting)
REDIS_URL=redis://localhost:6379/0

# SSL/TLS
SSL_CERTFILE=/path/to/cert.pem
SSL_KEYFILE=/path/to/key.pem
```

### Production Checklist

- [ ] Change default SECRET_KEY
- [ ] Enable HTTPS/TLS 1.3
- [ ] Configure trusted hosts
- [ ] Set up Redis for rate limiting
- [ ] Enable PostgreSQL SSL
- [ ] Configure Sentry for error tracking
- [ ] Set up log aggregation
- [ ] Enable MFA for admin accounts
- [ ] Configure backup encryption
- [ ] Set up monitoring alerts

### Docker Security

```dockerfile
# Run as non-root user
USER appuser

# Read-only filesystem
read_only: true

# No new privileges
no_new_privileges: true

# Drop all capabilities
cap_drop:
  - ALL
```

---

## Incident Response

### Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| **Critical** | Data breach, system compromise | 15 minutes |
| **High** | Unauthorized access attempt | 1 hour |
| **Medium** | Suspicious activity detected | 4 hours |
| **Low** | Policy violation | 24 hours |

### Response Procedures

1. **Detection:** Automated alerts + manual reporting
2. **Containment:** Isolate affected systems
3. **Investigation:** Preserve logs and evidence
4. **Recovery:** Restore from clean backups
5. **Post-Incident:** Review and update procedures

### Contact

- **Security Team:** security@utility.com
- **24/7 Hotline:** +91-XXX-XXX-XXXX
- **KSERC Liaison:** regulatory@kserc.gov.in

---

## Compliance

### Regulatory Compliance

| Regulation | Status | Notes |
|------------|--------|-------|
| **KSERC Framework** | ✅ Compliant | MYT 2022-27 Order |
| **Data Retention** | ✅ Compliant | 7 years audit trail |
| **GDPR** | ✅ Compliant | Data subject rights |
| **ISO 27001** | 🔄 In Progress | Certification pending |

### Audit Requirements

- All user actions logged with timestamp and IP
- Immutable audit trail (WORM storage)
- Annual penetration testing
- Quarterly access reviews

---

## Security Contacts

**For security issues, contact:**

- Email: security@utility.com
- PGP Key: [Download Public Key]
- Response Time: Within 24 hours

**Responsible Disclosure:**
We appreciate responsible disclosure of vulnerabilities. Please do not publicly disclose issues until we've had a chance to address them.

---

*This document is classified as Internal Use Only. Distribution outside the organization requires written approval.*
