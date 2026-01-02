# Security Documentation

This document outlines the security measures implemented in **Insight-Flow**.

## 🔐 Security Overview

Insight-Flow implements industry-standard security practices across all layers of the application stack.

| Category | Status | Details |
|----------|--------|---------|
| Password Hashing | ✅ Excellent | Argon2id (PHC winner) with progressive rehashing |
| JWT Implementation | ✅ Excellent | PyJWT with token blacklist and rotation |
| SQL Injection | ✅ Excellent | SQLAlchemy ORM + escaped LIKE patterns |
| File Upload | ✅ Excellent | Extension + MIME validation, size limits, path traversal protection |
| XSS Protection | ✅ Excellent | HttpOnly cookies, CSP headers, no localStorage tokens |
| CSRF Protection | ✅ Excellent | Double-submit cookie pattern |
| Rate Limiting | ✅ Excellent | Redis-backed (production) with account lockout |
| Security Headers | ✅ Excellent | Full suite including HSTS, CSP, X-Frame-Options |
| IP Security | ✅ Excellent | Trusted proxy validation, IP sanitization |
| Error Handling | ✅ Excellent | No information leakage in production |

---

## 🔒 Authentication Security

### Password Hashing

We use **Argon2id** (the winner of the Password Hashing Competition) with the following parameters:

```python
argon2__time_cost=3
argon2__memory_cost=65536  # 64 MB
argon2__parallelism=4
argon2__hash_len=32
argon2__salt_len=16
```

**Features:**
- Progressive rehashing from bcrypt to argon2
- Have I Been Pwned API integration for breach detection
- Password policy enforcement (entropy, banned patterns, etc.)

### JWT Token Security

- **Library:** PyJWT (avoiding CVE-2024-33663, CVE-2024-33664 in python-jose)
- **Algorithm:** HS256
- **Access Token Expiry:** 30 minutes
- **Refresh Token Expiry:** 30 days
- **Token Blacklist:** Tokens are blacklisted on logout

### Cookie Security

```python
# Production Settings
httponly=True      # Prevents XSS token theft
secure=True        # HTTPS only
samesite="none"    # Required for cross-origin (Vercel → Render)
```

**Important:** Tokens are NEVER stored in localStorage to prevent XSS attacks.

---

## 🛡️ Request Security

### Trusted Proxy Handling

IP addresses are extracted securely from `X-Forwarded-For` headers with:

1. **Trusted proxy validation** - Only accept headers from known proxies
2. **IP sanitization** - Validate IP format, reject malformed input
3. **CIDR matching** - Support for cloud provider IP ranges

Configure via environment variables:
```env
TRUSTED_PROXIES=10.0.0.0/8,172.16.0.0/12
CLOUD_PROVIDER=render  # or: vercel, cloudflare
```

### Rate Limiting

| Endpoint Type | Limit |
|---------------|-------|
| Login | 5 requests/minute (per IP) |
| Registration | 5 requests/minute |
| Password Reset | 3 requests/minute |
| Payment Operations | 5-10 requests/minute |
| General API | 200 requests/minute |

**Account Lockout:** 5 failed login attempts → 15 minute lockout

---

## 📁 File Upload Security

All file uploads are validated with:

1. **Extension Whitelist**
   - Images: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`
   - Documents: `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.ppt`, `.pptx`, `.txt`, `.csv`, `.md`

2. **MIME Type Validation**
   - Content-Type must match file extension
   - Prevents disguising malicious files

3. **Size Limits**
   - General files: 10 MB
   - Avatars: 5 MB

4. **Path Traversal Protection**
   - All paths normalized and validated
   - UUID-based filenames prevent collisions

---

## 🌐 Security Headers

```http
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'none'; frame-ancestors 'none'
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Cross-Origin-Opener-Policy: unsafe-none
Cross-Origin-Resource-Policy: same-origin
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload  # Production only
```

---

## 🚫 CSRF Protection

**Method:** Double-submit cookie pattern

1. CSRF token set as a readable cookie (not HttpOnly)
2. Client sends token in `X-CSRF-Token` header
3. Server validates header matches cookie (constant-time comparison)

**Exempt Paths:** Authentication endpoints (login, register, OAuth)

---

## ⚠️ Error Handling

**Development Mode:**
- Full error details returned for debugging
- Stack traces in logs

**Production Mode:**
- Generic error messages to users
- No internal details exposed
- Error ID provided for support correlation
- Full details logged internally

```json
{
  "success": false,
  "message": "An unexpected error occurred. Please try again later.",
  "error_id": "a1b2c3d4"
}
```

---

## 🔐 Secrets Management

### Required Environment Variables

```env
# Critical (required)
SECRET_KEY=<min 32 characters>
DATABASE_URL=postgresql+asyncpg://...

# Authentication
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

# Production
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend.com

# Optional (recommended)
REDIS_URL=redis://...
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
```

### Secret Key Requirements

- Minimum 32 characters
- Generated with cryptographically secure random
- Example: `openssl rand -hex 32`

---

## 🔍 Security Audit Log

All security-relevant events are logged:

- Authentication attempts (success/failure)
- Account lockouts
- Password changes
- File upload violations
- Suspicious activity detection
- Payment operations

Log location: `logs/security_audit.log`

---

## 📋 Security Checklist for Deployment

- [ ] `SECRET_KEY` is set and secure (32+ characters)
- [ ] `ENVIRONMENT=production` is set
- [ ] `CORS_ORIGINS` contains only trusted domains
- [ ] `COOKIE_SECURE=True` (HTTPS)
- [ ] Redis is configured for rate limiting
- [ ] Database connection uses SSL
- [ ] Stripe webhook secret is configured
- [ ] HSTS preload is enabled
- [ ] Logs are configured (no sensitive data)
- [ ] Error messages are generic

---

## 🐛 Reporting Security Issues

If you discover a security vulnerability, please:

1. **Do NOT** create a public GitHub issue
2. Email: security@insight-flow.com
3. Include: Description, reproduction steps, potential impact

We aim to respond within 48 hours and will credit you in your security acknowledgments.
