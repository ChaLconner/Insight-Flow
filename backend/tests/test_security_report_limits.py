"""Focused tests for bounded public telemetry and entitlement fail-closed behavior."""

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from middleware.request_body_limit import RequestBodyLimitMiddleware
from routers.security_logs import _normalise_reports


def test_csp_report_normalization_accepts_browser_shapes_and_scalars_only():
    payload = {"csp-report": {"blocked-uri": "https://example.test", "nested": {"x": "y"}}}

    assert _normalise_reports(payload) == [{"blocked-uri": "https://example.test"}]
    assert _normalise_reports([{"body": "ignored"}, {"type": "csp-violation", "age": 1}]) == [
        {"type": "csp-violation", "age": 1}
    ]


def test_request_body_limit_rejects_before_handler_parsing():
    async def endpoint(request):
        await request.body()
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/limited", endpoint, methods=["POST"])])
    app.add_middleware(RequestBodyLimitMiddleware, limits={"/limited": 64})

    response = TestClient(app).post("/limited", content=b"x" * 65)

    assert response.status_code == 413


def test_csp_report_normalization_caps_fanout_and_field_size():
    payload = [{"blocked-uri": "x" * 10_000} for _ in range(20)]
    reports = _normalise_reports(payload)

    assert len(reports) == 10
    assert len(reports[0]["blocked-uri"]) == 2_048
