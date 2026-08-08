"""
Payment service for Stripe integration.
Handles payment methods, subscriptions, and payment history.

Features:
- Async Stripe API calls using run_in_executor
- Idempotency keys to prevent duplicate charges
- Payment locks to prevent race conditions
- Safe error messages for users
"""

import asyncio
import contextlib
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import stripe
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from stripe import InvalidRequestError, StripeError

from config import get_settings
from models.payment import (
    PaymentHistory,
    PaymentMethod,
    PaymentStatus,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from schemas.payment import (
    PLAN_DETAILS,
    PaymentMethodCreate,
    SetupIntentResponse,
    SubscriptionCreate,
    SubscriptionPlanEnum,
)
from security.payment_operations import (
    generate_setup_intent_key,
    generate_subscription_key,
    payment_lock,
)
from security.payment_security import security_logger

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Service for handling Stripe payment operations.
    """

    def __init__(self):
        settings = get_settings()
        if settings.stripe.is_configured:
            stripe.api_key = settings.stripe.secret_key
            self._configured = True
        else:
            self._configured = False
            logger.warning("Stripe is not configured. Payment features will be disabled.")

    @property
    def is_configured(self) -> bool:
        return self._configured

    def _check_configured(self):
        """Raise an error if Stripe is not configured."""
        if not self._configured:
            raise ValueError(
                "Stripe is not configured. Please set STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY."
            )

    async def _run_stripe_cmd(
        self, func, *args, idempotency_key: str | None = None, **kwargs
    ) -> Any:
        """
        Run a blocking Stripe command in a separate thread.

        Args:
            func: Stripe SDK function to call
            *args: Positional arguments for the function
            idempotency_key: Optional idempotency key for safe retries
            **kwargs: Keyword arguments for the function

        Returns:
            Result from Stripe API
        """
        if idempotency_key:
            kwargs["idempotency_key"] = idempotency_key

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    # =========================================================================
    # Customer Management
    # =========================================================================

    async def get_or_create_stripe_customer(  # noqa: PLR0912, PLR0915
        self,
        db: AsyncSession,
        user_id: UUID,
        email: str,
        name: str | None = None,
        user: Any | None = None,  # Optional user object for cached customer ID
    ) -> str:
        """
        Get existing Stripe customer ID or create a new one.
        Optimized: First checks cached stripe_customer_id on User model.
        Also verifies the customer still exists in Stripe.
        """
        self._check_configured()

        existing_customer_id = None

        # OPTIMIZATION: First check cached customer ID on the User object if provided
        if user and hasattr(user, "stripe_customer_id") and user.stripe_customer_id:
            existing_customer_id = user.stripe_customer_id

        # Fallback: Check user directly from DB if not provided
        if not existing_customer_id:
            from models import User

            result = await db.execute(select(User).where(User.id == user_id))
            db_user = result.scalar_one_or_none()
            if db_user and hasattr(db_user, "stripe_customer_id") and db_user.stripe_customer_id:
                existing_customer_id = db_user.stripe_customer_id
                user = db_user  # Keep reference for update later

        # Fallback: Check if user already has a subscription with customer ID
        if not existing_customer_id:
            result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
            subscription = result.scalar_one_or_none()

            if subscription and subscription.stripe_customer_id:
                existing_customer_id = subscription.stripe_customer_id

        # Fallback: Check payment methods for existing customer ID
        if not existing_customer_id:
            result = await db.execute(
                select(PaymentMethod).where(PaymentMethod.user_id == user_id).limit(1)
            )
            payment_method = result.scalar_one_or_none()

            if payment_method and payment_method.stripe_customer_id:
                existing_customer_id = payment_method.stripe_customer_id

        # Verify existing customer still exists in Stripe
        if existing_customer_id:
            try:
                await self._run_stripe_cmd(stripe.Customer.retrieve, existing_customer_id)
                # Customer exists, cache it on User if not already cached
                if user and hasattr(user, "stripe_customer_id") and not user.stripe_customer_id:
                    from models import User

                    await db.execute(
                        update(User)
                        .where(User.id == user_id)
                        .values(stripe_customer_id=existing_customer_id)
                    )
                    await db.commit()
                return existing_customer_id
            except InvalidRequestError as e:
                # If checking "No such customer", we must clear it from DB to avoid infinite loops
                is_no_such_customer = "No such customer" in str(e) or "resource_missing" in str(e)

                if is_no_such_customer:
                    logger.warning(
                        f"Customer {existing_customer_id} not found in Stripe, creating new one"
                    )

                    # 1. Clear from User
                    from models import User

                    await db.execute(
                        update(User).where(User.id == user_id).values(stripe_customer_id=None)
                    )

                    # 2. Clear from Subscriptions (nullable)
                    await db.execute(
                        update(Subscription)
                        .where(Subscription.user_id == user_id)
                        .values(stripe_customer_id=None, stripe_subscription_id=None)
                    )

                    # 3. Delete PaymentMethods with stale customer (stripe_customer_id is NOT NULL)
                    await db.execute(delete(PaymentMethod).where(PaymentMethod.user_id == user_id))

                    await db.commit()
                    logger.info(f"Cleared stale customer data for user {user_id}")
                else:
                    raise

        # Fallback: Search Stripe by email to avoid duplicates
        if not existing_customer_id:
            try:
                search_result = await self._run_stripe_cmd(
                    stripe.Customer.list, email=email, limit=1
                )
                if search_result and search_result.data:
                    existing_customer_id = search_result.data[0].id
                    logger.info(
                        f"Found existing Stripe customer {existing_customer_id} by email {email}"
                    )

                    # Update User with found ID
                    if user_id:
                        from models import User

                        await db.execute(
                            update(User)
                            .where(User.id == user_id)
                            .values(stripe_customer_id=existing_customer_id)
                        )
                        await db.commit()
                    return str(existing_customer_id)
            except Exception as e:
                logger.warning(f"Error searching Stripe customer by email: {e}")

        # Create new Stripe customer
        customer = await self._run_stripe_cmd(
            stripe.Customer.create, email=email, name=name, metadata={"user_id": str(user_id)}
        )

        # Cache the new customer ID on User model
        from models import User

        await db.execute(
            update(User).where(User.id == user_id).values(stripe_customer_id=customer.id)
        )
        await db.commit()

        logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
        return str(customer.id)

    # =========================================================================
    # Setup Intent (for adding payment methods)
    # =========================================================================

    async def create_setup_intent(
        self,
        db: AsyncSession,
        user_id: UUID,
        email: str,
        name: str | None = None,
        user: Any | None = None,  # Optional user object for cached customer ID
    ) -> SetupIntentResponse:
        """
        Create a Stripe SetupIntent for adding a new payment method.
        Optimized: Uses cached customer ID if available.
        Includes retry logic for stale customer IDs.
        """
        self._check_configured()

        customer_id = await self.get_or_create_stripe_customer(db, user_id, email, name, user)

        try:
            # Generate idempotency key to prevent duplicates on retry
            idem_key = generate_setup_intent_key(user_id)

            setup_intent = await self._run_stripe_cmd(
                stripe.SetupIntent.create,
                customer=customer_id,
                payment_method_types=["card"],
                metadata={"user_id": str(user_id)},
                idempotency_key=idem_key,
            )
        except InvalidRequestError as e:
            # Handle stale customer ID - clear and retry
            if "No such customer" in str(e) or "resource_missing" in str(e):
                logger.warning(
                    f"Customer {customer_id} not found in Stripe during SetupIntent creation, clearing and retrying"
                )

                # Clear stale customer IDs from Subscription (nullable)
                await db.execute(
                    update(Subscription)
                    .where(Subscription.user_id == user_id)
                    .values(stripe_customer_id=None, stripe_subscription_id=None)
                )

                # Delete payment methods with stale customer ID (stripe_customer_id is NOT NULL)
                # CRITICAL FIX: Only delete methods with THIS specific invalid customer_id
                # Do NOT delete all user's payment methods, as they might have just added a new valid one!
                await db.execute(
                    delete(PaymentMethod)
                    .where(PaymentMethod.user_id == user_id)
                    .where(PaymentMethod.stripe_customer_id == customer_id)
                )
                await db.commit()
                logger.info(f"Cleared stale customer data for user {user_id}")

                # Create new customer
                new_customer = await self._run_stripe_cmd(
                    stripe.Customer.create,
                    email=email,
                    name=name,
                    metadata={"user_id": str(user_id)},
                )
                customer_id = new_customer.id
                logger.info(f"Created new Stripe customer {customer_id} for user {user_id}")

                # CRITICAL: Save the new customer ID to the User table immediately!
                from models import User

                await db.execute(
                    update(User).where(User.id == user_id).values(stripe_customer_id=customer_id)
                )
                await db.commit()
                logger.info(f"Updated User {user_id} with new customer ID {customer_id}")

                # Retry SetupIntent creation with new customer
                setup_intent = await self._run_stripe_cmd(
                    stripe.SetupIntent.create,
                    customer=customer_id,
                    payment_method_types=["card"],
                    metadata={"user_id": str(user_id)},
                )
            else:
                raise

        return SetupIntentResponse(
            client_secret=setup_intent.client_secret, customer_id=customer_id
        )

    # =========================================================================
    # Payment Method Management
    # =========================================================================

    async def attach_payment_method(
        self, db: AsyncSession, user_id: UUID, data: PaymentMethodCreate, customer_id: str
    ) -> PaymentMethod:
        """
        Attach a payment method to a user after SetupIntent confirmation.
        """
        self._check_configured()

        # Get payment method details from Stripe
        pm = await self._run_stripe_cmd(stripe.PaymentMethod.retrieve, data.payment_method_id)

        if pm.customer and str(pm.customer) != customer_id:
            raise ValueError("Payment method does not belong to current customer")

        # Attach to customer if not already attached
        if not pm.customer:
            await self._run_stripe_cmd(
                stripe.PaymentMethod.attach, data.payment_method_id, customer=customer_id
            )

        # If setting as default, unset other defaults
        if data.set_as_default:
            await db.execute(
                update(PaymentMethod)
                .where(PaymentMethod.user_id == user_id)
                .values(is_default=False)
            )

            # Set as default in Stripe
            await self._run_stripe_cmd(
                stripe.Customer.modify,
                customer_id,
                invoice_settings={"default_payment_method": data.payment_method_id},
            )

        # Extract billing address from request
        billing_address: dict[str, Any] = {}
        if data.billing_address:
            if hasattr(data.billing_address, "model_dump"):
                billing_address = data.billing_address.model_dump() or {}
            else:
                billing_address = {}

        # Create payment method record with all available info
        payment_method = PaymentMethod(
            user_id=user_id,
            stripe_payment_method_id=data.payment_method_id,
            stripe_customer_id=customer_id,
            # Card details from Stripe
            card_brand=pm.card.brand,
            card_last4=pm.card.last4,
            card_exp_month=pm.card.exp_month,
            card_exp_year=pm.card.exp_year,
            card_funding=pm.card.funding,
            card_country=pm.card.country,  # Card issuer country
            card_fingerprint=pm.card.fingerprint,  # For duplicate detection
            is_default=data.set_as_default,
            is_active=True,  # Explicitly set to active
            billing_name=data.billing_name
            or (pm.billing_details.name if pm.billing_details else None),
            billing_email=data.billing_email
            or (pm.billing_details.email if pm.billing_details else None),
            billing_phone=data.billing_phone
            or (pm.billing_details.phone if pm.billing_details else None),
            # Billing address - prefer user input, fallback to Stripe data
            billing_address_line1=billing_address.get("line1")
            or (
                pm.billing_details.address.line1
                if pm.billing_details and pm.billing_details.address
                else None
            ),
            billing_address_line2=billing_address.get("line2")
            or (
                pm.billing_details.address.line2
                if pm.billing_details and pm.billing_details.address
                else None
            ),
            billing_city=billing_address.get("city")
            or (
                pm.billing_details.address.city
                if pm.billing_details and pm.billing_details.address
                else None
            ),
            billing_state=billing_address.get("state")
            or (
                pm.billing_details.address.state
                if pm.billing_details and pm.billing_details.address
                else None
            ),
            billing_postal_code=billing_address.get("postal_code")
            or (
                pm.billing_details.address.postal_code
                if pm.billing_details and pm.billing_details.address
                else None
            ),
            billing_country=billing_address.get("country")
            or (
                pm.billing_details.address.country
                if pm.billing_details and pm.billing_details.address
                else None
            ),
        )

        db.add(payment_method)

        # Also update User's stripe_customer_id to ensure consistency
        from models import User

        await db.execute(
            update(User).where(User.id == user_id).values(stripe_customer_id=customer_id)
        )

        try:
            await db.commit()
        except Exception as e:
            logger.error(f"COMMIT FAILED: {e}")
            security_logger.log_payment_operation(
                operation="add_payment_method",
                user_id=user_id,
                success=False,
                details={"error": str(e), "card_brand": pm.card.brand, "last4": pm.card.last4},
            )
            raise

        await db.refresh(payment_method)

        # Log successful payment method addition
        security_logger.log_payment_operation(
            operation="add_payment_method",
            user_id=user_id,
            success=True,
            details={
                "payment_method_id": str(payment_method.id),
                "card_brand": pm.card.brand,
                "last4": pm.card.last4,
                "is_default": data.set_as_default,
            },
        )

        return payment_method

    async def list_payment_methods(self, db: AsyncSession, user_id: UUID) -> list[PaymentMethod]:
        """
        List all payment methods for a user.
        """
        result = await db.execute(
            select(PaymentMethod)
            .where(PaymentMethod.user_id == user_id)
            .where(PaymentMethod.is_active == True)
            .order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_payment_method(
        self, db: AsyncSession, payment_method_id: UUID, user_id: UUID
    ) -> PaymentMethod | None:
        """
        Get a specific payment method.
        """
        result = await db.execute(
            select(PaymentMethod)
            .where(PaymentMethod.id == payment_method_id)
            .where(PaymentMethod.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def set_default_payment_method(
        self, db: AsyncSession, payment_method_id: UUID, user_id: UUID
    ) -> PaymentMethod | None:
        """
        Set a payment method as default.
        """
        self._check_configured()

        payment_method = await self.get_payment_method(db, payment_method_id, user_id)
        if not payment_method:
            return None

        # Unset all other defaults
        await db.execute(
            update(PaymentMethod).where(PaymentMethod.user_id == user_id).values(is_default=False)
        )

        # Set this one as default
        payment_method.is_default = True

        # Update in Stripe (Customer Default)
        await self._run_stripe_cmd(
            stripe.Customer.modify,
            payment_method.stripe_customer_id,
            invoice_settings={"default_payment_method": payment_method.stripe_payment_method_id},
        )

        # CRITICAL: Also update any active subscription to use this new default method
        # Otherwise, the subscription keeps using the old card until the next cycle failure
        active_sub = await self.get_subscription(db, user_id)
        if (
            active_sub
            and active_sub.stripe_subscription_id
            and active_sub.status
            in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING, SubscriptionStatus.PAST_DUE]
        ):
            try:
                await self._run_stripe_cmd(
                    stripe.Subscription.modify,
                    active_sub.stripe_subscription_id,
                    default_payment_method=payment_method.stripe_payment_method_id,
                )

                # Update local reference
                active_sub.default_payment_method_id = payment_method.id  # type: ignore
                db.add(active_sub)
                logger.info(
                    f"Updated subscription {active_sub.id} to use new default payment method {payment_method.id}"
                )
            except Exception as e:
                logger.error(f"Failed to update subscription default payment method: {e}")
                # Don't fail the whole request, just log it. The customer default is already set.

        await db.commit()
        await db.refresh(payment_method)

        return payment_method

    async def list_payment_history(
        self,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        status_filter: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> tuple[list[PaymentHistory], int]:
        """
        List payment history for a user with proper pagination.
        Returns a tuple of (items, total_count).

        Args:
            db: Database session
            user_id: User to get history for
            limit: Max items per page
            offset: Items to skip
            status_filter: Optional status filter ('succeeded', 'failed', 'pending', 'refunded')
            start_date: Optional start date for filtering (inclusive)
            end_date: Optional end date for filtering (inclusive)
        """
        from sqlalchemy import func

        # Build base query
        base_query = select(PaymentHistory).where(PaymentHistory.user_id == user_id)
        count_query = select(func.count(PaymentHistory.id)).where(PaymentHistory.user_id == user_id)

        # Apply status filter if provided
        if status_filter:
            try:
                status_enum = PaymentStatus(status_filter)
                base_query = base_query.where(PaymentHistory.status == status_enum)
                count_query = count_query.where(PaymentHistory.status == status_enum)
            except ValueError:
                # Invalid status, ignore filter
                logger.warning(f"Invalid status filter: {status_filter}")

        # Apply date range filter if provided
        if start_date:
            base_query = base_query.where(PaymentHistory.created_at >= start_date)
            count_query = count_query.where(PaymentHistory.created_at >= start_date)

        if end_date:
            # Add 1 day to end_date to include the entire day
            from datetime import timedelta

            end_date_inclusive = end_date + timedelta(days=1)
            base_query = base_query.where(PaymentHistory.created_at < end_date_inclusive)
            count_query = count_query.where(PaymentHistory.created_at < end_date_inclusive)

        # Get total count
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated items
        result = await db.execute(
            base_query.order_by(PaymentHistory.created_at.desc()).offset(offset).limit(limit)
        )
        items = list(result.scalars().all())

        return items, total

    async def get_payment_history_stats(self, db: AsyncSession, user_id: UUID) -> dict:
        """
        Get aggregated payment history statistics for a user.
        Uses SQL aggregation for efficiency.
        """
        from decimal import Decimal

        from sqlalchemy import String, case, cast, func

        from models.payment import PaymentStatus

        # Aggregate query for stats
        # Use explicit casting and .value comparisons for robust Enum handling
        result = await db.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                cast(PaymentHistory.status, String)
                                == PaymentStatus.SUCCEEDED.value,
                                PaymentHistory.amount,
                            ),
                            else_=Decimal(0),
                        )
                    ),
                    Decimal(0),
                ).label("total_spent"),
                func.count(PaymentHistory.id).label("total_payments"),
                func.sum(
                    case(
                        (cast(PaymentHistory.status, String) == PaymentStatus.SUCCEEDED.value, 1),
                        else_=0,
                    )
                ).label("successful_payments"),
                func.sum(
                    case(
                        (cast(PaymentHistory.status, String) == PaymentStatus.FAILED.value, 1),
                        else_=0,
                    )
                ).label("failed_payments"),
                func.sum(
                    case(
                        (cast(PaymentHistory.status, String) == PaymentStatus.PENDING.value, 1),
                        else_=0,
                    )
                ).label("pending_payments"),
                func.sum(
                    case(
                        (cast(PaymentHistory.status, String) == PaymentStatus.REFUNDED.value, 1),
                        else_=0,
                    )
                ).label("refunded_payments"),
            ).where(PaymentHistory.user_id == user_id)
        )

        row = result.fetchone()

        if not row:
            return {
                "total_spent": 0.0,
                "total_payments": 0,
                "successful_payments": 0,
                "failed_payments": 0,
                "pending_payments": 0,
                "refunded_payments": 0,
                "currency": "usd",
            }

        return {
            "total_spent": float(row.total_spent or 0),
            "total_payments": int(row.total_payments or 0),
            "successful_payments": int(row.successful_payments or 0),
            "failed_payments": int(row.failed_payments or 0),
            "pending_payments": int(row.pending_payments or 0),
            "refunded_payments": int(row.refunded_payments or 0),
            "currency": "usd",
        }

    async def delete_payment_method(
        self, db: AsyncSession, payment_method_id: UUID, user_id: UUID
    ) -> bool:
        """
        Delete (deactivate) a payment method.
        Uses payment lock to prevent concurrent deletion and auto-promote race conditions.
        """
        self._check_configured()

        # Use payment lock to prevent concurrent card deletions
        async with payment_lock(user_id, "delete_payment_method"):
            payment_method = await self.get_payment_method(db, payment_method_id, user_id)
            if not payment_method:
                return False

            # If deleting default method, automatically promote another method if available
            if payment_method.is_default:
                other_methods = await self.list_payment_methods(db, user_id)
                # Filter out the one being deleted
                remaining = [m for m in other_methods if m.id != payment_method_id]

                if remaining:
                    # Promote the most recent one (list is sorted by created_at desc)
                    new_default = remaining[0]
                    logger.info(
                        f"Automatically promoting payment method {new_default.id} to default before deleting {payment_method_id}"
                    )
                    await self.set_default_payment_method(db, new_default.id, user_id)

            # Detach from Stripe
            with contextlib.suppress(InvalidRequestError):
                await self._run_stripe_cmd(
                    stripe.PaymentMethod.detach, payment_method.stripe_payment_method_id
                )

            # Soft delete (Preferred for billing history integrity)
            payment_method.is_active = False
            await db.commit()

            logger.info(f"Soft deleted payment method {payment_method_id} for user {user_id}")
            return True

    # =========================================================================
    # Subscription Management
    # =========================================================================

    async def get_subscription(self, db: AsyncSession, user_id: UUID) -> Subscription | None:
        """
        Get the user's current subscription.
        """
        result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
        return result.scalar_one_or_none()

    async def create_or_update_subscription(
        self, db: AsyncSession, user_id: UUID, data: SubscriptionCreate, customer_id: str
    ) -> Subscription:
        """
        Create or update a subscription.

        Uses payment lock to prevent concurrent subscription changes.
        Uses idempotency keys to prevent duplicate Stripe charges.
        """
        self._check_configured()

        # Use payment lock to prevent race conditions - MUST wrap entire operation
        async with payment_lock(user_id, "subscription"):
            existing = await self.get_subscription(db, user_id)
            plan_info = PLAN_DETAILS[data.plan]

            # Generate idempotency key for this operation
            idem_key = generate_subscription_key(user_id, data.plan.value)

            # All subscription logic must be inside this lock block
            return await self._execute_subscription_update(
                db, user_id, data, customer_id, existing, plan_info, idem_key
            )

    async def _execute_subscription_update(  # noqa: PLR0912, PLR0915
        self,
        db: AsyncSession,
        user_id: UUID,
        data: SubscriptionCreate,
        customer_id: str,
        existing: Subscription | None,
        plan_info: Any,
        idem_key: str,
    ) -> Subscription:
        """
        Execute the actual subscription update. Called within payment lock.
        """
        if data.plan == SubscriptionPlanEnum.FREE:
            # Free plan - no Stripe subscription needed
            if existing:
                # Cancel existing Stripe subscription if any
                if existing.stripe_subscription_id:
                    with contextlib.suppress(InvalidRequestError):
                        await self._run_stripe_cmd(
                            stripe.Subscription.delete, existing.stripe_subscription_id
                        )

                existing.plan = SubscriptionPlan.FREE
                existing.status = SubscriptionStatus.ACTIVE
                existing.stripe_subscription_id = None
                existing.price_amount = Decimal(0)
                existing.cancel_at_period_end = False
                existing.current_period_start = None
                existing.current_period_end = None
                await db.commit()
                await db.refresh(existing)
                return existing
            else:
                subscription = Subscription(
                    user_id=user_id,
                    stripe_customer_id=customer_id,
                    plan=SubscriptionPlan.FREE,
                    status=SubscriptionStatus.ACTIVE,
                    price_amount=0,
                    price_currency="usd",
                )
                db.add(subscription)
                await db.commit()
                await db.refresh(subscription)
                return subscription

        # Paid plan - create/update Stripe subscription using price_data

        # Resolve payment method - use provided one or find default
        stripe_payment_method_id = None
        if data.payment_method_id:
            pm = await self.get_payment_method(db, data.payment_method_id, user_id)
            if pm:
                stripe_payment_method_id = pm.stripe_payment_method_id

        # Fallback: find default payment method if not provided
        if not stripe_payment_method_id:
            all_methods = await self.list_payment_methods(db, user_id)
            default_method = next((m for m in all_methods if m.is_default), None)
            if not default_method and all_methods:
                default_method = all_methods[0]
            if default_method:
                stripe_payment_method_id = default_method.stripe_payment_method_id

        # Ensure we have a payment method for paid plans
        if not stripe_payment_method_id:
            raise ValueError(
                "A payment method is required for paid plans. Please add a card first."
            )

        # Prepare Stripe Product and Price (Subscription.create requires a price ID, not inline price_data)
        # First, find or create a product for this plan
        product_name = f"Insight Flow {plan_info.name} Plan"
        plan_id_str = data.plan.value
        target_unit_amount = int(plan_info.price_monthly * 100)

        # List products and filter by metadata (more reliable than search)
        try:
            existing_products = await self._run_stripe_cmd(
                stripe.Product.list, limit=100, active=True
            )

            product = None
            for p in existing_products.data:
                if p.metadata.get("plan_id") == plan_id_str:
                    product = p
                    break

            if not product:
                # Create new product
                product = await self._run_stripe_cmd(
                    stripe.Product.create, name=product_name, metadata={"plan_id": plan_id_str}
                )
                logger.info(f"Created new Stripe product: {product.id}")

            # Find or create a price for this product
            existing_prices = await self._run_stripe_cmd(
                stripe.Price.list, product=product.id, active=True, type="recurring"
            )

            stripe_price_id = None
            for price in existing_prices.data:
                if (
                    price.unit_amount == target_unit_amount
                    and price.currency == plan_info.currency
                    and price.recurring
                    and price.recurring.interval == "month"
                ):
                    stripe_price_id = price.id
                    break

            if not stripe_price_id:
                # Create a new price
                price = await self._run_stripe_cmd(
                    stripe.Price.create,
                    product=product.id,
                    currency=plan_info.currency,
                    unit_amount=target_unit_amount,
                    recurring={"interval": "month"},
                )
                stripe_price_id = price.id
                logger.info(f"Created new Stripe price: {stripe_price_id}")

        except StripeError as e:
            logger.error(f"Stripe error during product/price setup: {e}")
            raise ValueError(f"Failed to set up subscription: {e!s}")

        if existing:
            if existing.stripe_subscription_id:
                # Update existing Stripe subscription
                try:
                    # Retrieve to get item ID
                    sub = await self._run_stripe_cmd(
                        stripe.Subscription.retrieve, existing.stripe_subscription_id
                    )
                    item_id = sub["items"]["data"][0].id

                    # Update subscription
                    modify_kwargs = {
                        "items": [
                            {
                                "id": item_id,
                                "price": stripe_price_id,
                            }
                        ],
                        "proration_behavior": "always_invoice",
                        "expand": ["latest_invoice"],
                    }
                    modify_kwargs_typed: dict[str, Any] = modify_kwargs
                    if stripe_payment_method_id:
                        modify_kwargs["default_payment_method"] = stripe_payment_method_id

                    stripe_sub = await self._run_stripe_cmd(
                        stripe.Subscription.modify,
                        existing.stripe_subscription_id,
                        **modify_kwargs_typed,
                    )

                    # Record payment immediately
                    if hasattr(stripe_sub, "latest_invoice"):
                        await self._record_invoice_payment(
                            db, user_id, existing.id, stripe_sub.latest_invoice
                        )
                except InvalidRequestError as e:
                    logger.error(f"Failed to update subscription in Stripe: {e}")
                    # Fallback: if subscription doesn't exist in Stripe, create new
                    if "No such subscription" in str(e):
                        stripe_sub = await self._run_stripe_cmd(
                            stripe.Subscription.create,
                            customer=customer_id,
                            items=[{"price": stripe_price_id}],
                            default_payment_method=stripe_payment_method_id,
                            metadata={"user_id": str(user_id)},
                            expand=["latest_invoice"],
                        )
                        existing.stripe_subscription_id = stripe_sub.id

                        # Record payment immediately
                        if hasattr(stripe_sub, "latest_invoice"):
                            await self._record_invoice_payment(
                                db, user_id, existing.id, stripe_sub.latest_invoice
                            )
                    else:
                        raise
            else:
                # Has local record but no Stripe ID (was previously Free or error)
                stripe_sub = await self._run_stripe_cmd(
                    stripe.Subscription.create,
                    customer=customer_id,
                    items=[{"price": stripe_price_id}],
                    default_payment_method=stripe_payment_method_id,
                    metadata={"user_id": str(user_id)},
                )
                existing.stripe_subscription_id = stripe_sub.id

            # Extract period dates and status from Stripe response
            period_start = None
            period_end = None
            if stripe_sub:
                if stripe_sub.current_period_start:
                    period_start = datetime.fromtimestamp(
                        stripe_sub.current_period_start
                    ).isoformat()
                if stripe_sub.current_period_end:
                    period_end = datetime.fromtimestamp(stripe_sub.current_period_end).isoformat()

            # Update local DB fields
            existing.plan = SubscriptionPlan(data.plan.value)
            existing.status = SubscriptionStatus.ACTIVE
            existing.stripe_customer_id = customer_id
            existing.price_amount = plan_info.price_monthly
            existing.price_currency = plan_info.currency
            existing.current_period_start = period_start
            existing.current_period_end = period_end
            if data.payment_method_id:
                existing.default_payment_method_id = data.payment_method_id  # type: ignore

            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            # Create new local and Stripe subscription
            stripe_sub = await self._run_stripe_cmd(
                stripe.Subscription.create,
                customer=customer_id,
                items=[{"price": stripe_price_id}],
                default_payment_method=stripe_payment_method_id,
                metadata={"user_id": str(user_id)},
                expand=["latest_invoice"],
                idempotency_key=idem_key,
            )

            # Extract period dates from Stripe response
            period_start = None
            period_end = None
            if stripe_sub.current_period_start:
                period_start = datetime.fromtimestamp(stripe_sub.current_period_start).isoformat()
            if stripe_sub.current_period_end:
                period_end = datetime.fromtimestamp(stripe_sub.current_period_end).isoformat()

            subscription = Subscription(
                user_id=user_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=stripe_sub.id,
                plan=SubscriptionPlan(data.plan.value),
                status=SubscriptionStatus.ACTIVE,
                price_amount=plan_info.price_monthly,
                price_currency=plan_info.currency,
                default_payment_method_id=data.payment_method_id,
                current_period_start=period_start,
                current_period_end=period_end,
            )
            db.add(subscription)
            await db.commit()
            await db.refresh(subscription)

            # Record payment immediately (now that subscription has an ID)
            if hasattr(stripe_sub, "latest_invoice"):
                await self._record_invoice_payment(
                    db, user_id, subscription.id, stripe_sub.latest_invoice
                )

            return subscription

    async def cancel_subscription(
        self, db: AsyncSession, user_id: UUID, cancel_immediately: bool = False
    ) -> Subscription | None:
        """
        Cancel a subscription.
        Uses payment lock to prevent concurrent cancellation requests.
        """
        self._check_configured()

        # Use payment lock to prevent concurrent cancellation
        async with payment_lock(user_id, "cancel_subscription"):
            subscription = await self.get_subscription(db, user_id)
            if not subscription:
                return None

            if subscription.stripe_subscription_id:
                if cancel_immediately:
                    await self._run_stripe_cmd(
                        stripe.Subscription.delete, subscription.stripe_subscription_id
                    )
                    subscription.status = SubscriptionStatus.CANCELED

                    # Downgrade to free plan immediately
                    subscription.plan = SubscriptionPlan.FREE
                    subscription.price_amount = Decimal(0)
                    subscription.current_period_start = None
                    subscription.current_period_end = None
                else:
                    await self._run_stripe_cmd(
                        stripe.Subscription.modify,
                        subscription.stripe_subscription_id,
                        cancel_at_period_end=True,
                    )
                    subscription.cancel_at_period_end = True
                    # Do NOT downgrade yet; wait for period end (webhook)
            else:
                # No Stripe subscription, just mark as canceled
                subscription.status = SubscriptionStatus.CANCELED
                subscription.plan = SubscriptionPlan.FREE
                subscription.price_amount = Decimal(0)
                subscription.current_period_start = None
                subscription.current_period_end = None

            await db.commit()
            await db.refresh(subscription)

            logger.info(f"Canceled subscription for user {user_id}")
            return subscription

    async def resume_subscription(self, db: AsyncSession, user_id: UUID) -> Subscription | None:
        """
        Resume a canceled subscription (re-enable auto-renew).
        Only works if the subscription is still active but scheduled to cancel.
        Uses payment lock to prevent concurrent resume requests.
        """
        self._check_configured()

        # Use payment lock to prevent concurrent resume
        async with payment_lock(user_id, "resume_subscription"):
            subscription = await self.get_subscription(db, user_id)
            if not subscription:
                raise ValueError("No subscription found")

            if not subscription.stripe_subscription_id:
                raise ValueError("Cannot resume a free or local-only subscription")

            # Check if actually resumable
            if subscription.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]:
                raise ValueError(
                    f"Cannot resume subscription with status '{subscription.status}'. Please subscribe to a new plan."
                )

            if not subscription.cancel_at_period_end:
                # Already active/auto-renewing
                return subscription

            # Update Stripe
            try:
                stripe_sub = await self._run_stripe_cmd(
                    stripe.Subscription.modify,
                    subscription.stripe_subscription_id,
                    cancel_at_period_end=False,
                )
            except InvalidRequestError as e:
                logger.error(f"Failed to resume subscription in Stripe: {e}")
                raise ValueError("Failed to resume subscription with payment provider")

            # Update local
            subscription.cancel_at_period_end = False
            subscription.status = SubscriptionStatus(stripe_sub.status)

            await db.commit()
            await db.refresh(subscription)

            logger.info(f"Resumed subscription for user {user_id}")
            return subscription

    async def _record_invoice_payment(
        self, db: AsyncSession, user_id: UUID, subscription_id: UUID, invoice: Any
    ):
        """
        Record a successful payment from an invoice object (e.g. from latest_invoice expansion).
        Handles duplicate insertion gracefully.
        """
        if not invoice or isinstance(invoice, str):
            return

        # Check status (we only care about paid invoices here)
        if invoice.status != "paid" or invoice.amount_paid == 0:
            return

        # Check if already exists (optimization)
        result = await db.execute(
            select(PaymentHistory).where(PaymentHistory.stripe_invoice_id == invoice.id)
        )
        if result.scalar_one_or_none():
            return

        history = PaymentHistory(
            user_id=user_id,
            subscription_id=subscription_id,
            stripe_payment_intent_id=invoice.payment_intent
            if hasattr(invoice, "payment_intent") and not isinstance(invoice.payment_intent, dict)
            else (
                invoice.payment_intent.id
                if hasattr(invoice, "payment_intent") and invoice.payment_intent
                else None
            ),
            stripe_invoice_id=invoice.id,
            stripe_charge_id=invoice.charge,
            amount=invoice.amount_paid / 100.0,
            currency=invoice.currency,
            status=PaymentStatus.SUCCEEDED,
            description=invoice.description or f"Invoice {invoice.number}",
            invoice_url=invoice.hosted_invoice_url,
            receipt_url=invoice.receipt_url if hasattr(invoice, "receipt_url") else None,
        )

        try:
            db.add(history)
            await db.commit()
            logger.info(f"Recorded immediate payment for invoice {invoice.id}")
        except Exception as e:
            # Likely duplicate
            await db.rollback()
            logger.debug(f"Skipped duplicate invoice recording: {e}")

    async def process_webhook(self, db: AsyncSession, event: stripe.Event):  # noqa: PLR0912
        """
        Process Stripe webhook events to keep local DB in sync.
        Implements idempotency using WebhookEventLog to prevent duplicate processing.
        """
        from datetime import datetime

        from models.webhook_log import WebhookEventLog

        event_id = event.get("id")
        event_type = event.get("type")
        data = event.get("data", {}).get("object", {})

        logger.info(f"Received webhook event: {event_type} (ID: {event_id})")

        # Check for duplicate event (idempotency)
        existing_log = await db.execute(
            select(WebhookEventLog).where(WebhookEventLog.stripe_event_id == event_id)
        )
        existing = existing_log.scalar_one_or_none()

        if existing and existing.processed:
            logger.info(f"Skipping already processed webhook event: {event_id}")
            return

        # Create or update log entry
        if not existing:
            webhook_log = WebhookEventLog(
                stripe_event_id=event_id,
                event_type=event_type,
                # The Stripe signature has already been verified. Keep only
                # idempotency metadata; raw event bodies may contain customer
                # and payment information and do not need durable retention.
                raw_payload=None,
                processed=False,
            )
            db.add(webhook_log)
            await db.flush()
        else:
            webhook_log = existing
            webhook_log.retry_count += 1

        try:
            # Process based on event type
            # Subscription events
            if event_type in (
                "customer.subscription.created",
                "customer.subscription.updated",
            ):
                await self._handle_subscription_updated(db, data)
            elif event_type == "customer.subscription.deleted":
                await self._handle_subscription_deleted(db, data)
            # Payment events
            elif event_type == "invoice.payment_succeeded":
                await self._handle_payment_succeeded(db, data)
            elif event_type == "invoice.payment_failed":
                await self._handle_payment_failed(db, data)
            elif event_type == "invoice.upcoming":
                # Log upcoming invoice for monitoring
                logger.info(f"Upcoming invoice for customer: {data.get('customer')}")
            # Payment method events
            elif event_type == "payment_method.attached":
                await self._handle_payment_method_attached(db, data)
            elif event_type == "payment_method.detached":
                await self._handle_payment_method_detached(db, data)
            # Charge events
            elif event_type == "charge.refunded":
                await self._handle_charge_refunded(db, data)
            else:
                logger.debug(f"Unhandled webhook event type: {event_type}")

            # Mark as processed
            webhook_log.processed = True
            webhook_log.processed_at = datetime.now(UTC)
            webhook_log.error_message = None
            await db.commit()

            logger.info(f"Successfully processed webhook event: {event_id}")

        except Exception as e:
            # Log error but don't fail - allow retry
            webhook_log.error_message = str(e)
            await db.commit()
            logger.error(f"Error processing webhook {event_id}: {e}")
            raise

    async def _handle_subscription_updated(self, db: AsyncSession, stripe_sub: dict):
        """
        Handle subscription updates (renewals, plan changes).
        """
        stripe_sub_id = stripe_sub.get("id")

        # Find local subscription
        result = await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            # Maybe it's a new subscription not yet synced?
            # In a real app we might Create it here, but for now just log.
            logger.warning(f"Received update for unknown subscription {stripe_sub_id}")
            return

        # Update fields
        new_status = stripe_sub.get("status")
        subscription.status = SubscriptionStatus(
            cast("str", new_status or subscription.status.value)
        )
        subscription.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)

        # If subscription is no longer valid for access, downgrade to FREE
        if new_status in ["canceled", "unpaid", "incomplete_expired"]:
            subscription.plan = SubscriptionPlan.FREE
            subscription.price_amount = Decimal(0)
            subscription.current_period_start = None
            subscription.current_period_end = None
            logger.info(
                f"Downgraded subscription {subscription.id} to FREE due to status {new_status}"
            )
        else:
            # Update period dates only if active/trialing/past_due
            if stripe_sub.get("current_period_start"):
                # Ensure timestamp is int (sometimes float in python vs json)
                ts = int(stripe_sub["current_period_start"])
                subscription.current_period_start = datetime.fromtimestamp(ts).isoformat()
            if stripe_sub.get("current_period_end"):
                ts = int(stripe_sub["current_period_end"])
                subscription.current_period_end = datetime.fromtimestamp(ts).isoformat()

        await db.commit()
        logger.info(f"Updated subscription {subscription.id} from webhook")

    async def _handle_subscription_deleted(self, db: AsyncSession, stripe_sub: dict):
        """
        Handle subscription cancellation/expiration.
        """
        stripe_sub_id = stripe_sub.get("id")

        result = await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            return

        # Downgrade to free
        subscription.plan = SubscriptionPlan.FREE
        subscription.status = SubscriptionStatus.CANCELED
        subscription.stripe_subscription_id = None
        subscription.current_period_start = None
        subscription.current_period_end = None

        await db.commit()
        logger.info(f"Downgraded subscription {subscription.id} to FREE due to deletion webhook")

    async def _handle_payment_succeeded(self, db: AsyncSession, invoice: dict):
        """
        Record a successful payment.
        """
        customer_id = invoice.get("customer")
        amount_paid = invoice.get("amount_paid")

        if not amount_paid or amount_paid == 0:
            return  # Ignore zero-amount invoices (like trials or free updates)

        # Find user by strip_customer_id
        from models import User

        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"Payment succeeded for unknown customer {customer_id}")
            return

        # Get subscription ID if present
        subscription_id = None
        if invoice.get("subscription"):
            result = await db.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == invoice.get("subscription")
                )
            )
            sub = result.scalar_one_or_none()
            if sub:
                subscription_id = sub.id

        # Get payment method - look up from invoice or charge
        payment_method_id = None
        stripe_pm_id = invoice.get("default_payment_method")

        # If no default_payment_method on invoice, try to get from charge
        if not stripe_pm_id:
            charge_id = invoice.get("charge")
            if charge_id and isinstance(charge_id, str):
                try:
                    charge = await self._run_stripe_cmd(stripe.Charge.retrieve, charge_id)
                    stripe_pm_id = charge.payment_method
                except Exception as e:
                    logger.debug(f"Could not retrieve charge {charge_id}: {e}")

        # Link to our local payment method record
        if stripe_pm_id:
            result = await db.execute(
                select(PaymentMethod).where(
                    PaymentMethod.stripe_payment_method_id == stripe_pm_id,
                    PaymentMethod.user_id == user.id,
                )
            )
            pm = result.scalar_one_or_none()
            if pm:
                payment_method_id = pm.id

        # Create history record
        history = PaymentHistory(
            user_id=user.id,
            subscription_id=subscription_id,
            payment_method_id=payment_method_id,
            stripe_payment_intent_id=invoice.get("payment_intent"),
            stripe_invoice_id=invoice.get("id"),
            stripe_charge_id=invoice.get("charge"),
            amount=amount_paid / 100.0,  # Convert cents to dollars
            currency=invoice.get("currency", "usd"),
            status=PaymentStatus.SUCCEEDED,
            description=invoice.get("description") or f"Invoice {invoice.get('number')}",
            invoice_url=invoice.get("hosted_invoice_url"),
            receipt_url=invoice.get("receipt_url"),  # Often null until email sent
        )

        try:
            db.add(history)
            await db.commit()
            logger.info(
                f"Recorded payment of {history.amount} {history.currency} for user {user.id}"
            )
        except Exception as e:
            # Check for integrity error (duplicate payment)
            if "IntegrityError" in type(e).__name__ or "unique constraint" in str(e).lower():
                await db.rollback()
                logger.warning(
                    f"Duplicate payment event received for invoice {invoice.get('id')}. Skipping."
                )
            else:
                raise e

    async def _handle_payment_failed(self, db: AsyncSession, invoice: dict):
        """
        Handle failed payment.
        """
        customer_id = invoice.get("customer")

        from models import User

        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()

        if not user:
            return

        history = PaymentHistory(
            user_id=user.id,
            stripe_payment_intent_id=invoice.get("payment_intent"),
            stripe_invoice_id=invoice.get("id"),
            amount=invoice.get("amount_due", 0) / 100.0,
            currency=invoice.get("currency", "usd"),
            status=PaymentStatus.FAILED,
            description=f"Payment failed for Invoice {invoice.get('number')}",
            invoice_url=invoice.get("hosted_invoice_url"),
            failure_code=invoice.get("last_payment_error", {}).get("code"),
            failure_message=invoice.get("last_payment_error", {}).get("message"),
        )
        db.add(history)
        await db.commit()
        logger.warning(f"Recorded FAILED payment for user {user.id}")

    async def _handle_payment_method_attached(self, _db: AsyncSession, pm_data: dict):
        """
        Handle payment method attached to customer.
        This is informational - the main flow already syncs payment methods.
        """
        pm_id = pm_data.get("id")
        customer_id = pm_data.get("customer")
        logger.info(f"Payment method {pm_id} attached to customer {customer_id}")

    async def _handle_payment_method_detached(self, db: AsyncSession, pm_data: dict):
        """
        Handle payment method detached from customer.
        Deactivate local record if it exists.
        """
        stripe_pm_id = pm_data.get("id")

        result = await db.execute(
            select(PaymentMethod).where(PaymentMethod.stripe_payment_method_id == stripe_pm_id)
        )
        payment_method = result.scalar_one_or_none()

        if payment_method:
            payment_method.is_active = False
            await db.commit()
            logger.info(f"Deactivated payment method {payment_method.id} via webhook")

    async def _handle_charge_refunded(self, db: AsyncSession, charge_data: dict):
        """
        Handle charge refunded event.
        Update payment history record to reflect refund.
        Supports both full and partial refunds.
        """
        charge_id = charge_data.get("id")
        amount_refunded = charge_data.get("amount_refunded", 0) / 100.0
        original_amount = charge_data.get("amount", 0) / 100.0
        refunded = charge_data.get("refunded", False)  # True if fully refunded

        # Find payment history by charge ID
        result = await db.execute(
            select(PaymentHistory).where(PaymentHistory.stripe_charge_id == charge_id)
        )
        history = result.scalar_one_or_none()

        if history:
            # Track refunded amount (supports incremental partial refunds)
            history.refunded_amount = amount_refunded

            # Only mark as REFUNDED if fully refunded
            if refunded or (original_amount > 0 and amount_refunded >= original_amount):
                history.status = PaymentStatus.REFUNDED
                history.description = f"{history.description} (Fully Refunded)"
            else:
                # Partial refund - keep as succeeded but track amount
                history.description = (
                    f"{history.description} (Partial Refund: ${amount_refunded:.2f})"
                )

            await db.commit()
            logger.info(
                f"Updated payment {history.id} with refund: ${amount_refunded:.2f} (full={refunded})"
            )
        else:
            logger.warning(f"Received refund for unknown charge: {charge_id}")


# Singleton instance
payment_service = PaymentService()


def get_payment_service() -> PaymentService:
    """Get the payment service singleton."""
    return payment_service
