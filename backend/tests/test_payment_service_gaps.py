"""
Additional tests for Payment Service to cover edge cases and error handling.
Focuses on _record_invoice_payment exceptions and cancel_subscription variations.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from models.payment import (
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from services.payment_service import PaymentService


@pytest.fixture
def mock_payment_service():
    service = PaymentService()
    # Mock configuration check - must set _configured to True
    service._configured = True
    return service


@pytest.fixture
def mock_db_session():
    session = AsyncMock()

    # db.add is synchronous
    session.add = MagicMock()

    # db.commit and rollback are async
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    # execute is async (awaited), so its return_value is the Result object.
    # The Result object methods (scalar_one_or_none) are synchronous.
    result_mock = MagicMock()
    session.execute.return_value = result_mock
    result_mock.scalar_one_or_none.return_value = None
    return session


@pytest.mark.asyncio
async def test_record_invoice_payment_duplicate_integrity_error(
    mock_payment_service, mock_db_session
):
    """Test _record_invoice_payment handles IntegrityError gracefully (idempotency)."""
    user_id = uuid4()
    sub_id = uuid4()
    invoice_mock = MagicMock()
    invoice_mock.get.return_value = "inv_123"
    invoice_mock.id = "inv_123"
    invoice_mock.status = "paid"
    invoice_mock.amount_paid = 1000
    invoice_mock.currency = "usd"
    invoice_mock.payment_intent = "pi_123"
    invoice_mock.charge = "ch_123"
    invoice_mock.description = "Test Invoice"
    invoice_mock.hosted_invoice_url = "http://url"
    invoice_mock.receipt_url = "http://receipt"

    # Mock db.add to raise IntegrityError
    # We simulate IntegrityError by raising an Exception with matching str or type name
    # Since we can't easily import sqlalchemy IntegrityError without dependency, we use generic exception with message
    mock_db_session.add.side_effect = Exception("unique constraint violation")

    await mock_payment_service._record_invoice_payment(
        mock_db_session, user_id, sub_id, invoice_mock
    )

    # Should rollback and log (no crash)
    mock_db_session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_subscription_immediately(mock_payment_service, mock_db_session):
    """Test canceling subscription immediately."""
    user_id = uuid4()
    subscription = Subscription(
        id=uuid4(),
        user_id=user_id,
        stripe_subscription_id="sub_123",
        status=SubscriptionStatus.ACTIVE,
        plan=SubscriptionPlan.PRO,
    )
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = subscription

    with patch.object(
        mock_payment_service, "_run_stripe_cmd", new_callable=AsyncMock
    ) as mock_stripe:
        result = await mock_payment_service.cancel_subscription(
            mock_db_session, user_id, cancel_immediately=True
        )

        # Verify Stripe delete called
        assert mock_stripe.call_count == 1
        args, _ = mock_stripe.call_args
        # stripe.Subscription.delete is passed as first arg
        assert args[1] == "sub_123"

        # Verify local update
        assert result.status == SubscriptionStatus.CANCELED
        assert result.plan == SubscriptionPlan.FREE
        assert result.price_amount == Decimal(0)


@pytest.mark.asyncio
async def test_cancel_subscription_at_period_end(mock_payment_service, mock_db_session):
    """Test canceling subscription at period end."""
    user_id = uuid4()
    subscription = Subscription(
        id=uuid4(),
        user_id=user_id,
        stripe_subscription_id="sub_123",
        status=SubscriptionStatus.ACTIVE,
        plan=SubscriptionPlan.PRO,
        cancel_at_period_end=False,
    )
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = subscription

    with patch.object(
        mock_payment_service, "_run_stripe_cmd", new_callable=AsyncMock
    ) as mock_stripe:
        result = await mock_payment_service.cancel_subscription(
            mock_db_session, user_id, cancel_immediately=False
        )

        # Verify Stripe modify called
        assert mock_stripe.call_count == 1
        # Check kwargs
        _, kwargs = mock_stripe.call_args
        assert kwargs["cancel_at_period_end"] is True

        # Verify local update - status NOT changed yet
        assert result.cancel_at_period_end is True
        # Plan should stay same until webhook
        assert result.plan == SubscriptionPlan.PRO


@pytest.mark.asyncio
async def test_resume_subscription_success(mock_payment_service, mock_db_session):
    """Test resume subscription logic."""
    user_id = uuid4()
    subscription = Subscription(
        id=uuid4(),
        user_id=user_id,
        stripe_subscription_id="sub_123",
        status=SubscriptionStatus.ACTIVE,
        cancel_at_period_end=True,
    )
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = subscription

    mock_stripe_sub = MagicMock()
    mock_stripe_sub.status = "active"

    with patch.object(
        mock_payment_service, "_run_stripe_cmd", new_callable=AsyncMock
    ) as mock_stripe:
        mock_stripe.return_value = mock_stripe_sub

        result = await mock_payment_service.resume_subscription(mock_db_session, user_id)

        assert mock_stripe.call_count == 1
        _, kwargs = mock_stripe.call_args
        assert kwargs["cancel_at_period_end"] is False

        assert result.cancel_at_period_end is False
        assert result.status == SubscriptionStatus.ACTIVE
