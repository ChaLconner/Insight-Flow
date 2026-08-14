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
import inspect
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import stripe
from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError
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


@contextlib.asynccontextmanager
async def _payment_savepoint(db: AsyncSession):
    """Use a savepoint when the session supports it, including test doubles."""
    begin_nested = getattr(db, "begin_nested", None)
    if begin_nested is None:
        yield
        return

    transaction = begin_nested()
    if inspect.isawaitable(transaction):
        transaction = await transaction
    if not hasattr(transaction, "__aenter__"):
        yield
        return

    async with transaction:
        yield


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

    @staticmethod
    def _subscription_status_from_stripe(
        stripe_subscription: Any,
        *,
        default: SubscriptionStatus,
    ) -> SubscriptionStatus:
        """Map Stripe status without failing open to an active subscription."""
        raw_status = getattr(stripe_subscription, "status", None)
        if raw_status is None and isinstance(stripe_subscription, dict):
            raw_status = stripe_subscription.get("status")
        try:
            return SubscriptionStatus(str(raw_status))
        except (TypeError, ValueError):
            logger.warning("Unknown Stripe subscription status %r; using %s", raw_status, default)
            return default

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

    async def _find_customer_id(
        self, db: AsyncSession, user_id: UUID, user: Any | None
    ) -> tuple[str | None, Any | None]:
        if user and hasattr(user, "stripe_customer_id") and user.stripe_customer_id:
            return user.stripe_customer_id, user

        from models import User

        result = await db.execute(select(User).where(User.id == user_id))
        db_user = result.scalar_one_or_none()
        if db_user and hasattr(db_user, "stripe_customer_id") and db_user.stripe_customer_id:
            return db_user.stripe_customer_id, db_user

        result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
        subscription = result.scalar_one_or_none()
        if subscription and subscription.stripe_customer_id:
            return subscription.stripe_customer_id, user

        result = await db.execute(
            select(PaymentMethod).where(PaymentMethod.user_id == user_id).limit(1)
        )
        payment_method = result.scalar_one_or_none()
        if payment_method and payment_method.stripe_customer_id:
            return payment_method.stripe_customer_id, user
        return None, user

    async def _cache_customer_id(self, db: AsyncSession, user_id: UUID, customer_id: str) -> None:
        from models import User

        await db.execute(
            update(User).where(User.id == user_id).values(stripe_customer_id=customer_id)
        )
        await db.commit()

    async def _clear_stale_customer_data(self, db: AsyncSession, user_id: UUID) -> None:
        from models import User

        await db.execute(update(User).where(User.id == user_id).values(stripe_customer_id=None))
        await db.execute(
            update(Subscription)
            .where(Subscription.user_id == user_id)
            .values(stripe_customer_id=None, stripe_subscription_id=None)
        )
        await db.execute(delete(PaymentMethod).where(PaymentMethod.user_id == user_id))
        await db.commit()
        logger.info(f"Cleared stale customer data for user {user_id}")

    async def _verify_customer_id(
        self, db: AsyncSession, user_id: UUID, customer_id: str, user: Any | None
    ) -> bool:
        try:
            await self._run_stripe_cmd(stripe.Customer.retrieve, customer_id)
            if user and hasattr(user, "stripe_customer_id") and not user.stripe_customer_id:
                await self._cache_customer_id(db, user_id, customer_id)
            return True
        except InvalidRequestError as error:
            if "No such customer" not in str(error) and "resource_missing" not in str(error):
                raise
            logger.warning(f"Customer {customer_id} not found in Stripe, creating new one")
            await self._clear_stale_customer_data(db, user_id)
            return False

    async def _find_customer_by_email(
        self, db: AsyncSession, user_id: UUID, email: str
    ) -> str | None:
        try:
            search_result = await self._run_stripe_cmd(stripe.Customer.list, email=email, limit=1)
            if search_result and search_result.data:
                customer_id = str(search_result.data[0].id)
                logger.info(f"Found existing Stripe customer {customer_id} by email {email}")
                await self._cache_customer_id(db, user_id, customer_id)
                return customer_id
        except Exception as error:
            logger.warning(f"Error searching Stripe customer by email: {error}")
        return None

    async def _create_stripe_customer(
        self, db: AsyncSession, user_id: UUID, email: str, name: str | None
    ) -> str:
        customer = await self._run_stripe_cmd(
            stripe.Customer.create, email=email, name=name, metadata={"user_id": str(user_id)}
        )
        await self._cache_customer_id(db, user_id, customer.id)
        logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
        return str(customer.id)

    async def get_or_create_stripe_customer(
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
        existing_customer_id, user = await self._find_customer_id(db, user_id, user)
        if existing_customer_id and await self._verify_customer_id(
            db, user_id, existing_customer_id, user
        ):
            return existing_customer_id

        customer_id = await self._find_customer_by_email(db, user_id, email)
        if customer_id:
            return customer_id
        return await self._create_stripe_customer(db, user_id, email, name)

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

    async def _ensure_payment_method_customer(
        self, data: PaymentMethodCreate, customer_id: str
    ) -> Any:
        pm = await self._run_stripe_cmd(stripe.PaymentMethod.retrieve, data.payment_method_id)
        if pm.customer and str(pm.customer) != customer_id:
            raise ValueError("Payment method does not belong to current customer")
        if not pm.customer:
            await self._run_stripe_cmd(
                stripe.PaymentMethod.attach, data.payment_method_id, customer=customer_id
            )
        return pm

    async def _set_default_payment_method(
        self,
        db: AsyncSession,
        user_id: UUID,
        data: PaymentMethodCreate,
        customer_id: str,
    ) -> None:
        if not data.set_as_default:
            return
        await db.execute(
            update(PaymentMethod).where(PaymentMethod.user_id == user_id).values(is_default=False)
        )
        await self._run_stripe_cmd(
            stripe.Customer.modify,
            customer_id,
            invoice_settings={"default_payment_method": data.payment_method_id},
        )

    @staticmethod
    def _extract_billing_address(data: PaymentMethodCreate) -> dict[str, Any]:
        billing_address = data.billing_address
        if billing_address and hasattr(billing_address, "model_dump"):
            return billing_address.model_dump() or {}
        return {}

    @staticmethod
    def _billing_value(value: Any, billing_details: Any, field_name: str) -> Any:
        fallback = getattr(billing_details, field_name, None) if billing_details else None
        return value or fallback

    @staticmethod
    def _address_value(
        billing_address: dict[str, Any], stripe_address: Any, field_name: str
    ) -> Any:
        return billing_address.get(field_name) or getattr(stripe_address, field_name, None)

    def _build_billing_fields(self, data: PaymentMethodCreate, pm: Any) -> dict[str, Any]:
        billing_address = self._extract_billing_address(data)
        billing_details = pm.billing_details
        stripe_address = billing_details.address if billing_details else None

        return {
            "billing_name": self._billing_value(data.billing_name, billing_details, "name"),
            "billing_email": self._billing_value(data.billing_email, billing_details, "email"),
            "billing_phone": self._billing_value(data.billing_phone, billing_details, "phone"),
            "billing_address_line1": self._address_value(billing_address, stripe_address, "line1"),
            "billing_address_line2": self._address_value(billing_address, stripe_address, "line2"),
            "billing_city": self._address_value(billing_address, stripe_address, "city"),
            "billing_state": self._address_value(billing_address, stripe_address, "state"),
            "billing_postal_code": self._address_value(
                billing_address, stripe_address, "postal_code"
            ),
            "billing_country": self._address_value(billing_address, stripe_address, "country"),
        }

    def _build_payment_method(
        self,
        user_id: UUID,
        data: PaymentMethodCreate,
        customer_id: str,
        pm: Any,
    ) -> PaymentMethod:
        return PaymentMethod(
            user_id=user_id,
            stripe_payment_method_id=data.payment_method_id,
            stripe_customer_id=customer_id,
            card_brand=pm.card.brand,
            card_last4=pm.card.last4,
            card_exp_month=pm.card.exp_month,
            card_exp_year=pm.card.exp_year,
            card_funding=pm.card.funding,
            card_country=pm.card.country,
            card_fingerprint=pm.card.fingerprint,
            is_default=data.set_as_default,
            is_active=True,
            **self._build_billing_fields(data, pm),
        )

    async def attach_payment_method(
        self, db: AsyncSession, user_id: UUID, data: PaymentMethodCreate, customer_id: str
    ) -> PaymentMethod:
        """
        Attach a payment method to a user after SetupIntent confirmation.
        """
        self._check_configured()

        pm = await self._ensure_payment_method_customer(data, customer_id)
        await self._set_default_payment_method(db, user_id, data, customer_id)
        payment_method = self._build_payment_method(user_id, data, customer_id, pm)

        db.add(payment_method)

        # Also update User's stripe_customer_id to ensure consistency
        from models import User

        await db.execute(
            update(User).where(User.id == user_id).values(stripe_customer_id=customer_id)
        )

        try:
            await db.commit()
        except Exception as e:
            logger.exception(f"COMMIT FAILED: {e}")
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
            .where(PaymentMethod.is_active.is_(True))
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
                active_sub.default_payment_method_id = payment_method.id
                db.add(active_sub)
                logger.info(
                    f"Updated subscription {active_sub.id} to use new default payment method {payment_method.id}"
                )
            except Exception as e:
                logger.exception(f"Failed to update subscription default payment method: {e}")
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

        status_expr = cast(PaymentHistory.status, String)
        refunded_amount_expr = func.coalesce(PaymentHistory.refunded_amount, Decimal(0))
        net_amount_expr = case(
            (
                PaymentHistory.amount > refunded_amount_expr,
                PaymentHistory.amount - refunded_amount_expr,
            ),
            else_=Decimal(0),
        )
        successful_currency_expr = case(
            (status_expr == PaymentStatus.SUCCEEDED.value, PaymentHistory.currency),
            else_=None,
        )

        # Aggregate query for stats. Total spent is net of partial refunds and
        # currency is based only on successful payments.
        result = await db.execute(
            select(
                func.coalesce(
                    func.sum(
                        case(
                            (
                                status_expr == PaymentStatus.SUCCEEDED.value,
                                net_amount_expr,
                            ),
                            else_=Decimal(0),
                        )
                    ),
                    Decimal(0),
                ).label("total_spent"),
                func.count(PaymentHistory.id).label("total_payments"),
                func.sum(
                    case(
                        (status_expr == PaymentStatus.SUCCEEDED.value, 1),
                        else_=0,
                    )
                ).label("successful_payments"),
                func.sum(
                    case(
                        (status_expr == PaymentStatus.FAILED.value, 1),
                        else_=0,
                    )
                ).label("failed_payments"),
                func.sum(
                    case(
                        (status_expr == PaymentStatus.PENDING.value, 1),
                        else_=0,
                    )
                ).label("pending_payments"),
                func.sum(
                    case(
                        (status_expr == PaymentStatus.REFUNDED.value, 1),
                        else_=0,
                    )
                ).label("refunded_payments"),
                func.count(func.distinct(successful_currency_expr)).label("currency_count"),
                func.min(successful_currency_expr).label("currency"),
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

        currency_count = int(row.currency_count) if isinstance(row.currency_count, int) else 0
        currency = row.currency if isinstance(row.currency, str) else None
        if currency_count > 1:
            display_currency = "mixed"
        elif currency:
            display_currency = currency
        else:
            display_currency = "usd"

        return {
            "total_spent": float(row.total_spent or 0),
            "total_payments": int(row.total_payments or 0),
            "successful_payments": int(row.successful_payments or 0),
            "failed_payments": int(row.failed_payments or 0),
            "pending_payments": int(row.pending_payments or 0),
            "refunded_payments": int(row.refunded_payments or 0),
            "currency": display_currency,
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
        result = await db.execute(
            select(Subscription).where(Subscription.user_id == user_id).with_for_update()
        )
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

    async def _execute_free_subscription(
        self,
        db: AsyncSession,
        user_id: UUID,
        customer_id: str,
        existing: Subscription | None,
    ) -> Subscription:
        if existing:
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

    async def _resolve_subscription_payment_method(
        self, db: AsyncSession, user_id: UUID, data: SubscriptionCreate
    ) -> str:
        stripe_payment_method_id = None
        if data.payment_method_id:
            payment_method = await self.get_payment_method(db, data.payment_method_id, user_id)
            if payment_method:
                stripe_payment_method_id = payment_method.stripe_payment_method_id

        if not stripe_payment_method_id:
            all_methods = await self.list_payment_methods(db, user_id)
            default_method = next((method for method in all_methods if method.is_default), None)
            if not default_method and all_methods:
                default_method = all_methods[0]
            if default_method:
                stripe_payment_method_id = default_method.stripe_payment_method_id

        if not stripe_payment_method_id:
            raise ValueError(
                "A payment method is required for paid plans. Please add a card first."
            )
        return stripe_payment_method_id

    async def _get_or_create_stripe_price(self, plan_info: Any, plan_id: str) -> str:
        product_name = f"Insight Flow {plan_info.name} Plan"
        target_unit_amount = int(plan_info.price_monthly * 100)
        try:
            products = await self._run_stripe_cmd(stripe.Product.list, limit=100, active=True)
            product = next(
                (item for item in products.data if item.metadata.get("plan_id") == plan_id),
                None,
            )
            if not product:
                product = await self._run_stripe_cmd(
                    stripe.Product.create,
                    name=product_name,
                    metadata={"plan_id": plan_id},
                )
                logger.info(f"Created new Stripe product: {product.id}")

            prices = await self._run_stripe_cmd(
                stripe.Price.list, product=product.id, active=True, type="recurring"
            )
            matching_price = next(
                (
                    price
                    for price in prices.data
                    if price.unit_amount == target_unit_amount
                    and price.currency == plan_info.currency
                    and price.recurring
                    and price.recurring.interval == "month"
                ),
                None,
            )
            if matching_price:
                return str(matching_price.id)

            price = await self._run_stripe_cmd(
                stripe.Price.create,
                product=product.id,
                currency=plan_info.currency,
                unit_amount=target_unit_amount,
                recurring={"interval": "month"},
            )
            logger.info(f"Created new Stripe price: {price.id}")
            return str(price.id)
        except StripeError as error:
            logger.exception("Stripe error during product/price setup: %s", error)
            raise ValueError(f"Failed to set up subscription: {error!s}") from error

    async def _create_stripe_subscription(
        self,
        user_id: UUID,
        customer_id: str,
        stripe_price_id: str,
        stripe_payment_method_id: str,
        *,
        expand_invoice: bool = False,
        idempotency_key: str | None = None,
    ):
        kwargs: dict[str, Any] = {
            "customer": customer_id,
            "items": [{"price": stripe_price_id}],
            "default_payment_method": stripe_payment_method_id,
            "metadata": {"user_id": str(user_id)},
            "payment_behavior": "default_incomplete",
        }
        if expand_invoice:
            kwargs["expand"] = ["latest_invoice"]
        if idempotency_key:
            kwargs["idempotency_key"] = idempotency_key
        return await self._run_stripe_cmd(stripe.Subscription.create, **kwargs)

    async def _modify_stripe_subscription(
        self,
        subscription_id: str,
        stripe_price_id: str,
        stripe_payment_method_id: str,
    ):
        subscription = await self._run_stripe_cmd(stripe.Subscription.retrieve, subscription_id)
        item_id = subscription["items"]["data"][0].id
        modify_kwargs: dict[str, Any] = {
            "items": [{"id": item_id, "price": stripe_price_id}],
            "proration_behavior": "always_invoice",
            "expand": ["latest_invoice"],
            "payment_behavior": "error_if_incomplete",
        }
        if stripe_payment_method_id:
            modify_kwargs["default_payment_method"] = stripe_payment_method_id
        return await self._run_stripe_cmd(
            stripe.Subscription.modify, subscription_id, **modify_kwargs
        )

    async def _update_existing_stripe_subscription(
        self,
        db: AsyncSession,
        user_id: UUID,
        existing: Subscription,
        customer_id: str,
        stripe_price_id: str,
        stripe_payment_method_id: str,
    ):
        if not existing.stripe_subscription_id:
            return await self._create_stripe_subscription(
                user_id,
                customer_id,
                stripe_price_id,
                stripe_payment_method_id,
            )

        try:
            stripe_sub = await self._modify_stripe_subscription(
                existing.stripe_subscription_id,
                stripe_price_id,
                stripe_payment_method_id,
            )
            if hasattr(stripe_sub, "latest_invoice"):
                await self._record_invoice_payment(
                    db, user_id, existing.id, stripe_sub.latest_invoice
                )
            return stripe_sub
        except InvalidRequestError as error:
            logger.exception("Failed to update subscription in Stripe: %s", error)
            if "No such subscription" not in str(error):
                raise
            stripe_sub = await self._create_stripe_subscription(
                user_id,
                customer_id,
                stripe_price_id,
                stripe_payment_method_id,
                expand_invoice=True,
            )
            existing.stripe_subscription_id = stripe_sub.id
            if hasattr(stripe_sub, "latest_invoice"):
                await self._record_invoice_payment(
                    db, user_id, existing.id, stripe_sub.latest_invoice
                )
            return stripe_sub

    @staticmethod
    def _subscription_period(stripe_sub):
        if not stripe_sub:
            return None, None
        period_start = (
            datetime.fromtimestamp(stripe_sub.current_period_start).isoformat()
            if stripe_sub.current_period_start
            else None
        )
        period_end = (
            datetime.fromtimestamp(stripe_sub.current_period_end).isoformat()
            if stripe_sub.current_period_end
            else None
        )
        return period_start, period_end

    async def _execute_subscription_update(
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
            return await self._execute_free_subscription(db, user_id, customer_id, existing)

        # Paid plan - create/update Stripe subscription using price_data

        stripe_payment_method_id = await self._resolve_subscription_payment_method(
            db, user_id, data
        )
        stripe_price_id = await self._get_or_create_stripe_price(plan_info, data.plan.value)

        if existing:
            stripe_sub = await self._update_existing_stripe_subscription(
                db,
                user_id,
                existing,
                customer_id,
                stripe_price_id,
                stripe_payment_method_id,
            )
            period_start, period_end = self._subscription_period(stripe_sub)
            existing.plan = SubscriptionPlan(data.plan.value)
            existing.status = self._subscription_status_from_stripe(
                stripe_sub, default=SubscriptionStatus.INCOMPLETE
            )
            existing.stripe_customer_id = customer_id
            existing.price_amount = plan_info.price_monthly
            existing.price_currency = plan_info.currency
            existing.current_period_start = period_start
            existing.current_period_end = period_end
            if data.payment_method_id:
                existing.default_payment_method_id = data.payment_method_id

            await db.commit()
            await db.refresh(existing)
            return existing

        stripe_sub = await self._create_stripe_subscription(
            user_id,
            customer_id,
            stripe_price_id,
            stripe_payment_method_id,
            expand_invoice=True,
            idempotency_key=idem_key,
        )
        period_start, period_end = self._subscription_period(stripe_sub)
        subscription = Subscription(
            user_id=user_id,
            stripe_customer_id=customer_id,
            stripe_subscription_id=stripe_sub.id,
            plan=SubscriptionPlan(data.plan.value),
            status=self._subscription_status_from_stripe(
                stripe_sub, default=SubscriptionStatus.INCOMPLETE
            ),
            price_amount=plan_info.price_monthly,
            price_currency=plan_info.currency,
            default_payment_method_id=data.payment_method_id,
            current_period_start=period_start,
            current_period_end=period_end,
        )
        db.add(subscription)
        await db.commit()
        await db.refresh(subscription)
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

        # Use the same lock namespace as create/update/resume.
        async with payment_lock(user_id, "subscription"):
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
        async with payment_lock(user_id, "subscription"):
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
                logger.exception(f"Failed to resume subscription in Stripe: {e}")
                raise ValueError("Failed to resume subscription with payment provider")

            # Update local
            subscription.cancel_at_period_end = False
            # Provider statuses can gain new values.  Map unknown values to a
            # non-entitled state instead of turning a successful resume into a
            # 500 or failing open to an active subscription.
            subscription.status = self._subscription_status_from_stripe(
                stripe_sub, default=SubscriptionStatus.INCOMPLETE
            )

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

        payment_intent = getattr(invoice, "payment_intent", None)
        if isinstance(payment_intent, dict):
            payment_intent_id = getattr(payment_intent, "id", None)
        else:
            payment_intent_id = payment_intent

        history = PaymentHistory(
            user_id=user_id,
            subscription_id=subscription_id,
            stripe_payment_intent_id=payment_intent_id,
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
            async with _payment_savepoint(db):
                db.add(history)
                await db.flush()
            logger.info(f"Recorded immediate payment for invoice {invoice.id}")
        except IntegrityError:
            # A concurrent webhook may have inserted the same invoice. Only
            # suppress the database integrity error; connection/programming
            # failures must reach the caller and trigger a retry.
            logger.debug(f"Skipped duplicate invoice recording: {invoice.id}")

    async def _claim_webhook_event(
        self, db: AsyncSession, event_id: str, event_type: str | None
    ) -> tuple[Any | None, int]:
        from models.webhook_log import WebhookEventLog

        existing_log = await db.execute(
            select(WebhookEventLog)
            .where(WebhookEventLog.stripe_event_id == event_id)
            .with_for_update()
        )
        existing = existing_log.scalar_one_or_none()
        if existing and existing.processed:
            logger.info(f"Skipping already processed webhook event: {event_id}")
            return None, 0

        retry_count = (existing.retry_count or 0) + 1 if existing else 1
        if not existing:
            webhook_log = WebhookEventLog(
                stripe_event_id=event_id,
                event_type=event_type,
                raw_payload=None,
                processed=False,
            )
            db.add(webhook_log)
            try:
                await db.flush()
            except IntegrityError:
                await db.rollback()
                existing_log = await db.execute(
                    select(WebhookEventLog)
                    .where(WebhookEventLog.stripe_event_id == event_id)
                    .with_for_update()
                )
                existing = existing_log.scalar_one_or_none()
                if existing is None:
                    raise
                if existing.processed:
                    logger.info(f"Skipping already processed webhook event: {event_id}")
                    return None, retry_count
                webhook_log = existing
                webhook_log.retry_count = retry_count
        else:
            webhook_log = existing
            webhook_log.retry_count = retry_count
        return webhook_log, retry_count

    async def _dispatch_webhook_event(
        self, db: AsyncSession, event_type: str | None, data: dict[str, Any]
    ) -> None:
        if event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
        ):
            await self._handle_subscription_updated(db, data)
        elif event_type == "customer.subscription.deleted":
            await self._handle_subscription_deleted(db, data)
        elif event_type == "invoice.payment_succeeded":
            await self._handle_payment_succeeded(db, data)
        elif event_type == "invoice.payment_failed":
            await self._handle_payment_failed(db, data)
        elif event_type == "invoice.upcoming":
            logger.info(f"Upcoming invoice for customer: {data.get('customer')}")
        elif event_type == "payment_method.attached":
            self._handle_payment_method_attached(db, data)
        elif event_type == "payment_method.detached":
            await self._handle_payment_method_detached(db, data)
        elif event_type == "charge.refunded":
            await self._handle_charge_refunded(db, data)
        else:
            logger.debug(f"Unhandled webhook event type: {event_type}")

    async def _record_webhook_error(
        self,
        db: AsyncSession,
        event_id: str,
        event_type: str | None,
        retry_count: int,
        error: Exception,
    ) -> None:
        from models.webhook_log import WebhookEventLog

        try:
            error_result = await db.execute(
                select(WebhookEventLog).where(WebhookEventLog.stripe_event_id == event_id)
            )
            error_log = error_result.scalar_one_or_none()
            if error_log is None:
                error_log = WebhookEventLog(
                    stripe_event_id=event_id,
                    event_type=event_type,
                    raw_payload=None,
                    processed=False,
                )
                db.add(error_log)
            error_log.error_message = str(error)
            error_log.retry_count = retry_count
            await db.commit()
        except Exception:
            await db.rollback()

    async def process_webhook(self, db: AsyncSession, event: stripe.Event):
        """
        Process Stripe webhook events to keep local DB in sync.
        Implements idempotency using WebhookEventLog to prevent duplicate processing.
        """
        event_data = cast("dict[str, Any]", event)
        event_id = event_data.get("id")
        event_type = event_data.get("type")
        data = event_data.get("data", {}).get("object", {})

        logger.info(f"Received webhook event: {event_type} (ID: {event_id})")

        # Check for duplicate event (idempotency)
        if not event_id:
            raise ValueError("Stripe webhook event is missing its id")

        webhook_log, retry_count = await self._claim_webhook_event(db, event_id, event_type)
        if webhook_log is None:
            return

        try:
            await self._dispatch_webhook_event(db, event_type, data)

            # Mark as processed
            webhook_log.processed = True
            webhook_log.processed_at = datetime.now(UTC)
            webhook_log.error_message = None
            await db.commit()

            logger.info(f"Successfully processed webhook event: {event_id}")

        except Exception as error:
            # Roll back handler changes before recording the retryable error.
            await db.rollback()
            await self._record_webhook_error(db, event_id, event_type, retry_count, error)
            logger.exception("Error processing webhook %s: %s", event_id, error)
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
        try:
            subscription.status = SubscriptionStatus(
                cast("str", new_status or subscription.status.value)
            )
        except ValueError:
            logger.error(
                "Ignoring unknown Stripe subscription status %r for %s",
                new_status,
                subscription.id,
            )
            return
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

        logger.info(f"Downgraded subscription {subscription.id} to FREE due to deletion webhook")

    async def _resolve_invoice_links(
        self, db: AsyncSession, invoice: dict, user: Any
    ) -> tuple[UUID | None, UUID | None]:
        subscription_id: UUID | None = None
        if invoice.get("subscription"):
            result = await db.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == invoice.get("subscription")
                )
            )
            subscription = result.scalar_one_or_none()
            if subscription:
                subscription_id = subscription.id

        stripe_pm_id = invoice.get("default_payment_method")
        if not stripe_pm_id:
            charge_id = invoice.get("charge")
            if charge_id and isinstance(charge_id, str):
                try:
                    charge = await self._run_stripe_cmd(stripe.Charge.retrieve, charge_id)
                    stripe_pm_id = charge.payment_method
                except StripeError as error:
                    logger.debug("Could not retrieve charge %s: %s", charge_id, error)

        payment_method_id: UUID | None = None
        if stripe_pm_id:
            result = await db.execute(
                select(PaymentMethod).where(
                    PaymentMethod.stripe_payment_method_id == stripe_pm_id,
                    PaymentMethod.user_id == user.id,
                )
            )
            payment_method = result.scalar_one_or_none()
            if payment_method:
                payment_method_id = payment_method.id
        return subscription_id, payment_method_id

    async def _promote_existing_payment(
        self,
        db: AsyncSession,
        invoice: dict,
        invoice_id: str | None,
        amount_paid: int,
        subscription_id: UUID | None,
        payment_method_id: UUID | None,
    ) -> bool:
        if not invoice_id:
            return False

        existing_payment = await db.execute(
            select(PaymentHistory)
            .where(PaymentHistory.stripe_invoice_id == invoice_id)
            .with_for_update()
        )
        existing_history = existing_payment.scalar_one_or_none()
        if existing_history is None:
            return False
        if existing_history.status == PaymentStatus.SUCCEEDED:
            logger.info(f"Payment already recorded for invoice {invoice_id}")
            return True

        existing_history.status = PaymentStatus.SUCCEEDED
        existing_history.amount = Decimal(amount_paid) / Decimal("100")
        existing_history.currency = invoice.get("currency", "usd")
        existing_history.subscription_id = subscription_id
        existing_history.payment_method_id = payment_method_id
        existing_history.stripe_payment_intent_id = invoice.get("payment_intent")
        existing_history.stripe_charge_id = invoice.get("charge")
        existing_history.invoice_url = invoice.get("hosted_invoice_url")
        existing_history.receipt_url = invoice.get("receipt_url")
        existing_history.failure_code = None
        existing_history.failure_message = None
        existing_history.description = (
            invoice.get("description") or f"Invoice {invoice.get('number')}"
        )
        await db.flush()
        logger.info(f"Promoted payment {invoice_id} to succeeded")
        return True

    def _build_successful_payment_history(
        self,
        user: Any,
        invoice: dict,
        amount_paid: int,
        subscription_id: UUID | None,
        payment_method_id: UUID | None,
    ) -> PaymentHistory:
        return PaymentHistory(
            user_id=user.id,
            subscription_id=subscription_id,
            payment_method_id=payment_method_id,
            stripe_payment_intent_id=invoice.get("payment_intent"),
            stripe_invoice_id=invoice.get("id"),
            stripe_charge_id=invoice.get("charge"),
            amount=amount_paid / 100.0,
            currency=invoice.get("currency", "usd"),
            status=PaymentStatus.SUCCEEDED,
            description=invoice.get("description") or f"Invoice {invoice.get('number')}",
            invoice_url=invoice.get("hosted_invoice_url"),
            receipt_url=invoice.get("receipt_url"),
        )

    async def _record_successful_payment(
        self, db: AsyncSession, history: PaymentHistory, invoice: dict
    ) -> None:
        try:
            async with _payment_savepoint(db):
                db.add(history)
                await db.flush()
        except IntegrityError:
            identity_filters = []
            if invoice.get("id"):
                identity_filters.append(PaymentHistory.stripe_invoice_id == invoice.get("id"))
            if invoice.get("payment_intent"):
                identity_filters.append(
                    PaymentHistory.stripe_payment_intent_id == invoice.get("payment_intent")
                )
            if not identity_filters:
                raise
            duplicate_result = await db.execute(
                select(PaymentHistory).where(or_(*identity_filters))
            )
            if duplicate_result.scalar_one_or_none() is None:
                raise
            logger.info("Payment already recorded concurrently")
            return
        logger.info(
            f"Recorded payment of {history.amount} {history.currency} for user {history.user_id}"
        )

    async def _handle_payment_succeeded(self, db: AsyncSession, invoice: dict):
        """
        Record a successful payment.
        """
        customer_id = invoice.get("customer")
        amount_paid = invoice.get("amount_paid")

        if not amount_paid or amount_paid == 0:
            return  # Ignore zero-amount invoices (like trials or free updates)

        from models import User

        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"Payment succeeded for unknown customer {customer_id}")
            return

        invoice_id = invoice.get("id")
        subscription_id, payment_method_id = await self._resolve_invoice_links(db, invoice, user)
        if await self._promote_existing_payment(
            db,
            invoice,
            invoice_id,
            amount_paid,
            subscription_id,
            payment_method_id,
        ):
            return

        history = self._build_successful_payment_history(
            user, invoice, amount_paid, subscription_id, payment_method_id
        )
        await self._record_successful_payment(db, history, invoice)

    async def _is_duplicate_failed_payment(
        self, db: AsyncSession, invoice_id: str | None, invoice: dict
    ) -> bool:
        """Check whether a failed-payment insert lost a concurrent race."""
        identity_filters = []
        if invoice_id:
            identity_filters.append(PaymentHistory.stripe_invoice_id == invoice_id)
        payment_intent = invoice.get("payment_intent")
        if payment_intent:
            identity_filters.append(PaymentHistory.stripe_payment_intent_id == payment_intent)
        if not identity_filters:
            return False

        duplicate_result = await db.execute(select(PaymentHistory).where(or_(*identity_filters)))
        if duplicate_result.scalar_one_or_none() is None:
            return False
        logger.info("Failed payment already recorded concurrently")
        return True

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

        invoice_id = invoice.get("id")
        if invoice_id:
            existing_failure = await db.execute(
                select(PaymentHistory)
                .where(
                    PaymentHistory.user_id == user.id,
                    PaymentHistory.stripe_invoice_id == invoice_id,
                )
                .with_for_update()
            )
            existing_history = existing_failure.scalar_one_or_none()
            if existing_history is not None:
                if existing_history.status == PaymentStatus.SUCCEEDED:
                    logger.info(f"Ignoring late failed event for succeeded invoice {invoice_id}")
                    return
                if existing_history.status == PaymentStatus.FAILED:
                    logger.info(f"Failed payment already recorded for invoice {invoice_id}")
                    return
                existing_history.status = PaymentStatus.FAILED
                existing_history.failure_code = invoice.get("last_payment_error", {}).get("code")
                existing_history.failure_message = invoice.get("last_payment_error", {}).get(
                    "message"
                )
                await db.flush()
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
        try:
            async with _payment_savepoint(db):
                db.add(history)
                await db.flush()
        except IntegrityError:
            if not await self._is_duplicate_failed_payment(db, invoice_id, invoice):
                raise
            return
        logger.warning(f"Recorded FAILED payment for user {user.id}")

    def _handle_payment_method_attached(self, _db: AsyncSession, pm_data: dict):
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
