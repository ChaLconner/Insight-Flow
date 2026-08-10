"""Small ASGI request-body limits for untrusted endpoints."""

from starlette.responses import JSONResponse


class RequestBodyTooLarge(Exception):
    """Raised when a streamed request exceeds its configured byte limit."""


class RequestBodyLimitMiddleware:
    """Reject selected request bodies before FastAPI buffers/parses them."""

    def __init__(self, app, limits: dict[str, int]):
        self.app = app
        self.limits = limits

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        max_bytes = self.limits.get(scope.get("path", ""))
        if max_bytes is None:
            await self.app(scope, receive, send)
            return

        total = 0

        async def limited_receive():
            nonlocal total
            message = await receive()
            if message["type"] == "http.request":
                total += len(message.get("body", b""))
                if total > max_bytes:
                    raise RequestBodyTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except RequestBodyTooLarge:
            response = JSONResponse(
                {"detail": "Request body too large"},
                status_code=413,
            )
            await response(scope, receive, send)
