from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from services.security_log_service import SecurityLogService
from utils.logger import setup_logger

logger = setup_logger("security_router")
router = APIRouter(prefix="/security", tags=["security"])


class CSPReport(BaseModel):
    """CSP reports sent by browsers are usually strictly structured
    but exact fields can vary slightly by browser version.
    We accept generic dict to be safe and store it."""

    csp_report: dict[str, Any]


@router.post("/csp-report", status_code=204)
async def report_csp_violation(
    report: CSPReport,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Endpoint for browsers to report content security policy violations.
    """
    try:
        # Extract violation details
        violation = report.csp_report

        await SecurityLogService.log_event(
            db=db,
            event_type="csp_violation",
            severity="warning",
            details=violation,
            request=request,
        )
        logger.warning(f"CSP Violation reported: {violation.get('blocked-uri', 'unknown')}")

    except Exception as e:
        logger.error(f"Error processing CSP report: {e}")
        # Return 204 anyway to not upset the browser
        return None
