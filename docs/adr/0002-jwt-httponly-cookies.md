# ADR-0002: JWT Authentication with HttpOnly Cookies

## Status

Accepted

## Date

2026-01-02

## Context

The application requires secure authentication that:
- Works seamlessly with Next.js SPA frontend
- Protects against XSS token theft
- Supports OAuth providers (Google, GitHub)
- Enables session persistence across browser tabs

Traditional approaches include:
1. JWT in localStorage (vulnerable to XSS)
2. Session cookies (requires sticky sessions for scaling)
3. JWT in HttpOnly cookies (hybrid approach)

## Decision

Implement **JWT tokens stored in HttpOnly cookies** with:
- **Access token**: 30-minute expiry, stored in `access_token` cookie
- **Refresh token**: 7-day expiry, stored in `refresh_token` cookie
- **CSRF protection**: Double-submit cookie pattern
- **Token blacklist**: Database-backed for logout invalidation

### Cookie Configuration

```python
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    secure=True,  # HTTPS only in production
    samesite="lax",
    max_age=1800  # 30 minutes
)
```

## Consequences

### Positive

- XSS attacks cannot access tokens (HttpOnly)
- Automatic token transmission on every request
- Works with standard browser security model
- Refresh token enables seamless re-authentication

### Negative

- Requires CSRF protection (implemented via double-submit cookie)
- Logout requires server-side token blacklisting
- Cross-domain API calls need CORS configuration
- Token refresh adds complexity to frontend

### Neutral

- Cookies are domain-bound (expected behavior)
- Need to handle cookie-blocked browsers gracefully

## Alternatives Considered

### Alternative 1: JWT in localStorage

Rejected because:
- Vulnerable to XSS attacks
- Any injected script can steal tokens
- Not recommended for sensitive applications

### Alternative 2: Session-based Authentication

Rejected because:
- Requires sticky sessions or distributed session store
- Less scalable in multi-worker deployments
- Doesn't align with stateless API design

### Alternative 3: JWT in Memory + Refresh Token Cookie

Considered but rejected because:
- Token lost on page refresh
- Complex state management required
- Poor UX for multi-tab scenarios

## References

- [OWASP Session Management](https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/06-Session_Management_Testing/)
- [JWT Best Practices](https://auth0.com/blog/backend-for-frontend-pattern-with-auth0/)
- [CSRF Double-Submit Cookie](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
