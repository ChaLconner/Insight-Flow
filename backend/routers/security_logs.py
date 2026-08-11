import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from rate_limiter import RateLimits, limiter
from services.security_log_service import SecurityLogService
from utils.logger import setup_logger

logger = setup_logger("security_router")
router = APIRouter(prefix="/security", tags=["security"])


MAX_CSP_REPORT_BYTES = 64 * 1024
MAX_CSP_REPORTS = 10
MAX_CSP_FIELD_LENGTH = 2048
ALLOWED_CSP_FIELDS = {
    "blocked-uri",
    "column-number",
    "disposition",
    "document-uri",
    "effective-directive",
    "line-number",
    "original-policy",
    "referrer",
    "source-file",
    "status-code",
    "violated-directive",
    "type",
    "age",
    "url",
    "user_agent",
}


def _get_report_candidates(payload: Any) -> list[Any] | None:
    """Extract report objects from legacy and Reporting API payload shapes."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return None
    for field in ("csp-report", "csp_report", "body"):
        value = payload.get(field)
        if isinstance(value, dict):
            return [value]
    return [payload]


def _normalise_report(candidate: Any) -> dict[str, Any]:
    """Keep allowed scalar CSP fields and cap string lengths."""
    if not isinstance(candidate, dict):
        return {}
    normalized: dict[str, Any] = {}
    for key, value in candidate.items():
        if key not in ALLOWED_CSP_FIELDS:
            continue
        if isinstance(value, (str, int, float, bool)):
            normalized[key] = value[:MAX_CSP_FIELD_LENGTH] if isinstance(value, str) else value
    return normalized


def _normalise_reports(payload: Any) -> list[dict[str, Any]]:
    """Accept legacy and Reporting API shapes, then retain scalar fields only."""
    candidates = _get_report_candidates(payload)
    if candidates is None:
        return []

    return [
        normalized
        for normalized in (
            _normalise_report(candidate) for candidate in candidates[:MAX_CSP_REPORTS]
        )
        if normalized
    ]


@router.post("/csp-report", status_code=204)
@limiter.limit(RateLimits.CSP_REPORT)
async def report_csp_violation(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_async_db)],
):
    """
    Endpoint for browsers to report content security policy violations.
    """
    try:
        raw_body = await request.body()
        if len(raw_body) > MAX_CSP_REPORT_BYTES:
            return None
        try:
            payload = json.loads(raw_body)
        except (TypeError, ValueError):
            return None
        reports = _normalise_reports(payload)
        if not reports:
            return None

        await SecurityLogService.log_event(
            db=db,
            event_type="csp_violation",
            severity="warning",
            details={"reports": reports},
            request=request,
        )
        logger.warning("CSP violation reported: %s", reports[0].get("blocked-uri", "unknown"))

    except Exception as e:
        logger.exception(f"Error processing CSP report: {e}")
        # Return 204 anyway to not upset the browser
        return None
