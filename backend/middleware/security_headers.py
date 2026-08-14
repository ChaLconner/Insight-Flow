from starlette.datastructures import MutableHeaders

from config import get_settings


class SecurityHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)

                # Security Headers - Standard protection
                headers["X-Frame-Options"] = "DENY"
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-XSS-Protection"] = "1; mode=block"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

                settings = get_settings()

                csp_policy = "default-src 'none'; frame-ancestors 'none'"

                # Add reporting if configured (or default to our own endpoint)
                # The public Next.js rewrite is /api/security/csp-report;
                # operators can override this for direct backend deployments.
                report_uri = settings.security_report_uri or "/api/security/csp-report"
                csp_policy += f"; report-uri {report_uri}; report-to csp-endpoint"

                headers["Content-Security-Policy"] = csp_policy
                report_to_header = f'{{"group":"csp-endpoint","max_age":10886400,"endpoints":[{{"url":"{report_uri}"}}]}}'
                headers["Report-To"] = report_to_header

                # Permissions-Policy - restrict browser features for API
                headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

                # Cross-Origin headers
                # Use unsafe-none to allow OAuth popups to work correctly without COOP isolation issues
                headers["Cross-Origin-Opener-Policy"] = "unsafe-none"
                headers["Cross-Origin-Resource-Policy"] = "same-origin"

                # HSTS (Strict-Transport-Security) - Enable in production.
                # Use the canonical normalized settings predicate so auth,
                # middleware, and transport policy cannot disagree on the
                # environment when operators use values such as Production.
                if settings.is_production:
                    headers["Strict-Transport-Security"] = (
                        "max-age=31536000; includeSubDomains; preload"
                    )

            await send(message)

        await self.app(scope, receive, send_wrapper)
