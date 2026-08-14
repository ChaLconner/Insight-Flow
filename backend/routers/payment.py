"""
Payment router for handling payment-related API endpoints.
Includes rate limiting for security on sensitive operations.
Uses safe error messages to prevent information leakage.
"""

import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import SignatureVerificationError

from database import get_async_db
from dependencies.auth import get_current_active_user
from models import User
from rate_limiter import RateLimits, limiter
from schemas.payment import (
    PLAN_DETAILS,
    PaymentHistoryListResponse,
    PaymentHistoryResponse,
    PaymentHistoryStatsResponse,
    PaymentMethodCreate,
    PaymentMethodListResponse,
    PaymentMethodResponse,
    PlansListResponse,
    SetupIntentResponse,
    SubscriptionCreate,
    SubscriptionResponse,
)
from security.stripe_error_handler import log_and_get_safe_error
from services.payment_service import PaymentService, get_payment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["payment"])
PAYMENT_NOT_CONFIGURED_DETAIL = "Payment service is not configured"


def get_service() -> PaymentService:
    """Get payment service dependency."""
    return get_payment_service()


# ============================================================================
# Plans
# ============================================================================


@router.get("/plans", response_model=PlansListResponse)
async def get_available_plans():
    """
    Get all available subscription plans.
    """
    return PlansListResponse(plans=list(PLAN_DETAILS.values()))


@router.get("/plans/check-downgrade/{target_plan}")
async def check_downgrade_eligibility(
    target_plan: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Check if user can downgrade to a specific plan without exceeding limits.
    Returns current usage vs target plan limits and any warnings.
    """
    from sqlalchemy import distinct, func, or_, select

    from models.project import Project, ProjectMember
    from schemas.payment import SubscriptionPlanEnum

    # Get target plan details
    try:
        target_plan_enum = SubscriptionPlanEnum(target_plan)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid plan: {target_plan}"
        )

    target_plan_info = PLAN_DETAILS.get(target_plan_enum)
    if not target_plan_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    # Get current usage
    # 1. Projects count (owned + member of)
    projects_count = (
        await db.scalar(
            select(func.count(distinct(Project.id)))
            .outerjoin(ProjectMember, Project.id == ProjectMember.project_id)
            .where(
                or_(Project.owner_id == current_user.id, ProjectMember.user_id == current_user.id)
            )
        )
        or 0
    )

    # 2. Total team members across owned projects
    my_projects_subquery = select(Project.id).where(Project.owner_id == current_user.id)
    team_members_count = (
        await db.scalar(
            select(func.count(distinct(ProjectMember.user_id))).where(
                ProjectMember.project_id.in_(my_projects_subquery)
            )
        )
        or 0
    )

    # Ensure at least 1 (owner)
    if team_members_count == 0:
        team_members_count = 1

    # Check limits
    project_limit = target_plan_info.project_limit
    member_limit = target_plan_info.member_limit

    warnings = []
    can_downgrade = True

    # Check project limit
    if project_limit < 9999 and projects_count > project_limit:
        can_downgrade = False
        warnings.append(
            {
                "type": "projects_exceeded",
                "message": f"You have {projects_count} projects, but {target_plan_info.name} plan allows only {project_limit}.",
                "current": projects_count,
                "limit": project_limit,
                "action_required": f"Please delete or archive {projects_count - project_limit} project(s) before downgrading.",
            }
        )

    # Check member limit
    if member_limit < 9999 and team_members_count > member_limit:
        can_downgrade = False
        warnings.append(
            {
                "type": "members_exceeded",
                "message": f"You have {team_members_count} team members, but {target_plan_info.name} plan allows only {member_limit}.",
                "current": team_members_count,
                "limit": member_limit,
                "action_required": f"Please remove {team_members_count - member_limit} team member(s) before downgrading.",
            }
        )

    return {
        "can_downgrade": can_downgrade,
        "target_plan": target_plan,
        "target_plan_name": target_plan_info.name,
        "current_usage": {"projects": projects_count, "team_members": team_members_count},
        "target_limits": {
            "projects": project_limit if project_limit < 9999 else "unlimited",
            "team_members": member_limit if member_limit < 9999 else "unlimited",
        },
        "warnings": warnings,
    }


# ============================================================================
# Setup Intent (for adding payment methods via Stripe Elements)
# ============================================================================


@router.post("/setup-intent", response_model=SetupIntentResponse)
@limiter.limit(RateLimits.PAYMENT_SETUP_INTENT)
async def create_setup_intent(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: PaymentService = Depends(get_service),
):
    """
    Create a Stripe SetupIntent for adding a new payment method.
    Returns a client_secret to use with Stripe Elements on the frontend.
    """
    if not service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PAYMENT_NOT_CONFIGURED_DETAIL,
        )

    try:
        logger.info(f"Creating setup intent for user {current_user.id}")
        result = await service.create_setup_intent(
            db=db,
            user_id=current_user.id,
            email=current_user.email,
            name=current_user.name,
            user=current_user,  # Pass user for cached customer ID
        )
        logger.info("Setup intent created successfully")
        return result
    except Exception as e:
        # Use safe error handler - logs full details internally, returns user-friendly message
        safe_message = log_and_get_safe_error(
            e, operation="create_setup_intent", user_id=str(current_user.id)
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=safe_message)


# ============================================================================
# Payment Methods
# ============================================================================


@router.get("/methods", response_model=PaymentMethodListResponse)
async def list_payment_methods(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: PaymentService = Depends(get_service),
):
    """
    List all payment methods for the current user.
    """
    methods = await service.list_payment_methods(db, current_user.id)
    return PaymentMethodListResponse(
        payment_methods=[PaymentMethodResponse.model_validate(m) for m in methods],
        total=len(methods),
    )


@router.post("/methods", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimits.PAYMENT_ADD_METHOD)
async def add_payment_method(
    request: Request,
    data: PaymentMethodCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: PaymentService = Depends(get_service),
):
    """
    Add a new payment method after SetupIntent confirmation.
    """
    logger.info(f"Adding payment method for user {current_user.id}")

    if not service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PAYMENT_NOT_CONFIGURED_DETAIL,
        )

    try:
        customer_id = await service.get_or_create_stripe_customer(
            db=db,
            user_id=current_user.id,
            email=current_user.email,
            name=current_user.name,
            user=current_user,
        )
        method = await service.attach_payment_method(
            db=db, user_id=current_user.id, data=data, customer_id=customer_id
        )
        logger.info(f"Successfully added payment method {method.id}")
        return PaymentMethodResponse.model_validate(method)
    except Exception as e:
        # Use safe error handler
        safe_message = log_and_get_safe_error(
            e, operation="add_payment_method", user_id=str(current_user.id)
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=safe_message)


@router.put("/methods/{method_id}/default", response_model=PaymentMethodResponse)
async def set_default_payment_method(
    method_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: PaymentService = Depends(get_service),
):
    """
    Set a payment method as the default.
    """
    if not service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PAYMENT_NOT_CONFIGURED_DETAIL,
        )

    method = await service.set_default_payment_method(db, method_id, current_user.id)
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found"
        )

    return PaymentMethodResponse.model_validate(method)


@router.delete("/methods/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(RateLimits.PAYMENT_DELETE)
async def delete_payment_method(
    request: Request,
    method_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: PaymentService = Depends(get_service),
):
    """
    Delete a payment method.
    """
    if not service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PAYMENT_NOT_CONFIGURED_DETAIL,
        )

    try:
        success = await service.delete_payment_method(db, method_id, current_user.id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Payment method not found"
            )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# Payment History
# ============================================================================


@router.get("/history", response_model=PaymentHistoryListResponse)
async def list_payment_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(
        None, alias="status"
    ),  # Filter by status: 'succeeded', 'failed', 'pending', 'refunded'
    start_date: str | None = None,  # Filter by start date (ISO format: YYYY-MM-DD)
    end_date: str | None = None,  # Filter by end date (ISO format: YYYY-MM-DD)
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: PaymentService = Depends(get_service),
):
    """
    List payment history with proper pagination and optional filters.
    Returns paginated payments with total count for frontend pagination.

    Args:
        limit: Max items per page
        offset: Items to skip
        status: Optional filter - 'succeeded', 'failed', 'pending', 'refunded'
        start_date: Optional start date filter (YYYY-MM-DD format)
        end_date: Optional end date filter (YYYY-MM-DD format)
    """
    from datetime import datetime

    # Parse date strings to datetime objects
    parsed_start_date = None
    parsed_end_date = None

    if start_date:
        try:
            parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use YYYY-MM-DD.",
            )

    if end_date:
        try:
            parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use YYYY-MM-DD.",
            )

    history, total = await service.list_payment_history(
        db,
        current_user.id,
        limit,
        offset,
        status_filter=status_filter,
        start_date=parsed_start_date,
        end_date=parsed_end_date,
    )
    return PaymentHistoryListResponse(
        payments=[PaymentHistoryResponse.model_validate(h) for h in history], total=total
    )


@router.get("/history/stats", response_model=PaymentHistoryStatsResponse)
async def get_payment_history_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: PaymentService = Depends(get_service),
):
    """
    Get aggregated payment history statistics.
    Returns total spent, success/fail counts, etc. for dashboard stats.
    This is more efficient than computing from paginated results.
    """
    stats = await service.get_payment_history_stats(db, current_user.id)
    return PaymentHistoryStatsResponse(**stats)


# ============================================================================
# Subscription
# ============================================================================


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: PaymentService = Depends(get_service),
):
    """
    Get the current user's subscription.
    """
    subscription = await service.get_subscription(db, current_user.id)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No subscription found")

    return SubscriptionResponse.model_validate(subscription)


@router.post(
    "/subscription", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit(RateLimits.PAYMENT_SUBSCRIPTION)
async def create_subscription(
    request: Request,
    data: SubscriptionCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: PaymentService = Depends(get_service),
):
    """
    Create or update a subscription.
    """
    if not service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PAYMENT_NOT_CONFIGURED_DETAIL,
        )

    try:
        customer_id = await service.get_or_create_stripe_customer(
            db=db, user_id=current_user.id, email=current_user.email, name=current_user.name
        )

        subscription = await service.create_or_update_subscription(
            db=db, user_id=current_user.id, data=data, customer_id=customer_id
        )
        return SubscriptionResponse.model_validate(subscription)
    except ValueError as e:
        # Validation errors are safe to show
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        # Use safe error handler for Stripe errors
        safe_message = log_and_get_safe_error(
            e, operation="create_subscription", user_id=str(current_user.id)
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=safe_message)


@router.delete("/subscription", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(RateLimits.PAYMENT_SUBSCRIPTION)
async def cancel_subscription(
    request: Request,
    cancel_immediately: bool = False,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: PaymentService = Depends(get_service),
):
    """
    Cancel the current subscription.
    """
    if not service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PAYMENT_NOT_CONFIGURED_DETAIL,
        )

    subscription = await service.cancel_subscription(db, current_user.id, cancel_immediately)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No subscription found")


@router.post("/subscription/resume", response_model=SubscriptionResponse)
@limiter.limit(RateLimits.PAYMENT_SUBSCRIPTION)
async def resume_subscription(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
    service: PaymentService = Depends(get_service),
):
    """
    Resume a canceled subscription (re-enable auto-renew).
    """
    if not service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=PAYMENT_NOT_CONFIGURED_DETAIL,
        )

    try:
        subscription = await service.resume_subscription(db, current_user.id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No subscription found to resume"
            )
        return SubscriptionResponse.model_validate(subscription)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# =============================================================================
# Stripe Webhook IP Allowlist
# Reference: https://docs.stripe.com/ips
# =============================================================================


def get_client_ip(request: Request) -> str:
    """
    Extract real client IP securely, handling proxies with validation.

    Uses the centralized request_security utility for proper trusted proxy handling.
    """
    from utils.request_security import get_client_ip as secure_get_client_ip

    return secure_get_client_ip(request)


def is_ip_in_cidr(ip: str, cidr: str) -> bool:
    """Check if an IP address is within a CIDR range."""
    import ipaddress

    try:
        return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return False


def is_stripe_ip(ip: str) -> bool:
    """Check an optional operator-provided webhook source allowlist."""
    configured_ranges = os.getenv("STRIPE_WEBHOOK_IP_ALLOWLIST", "")
    return any(
        is_ip_in_cidr(ip, cidr.strip()) for cidr in configured_ranges.split(",") if cidr.strip()
    )


@router.post(
    "/webhook",
    include_in_schema=False,
    responses={
        400: {"description": "Invalid webhook request"},
        403: {"description": "Unauthorized webhook source"},
        413: {"description": "Webhook payload too large"},
        503: {"description": "Webhook endpoint is not configured"},
    },
)
@limiter.limit(RateLimits.WEBHOOK)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    service: PaymentService = Depends(get_service),
):
    """
    Handle Stripe webhooks.
    Verifies the Stripe signature and processes events idempotently.

    Security:
    - Stripe signature verification
    - Idempotent event processing
    """
    import stripe

    from config import get_settings

    settings = get_settings()

    # ==========================================================================
    # Optional operator-managed IP allowlist (production only)
    # ==========================================================================
    if settings.is_production and os.getenv("STRIPE_WEBHOOK_IP_ALLOWLIST", "").strip():
        client_ip = get_client_ip(request)
        if not is_stripe_ip(client_ip):
            logger.warning(f"Webhook request from non-allowlisted IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized webhook source",
            )

    # Check if webhook secret is configured
    if not settings.stripe.webhook_secret:
        logger.error("Stripe webhook secret is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook endpoint is not configured",
        )

    max_payload_bytes = 256 * 1024
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > max_payload_bytes:
                raise HTTPException(status_code=413, detail="Webhook payload too large")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid content-length")

    payload = await request.body()
    if len(payload) > max_payload_bytes:
        raise HTTPException(status_code=413, detail="Webhook payload too large")
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe.webhook_secret)
    except ValueError:
        # Invalid payload
        logger.warning("Received webhook with invalid payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except SignatureVerificationError:
        # Invalid signature
        logger.warning("Received webhook with invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    await service.process_webhook(db, event)
    return {"status": "success"}
