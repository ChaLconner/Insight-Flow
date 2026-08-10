import json
from typing import Any

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


def _normalise_reports(payload: Any) -> list[dict[str, Any]]:  # noqa: PLR0912
    """Accept legacy and Reporting API shapes, then retain scalar fields only."""
    if isinstance(payload, list):
        candidates = payload
    elif isinstance(payload, dict):
        if isinstance(payload.get("csp-report"), dict):
            candidates = [payload["csp-report"]]
        elif isinstance(payload.get("csp_report"), dict):
            candidates = [payload["csp_report"]]
        elif isinstance(payload.get("body"), dict):
            candidates = [payload["body"]]
        else:
            candidates = [payload]
    else:
        return []

    reports: list[dict[str, Any]] = []
    for candidate in candidates[:MAX_CSP_REPORTS]:
        if not isinstance(candidate, dict):
            continue
        normalized: dict[str, Any] = {}
        for key, value in candidate.items():
            if key not in ALLOWED_CSP_FIELDS:
                continue
            if isinstance(value, (str, int, float, bool)):
                normalized[key] = (
                    value if not isinstance(value, str) else value[:MAX_CSP_FIELD_LENGTH]
                )
        if normalized:
            reports.append(normalized)
    return reports


@router.post("/csp-report", status_code=204)
@limiter.limit(RateLimits.CSP_REPORT)
async def report_csp_violation(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
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
        logger.error(f"Error processing CSP report: {e}")
        # Return 204 anyway to not upset the browser
        return None
