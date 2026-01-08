"""
Comprehensive test suite for payment system.
Tests payment methods, subscriptions, webhooks, and security features.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = MagicMock()
    user.id = uuid4()
    user.email = "test@example.com"
    user.name = "Test User"
    user.stripe_customer_id = "cus_test123456789"
    user.is_active = True
    return user


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def mock_payment_method():
    """Create a mock payment method."""
    pm = MagicMock()
    pm.id = uuid4()
    pm.user_id = uuid4()
    pm.stripe_payment_method_id = "pm_test123456789"
    pm.stripe_customer_id = "cus_test123456789"
    pm.card_brand = "visa"
    pm.card_last4 = "4242"
    pm.card_exp_month = 12
    pm.card_exp_year = 2025
    pm.is_default = True
    pm.is_active = True
    return pm


@pytest.fixture
def mock_subscription():
    """Create a mock subscription."""
    sub = MagicMock()
    sub.id = uuid4()
    sub.user_id = uuid4()
    sub.stripe_subscription_id = "sub_test123456789"
    sub.stripe_customer_id = "cus_test123456789"
    sub.plan = "pro"
    sub.status = "active"
    sub.price_amount = Decimal("6.99")
    sub.cancel_at_period_end = False
    return sub


# ============================================================================
# Stripe Error Handler Tests
# ============================================================================


class TestStripeErrorHandler:
    """Test cases for the Stripe error handler."""

    def test_card_declined_returns_user_friendly_message(self):
        """Test that card declined errors return safe messages."""
        import stripe

        from security.stripe_error_handler import get_safe_error_message

        error = stripe.error.CardError(
            message="Your card was declined.", param="card_number", code="card_declined"
        )

        message = get_safe_error_message(error)
        assert "declined" in message.lower()
        assert "Your card was declined" in message or "try" in message.lower()
        # Should not contain internal details
        assert "param" not in message.lower()

    def test_insufficient_funds_returns_safe_message(self):
        """Test that insufficient funds shows helpful message."""
        import stripe

        from security.stripe_error_handler import get_safe_error_message

        error = stripe.error.CardError(
            message="Your card has insufficient funds.", param="", code="insufficient_funds"
        )

        message = get_safe_error_message(error)
        assert "insufficient funds" in message.lower() or "another" in message.lower()

    def test_rate_limit_returns_retry_message(self):
        """Test that rate limit errors advise to wait."""
        import stripe

        from security.stripe_error_handler import get_safe_error_message

        error = stripe.error.RateLimitError("Too many requests")

        message = get_safe_error_message(error)
        assert "wait" in message.lower() or "try again" in message.lower()

    def test_unknown_error_returns_generic_message(self):
        """Test that unknown errors don't leak details."""
        from security.stripe_error_handler import get_safe_error_message

        error = Exception("Internal database connection failed at port 5432")

        message = get_safe_error_message(error)
        assert "5432" not in message
        assert "database" not in message.lower()
        assert "unexpected" in message.lower() or "try again" in message.lower()

    def test_log_and_get_safe_error_logs_details(self):
        """Test that full details are logged internally."""
        from security.stripe_error_handler import log_and_get_safe_error

        with patch("security.stripe_error_handler.logger") as mock_logger:
            error = ValueError("Test validation error")
            log_and_get_safe_error(error, "test_operation", "user123")

            # Should log with full context
            mock_logger.error.assert_called_once()
            logged_extra = mock_logger.error.call_args
            assert "test_operation" in str(logged_extra)


# ============================================================================
# Idempotency Key Tests
# ============================================================================


class TestIdempotencyKeys:
    """Test cases for idempotency key generation."""

    def test_generate_idempotency_key_is_deterministic(self):
        """Test that same inputs produce same key."""
        from security.payment_operations import generate_idempotency_key

        user_id = uuid4()

        key1 = generate_idempotency_key("test_op", user_id, "plan")
        key2 = generate_idempotency_key("test_op", user_id, "plan")

        assert key1 == key2

    def test_different_operations_produce_different_keys(self):
        """Test that different operations get different keys."""
        from security.payment_operations import generate_idempotency_key

        user_id = uuid4()

        key1 = generate_idempotency_key("subscription", user_id)
        key2 = generate_idempotency_key("setup_intent", user_id)

        assert key1 != key2

    def test_key_format_is_valid_for_stripe(self):
        """Test that keys are valid for Stripe API."""
        from security.payment_operations import generate_setup_intent_key

        key = generate_setup_intent_key(uuid4())

        # Must be string, not too long (Stripe limit is 255)
        assert isinstance(key, str)
        assert len(key) <= 255
        assert len(key) >= 10  # Reasonable minimum

    def test_subscription_key_includes_plan(self):
        """Test that subscription key varies by plan."""
        from security.payment_operations import generate_subscription_key

        user_id = uuid4()

        key_pro = generate_subscription_key(user_id, "pro")
        key_starter = generate_subscription_key(user_id, "starter")

        assert key_pro != key_starter


# ============================================================================
# Payment Lock Tests
# ============================================================================


class TestPaymentLocks:
    """Test cases for payment operation locks."""

    @pytest.mark.asyncio
    async def test_payment_lock_acquires_and_releases(self):
        """Test that locks are properly acquired and released."""
        from security.payment_operations import payment_lock

        user_id = uuid4()
        lock_acquired = False

        async with payment_lock(user_id, "test"):
            lock_acquired = True

        assert lock_acquired

        # Lock should be released, so we can acquire again
        async with payment_lock(user_id, "test"):
            pass  # Should not timeout

    @pytest.mark.asyncio
    async def test_different_users_can_lock_simultaneously(self):
        """Test that different users don't block each other."""
        import asyncio

        from security.payment_operations import payment_lock

        user1 = uuid4()
        user2 = uuid4()
        results = []

        async def task(user_id, label):
            async with payment_lock(user_id, "test"):
                results.append(f"{label}_start")
                await asyncio.sleep(0.01)
                results.append(f"{label}_end")

        # Run concurrently - both should complete
        await asyncio.gather(task(user1, "user1"), task(user2, "user2"))

        assert len(results) == 4
        assert "user1_start" in results
        assert "user2_start" in results


# ============================================================================
# Payment Security Tests
# ============================================================================


class TestPaymentSecurity:
    """Test cases for payment security utilities."""

    def test_validate_payment_amount_rejects_negative(self):
        """Test that negative amounts are rejected."""
        from security.payment_security import validate_payment_amount

        is_valid, error = validate_payment_amount(-10.00)
        assert not is_valid
        assert "negative" in error.lower()

    def test_validate_payment_amount_rejects_excessive(self):
        """Test that excessively large amounts are rejected."""
        from security.payment_security import validate_payment_amount

        is_valid, error = validate_payment_amount(200000.00)
        assert not is_valid
        assert "maximum" in error.lower()

    def test_validate_payment_amount_accepts_valid(self):
        """Test that valid amounts are accepted."""
        from security.payment_security import validate_payment_amount

        is_valid, error = validate_payment_amount(9.99)
        assert is_valid
        assert error == ""

    def test_validate_payment_amount_checks_minimum(self):
        """Test that amounts below Stripe minimum are rejected."""
        from security.payment_security import validate_payment_amount

        is_valid, error = validate_payment_amount(0.10, "usd")
        assert not is_valid
        assert "minimum" in error.lower()

    def test_is_valid_stripe_id_accepts_valid(self):
        """Test Stripe ID validation for valid IDs."""
        from security.payment_security import is_valid_stripe_id

        assert is_valid_stripe_id("pm_1234567890abcdef", "pm_")
        assert is_valid_stripe_id("cus_1234567890abcdef", "cus_")
        assert is_valid_stripe_id("sub_1234567890abcdef", "sub_")
        assert is_valid_stripe_id("pi_1234567890abcdef", "pi_")

    def test_is_valid_stripe_id_rejects_invalid(self):
        """Test Stripe ID validation for invalid IDs."""
        from security.payment_security import is_valid_stripe_id

        assert not is_valid_stripe_id("invalid_id", "pm_")
        assert not is_valid_stripe_id("", "pm_")
        assert not is_valid_stripe_id(None, "pm_")  # type: ignore
        assert not is_valid_stripe_id("pm_short", "pm_")  # Too short

    def test_mask_card_number(self):
        """Test card number masking for PCI compliance."""
        from security.payment_security import mask_card_number

        assert mask_card_number("4242424242424242") == "************4242"
        assert mask_card_number("1234") == "1234"  # Already just last 4
        assert mask_card_number("") == "****"
        assert mask_card_number("123") == "****"


# ============================================================================
# Schema Tests
# ============================================================================


class TestPaymentSchemas:
    """Test cases for payment schemas."""

    def test_payment_history_stats_response_schema(self):
        """Test PaymentHistoryStatsResponse validation."""
        from schemas.payment import PaymentHistoryStatsResponse

        data = {
            "total_spent": 99.90,
            "total_payments": 10,
            "successful_payments": 9,
            "failed_payments": 1,
            "pending_payments": 0,
            "refunded_payments": 0,
            "currency": "usd",
        }

        schema = PaymentHistoryStatsResponse(**data)
        assert schema.total_spent == 99.90
        assert schema.total_payments == 10
        assert schema.successful_payments == 9

    def test_payment_history_stats_default_currency(self):
        """Test that currency defaults to USD."""
        from schemas.payment import PaymentHistoryStatsResponse

        data = {
            "total_spent": 0.00,
            "total_payments": 0,
            "successful_payments": 0,
            "failed_payments": 0,
            "pending_payments": 0,
            "refunded_payments": 0,
        }

        schema = PaymentHistoryStatsResponse(**data)
        assert schema.currency == "usd"

    def test_plan_details_contain_limits(self):
        """Test that all plans have proper limits defined."""
        from schemas.payment import PLAN_DETAILS, SubscriptionPlanEnum

        for plan_enum in SubscriptionPlanEnum:
            plan_info = PLAN_DETAILS[plan_enum]
            assert plan_info.project_limit >= 1
            assert plan_info.member_limit >= 1
            assert plan_info.price_monthly >= 0


# ============================================================================
# Webhook Handler Tests
# ============================================================================


class TestWebhookHandlers:
    """Test cases for webhook event handlers."""

    @pytest.mark.asyncio
    async def test_handle_subscription_deleted_downgrades_to_free(self, mock_db, mock_subscription):
        """Test that deleted subscription downgrades user to free."""
        from models.payment import SubscriptionPlan, SubscriptionStatus
        from services.payment_service import PaymentService

        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_subscription
        mock_db.execute.return_value = mock_result

        with patch.object(PaymentService, "__init__", return_value=None):
            service = PaymentService.__new__(PaymentService)
            service._configured = True

            stripe_sub = {"id": "sub_test123456789", "status": "canceled"}

            await service._handle_subscription_deleted(mock_db, stripe_sub)

            # Verify subscription was downgraded
            assert mock_subscription.plan == SubscriptionPlan.FREE
            assert mock_subscription.status == SubscriptionStatus.CANCELED
            mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_payment_failed_records_history(self, mock_db, mock_user):
        """Test that failed payments are recorded in history."""
        from models.payment import PaymentStatus
        from services.payment_service import PaymentService

        # Setup mock for user lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        with patch.object(PaymentService, "__init__", return_value=None):
            service = PaymentService.__new__(PaymentService)
            service._configured = True

            invoice = {
                "id": "in_test123",
                "customer": mock_user.stripe_customer_id,
                "amount_due": 699,  # $6.99 in cents
                "currency": "usd",
                "number": "INV-001",
                "payment_intent": "pi_test123",
                "hosted_invoice_url": "https://invoice.stripe.com/test",
                "last_payment_error": {
                    "code": "card_declined",
                    "message": "Your card was declined",
                },
            }

            await service._handle_payment_failed(mock_db, invoice)

            # Verify payment history was added
            mock_db.add.assert_called_once()
            added_history = mock_db.add.call_args[0][0]
            assert added_history.status == PaymentStatus.FAILED
            assert added_history.failure_code == "card_declined"


# ============================================================================
# Rate Limiter Tests
# ============================================================================


class TestRateLimiter:
    """Test cases for rate limiting configuration."""

    def test_rate_limits_defined_correctly(self):
        """Test that all rate limits are properly defined."""
        from rate_limiter import RateLimits

        # Verify payment limits exist and are strings
        assert isinstance(RateLimits.PAYMENT_SETUP_INTENT, str)
        assert isinstance(RateLimits.PAYMENT_ADD_METHOD, str)
        assert isinstance(RateLimits.PAYMENT_SUBSCRIPTION, str)
        assert isinstance(RateLimits.PAYMENT_DELETE, str)

        # Verify format (X/period)
        assert "/" in RateLimits.PAYMENT_SETUP_INTENT

    def test_rate_limit_values_are_reasonable(self):
        """Test that rate limits have sensible values."""
        from rate_limiter import RateLimits

        # Payment limits should be restrictive (<= 10/minute)
        setup_limit = int(RateLimits.PAYMENT_SETUP_INTENT.split("/")[0])
        assert setup_limit <= 10, "Setup intent limit should be <= 10/minute"

        # Subscription limit
        sub_limit = int(RateLimits.PAYMENT_SUBSCRIPTION.split("/")[0])
        assert sub_limit <= 10, "Subscription limit should be <= 10/minute"


# ============================================================================
# Integration Tests
# ============================================================================


class TestPaymentIntegration:
    """Integration tests for complete payment flows."""

    @pytest.mark.asyncio
    async def test_full_subscription_upgrade_flow(self, mock_db, mock_user):
        """Test complete flow: add card -> subscribe -> upgrade."""
        # This would require more complex mocking of the full Stripe SDK
        # and is marked as a placeholder for CI/CD integration testing
        pass

    @pytest.mark.asyncio
    async def test_downgrade_check_prevents_over_limit(self, mock_db, mock_user):
        """Test that downgrade is blocked when usage exceeds target limits."""
        # Integration test placeholder
        pass
