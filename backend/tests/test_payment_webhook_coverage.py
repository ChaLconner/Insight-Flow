from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.payment import (
    PaymentHistory,
    PaymentMethod,
    PaymentStatus,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from models.webhook_log import WebhookEventLog
from services.payment_service import PaymentService


# Mock stripe
@pytest.fixture
def mock_stripe():
    with patch("services.payment_service.stripe") as mock:
        yield mock


@pytest.fixture
def payment_service(async_session):
    return PaymentService()


@pytest.mark.asyncio
async def test_process_webhook_idempotency(payment_service, async_session, mock_stripe):
    # Setup - Create existing log
    event_id = "evt_existing"
    existing_log = WebhookEventLog(
        stripe_event_id=event_id, event_type="test_event", processed=True
    )
    async_session.add(existing_log)
    await async_session.commit()

    event = {"id": event_id, "type": "test_event", "data": {"object": {}}}

    # Act
    with patch.object(
        payment_service, "_handle_subscription_updated", new_callable=AsyncMock
    ) as mock_handler:
        await payment_service.process_webhook(async_session, event)
        mock_handler.assert_not_called()


@pytest.mark.asyncio
async def test_process_webhook_duplicate_processing(payment_service, async_session, mock_stripe):
    # Test case where log exists but processed=False (retry logic)
    event_id = "evt_retry"
    existing_log = WebhookEventLog(
        stripe_event_id=event_id,
        event_type="customer.subscription.updated",
        processed=False,
        retry_count=0,
    )
    async_session.add(existing_log)
    await async_session.commit()

    event = {
        "id": event_id,
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_123"}},
    }

    with patch.object(
        payment_service, "_handle_subscription_updated", new_callable=AsyncMock
    ) as mock_handler:
        await payment_service.process_webhook(async_session, event)
        mock_handler.assert_called_once()

    await async_session.refresh(existing_log)
    assert existing_log.retry_count == 1
    assert existing_log.processed is True


@pytest.mark.asyncio
async def test_handle_subscription_updated_not_found(payment_service, async_session):
    # Act
    result = await payment_service._handle_subscription_updated(
        async_session, {"id": "sub_unknown"}
    )
    # Should just return logging warning, no crash
    assert result is None


@pytest.mark.asyncio
async def test_handle_subscription_updated_downgrade(payment_service, async_session, test_user):
    # Setup
    sub = Subscription(
        user_id=test_user.id,
        stripe_subscription_id="sub_cancel",
        plan=SubscriptionPlan.PRO,
        status=SubscriptionStatus.ACTIVE,
    )
    async_session.add(sub)
    await async_session.commit()

    # Act - downgrade
    data = {"id": "sub_cancel", "status": "canceled"}
    await payment_service._handle_subscription_updated(async_session, data)
    await async_session.commit()

    # Assert
    await async_session.refresh(sub)
    assert sub.plan == SubscriptionPlan.FREE
    assert sub.status == SubscriptionStatus.CANCELED


@pytest.mark.asyncio
async def test_handle_subscription_updated_incomplete_expired_downgrades(
    payment_service, async_session, test_user
):
    sub = Subscription(
        user_id=test_user.id,
        stripe_subscription_id="sub_expired",
        plan=SubscriptionPlan.PRO,
        status=SubscriptionStatus.INCOMPLETE,
    )
    async_session.add(sub)
    await async_session.commit()

    await payment_service._handle_subscription_updated(
        async_session, {"id": "sub_expired", "status": "incomplete_expired"}
    )
    await async_session.commit()
    await async_session.refresh(sub)

    assert sub.plan == SubscriptionPlan.FREE
    assert sub.status == SubscriptionStatus.INCOMPLETE_EXPIRED


@pytest.mark.asyncio
async def test_handle_subscription_deleted(payment_service, async_session, test_user):
    # Setup
    sub = Subscription(
        user_id=test_user.id,
        stripe_subscription_id="sub_del",
        plan=SubscriptionPlan.PRO,
        status=SubscriptionStatus.ACTIVE,
    )
    async_session.add(sub)
    await async_session.commit()

    # Act
    data = {"id": "sub_del"}
    await payment_service._handle_subscription_deleted(async_session, data)
    await async_session.commit()

    # Assert
    await async_session.refresh(sub)
    assert sub.plan == SubscriptionPlan.FREE
    assert sub.status == SubscriptionStatus.CANCELED
    assert sub.stripe_subscription_id is None


@pytest.mark.asyncio
async def test_handle_payment_succeeded_success(payment_service, async_session, test_user):
    # Setup user stripe id
    test_user.stripe_customer_id = "cus_test"
    async_session.add(test_user)

    # Setup Subscription
    sub_id = "sub_pay"
    sub = Subscription(
        user_id=test_user.id, stripe_subscription_id=sub_id, plan=SubscriptionPlan.PRO
    )
    async_session.add(sub)
    await async_session.commit()

    # Data
    data = {
        "customer": "cus_test",
        "amount_paid": 2000,
        "subscription": sub_id,
        "id": "in_test",
        "currency": "usd",
        "status": "paid",
    }

    # Act
    await payment_service._handle_payment_succeeded(async_session, data)

    # Assert
    from sqlalchemy import select

    res = await async_session.execute(
        select(PaymentHistory).where(PaymentHistory.stripe_invoice_id == "in_test")
    )
    history = res.scalar_one_or_none()

    assert history is not None
    assert history.amount == 20.0
    assert history.status == PaymentStatus.SUCCEEDED


@pytest.mark.asyncio
async def test_handle_payment_failed(payment_service, async_session, test_user):
    test_user.stripe_customer_id = "cus_fail"
    async_session.add(test_user)
    await async_session.commit()

    data = {
        "customer": "cus_fail",
        "amount_due": 2000,
        "id": "in_fail",
        "currency": "usd",
        "last_payment_error": {"code": "card_declined", "message": "Decline"},
    }

    await payment_service._handle_payment_failed(async_session, data)

    from sqlalchemy import select

    res = await async_session.execute(
        select(PaymentHistory).where(PaymentHistory.stripe_invoice_id == "in_fail")
    )
    history = res.scalar_one_or_none()

    assert history is not None
    assert history.status == PaymentStatus.FAILED
    assert history.failure_code == "card_declined"


@pytest.mark.asyncio
async def test_payment_stats_use_net_refunds_and_success_currency(
    payment_service, async_session, test_user
):
    async_session.add_all(
        [
            PaymentHistory(
                user_id=test_user.id,
                stripe_invoice_id="in_stats_success",
                amount=100,
                refunded_amount=30,
                currency="usd",
                status=PaymentStatus.SUCCEEDED,
            ),
            PaymentHistory(
                user_id=test_user.id,
                stripe_invoice_id="in_stats_failed",
                amount=500,
                currency="eur",
                status=PaymentStatus.FAILED,
            ),
        ]
    )
    await async_session.commit()

    stats = await payment_service.get_payment_history_stats(async_session, test_user.id)

    assert stats["total_spent"] == 70.0
    assert stats["currency"] == "usd"


@pytest.mark.asyncio
async def test_payment_succeeded_promotes_existing_invoice_failure(
    payment_service, async_session, test_user
):
    test_user.stripe_customer_id = "cus_promote"
    async_session.add(test_user)
    existing = PaymentHistory(
        user_id=test_user.id,
        stripe_invoice_id="in_promote",
        amount=20,
        currency="usd",
        status=PaymentStatus.FAILED,
        failure_code="card_declined",
    )
    async_session.add(existing)
    await async_session.commit()

    await payment_service._handle_payment_succeeded(
        async_session,
        {
            "customer": "cus_promote",
            "amount_paid": 2000,
            "id": "in_promote",
            "currency": "usd",
        },
    )
    await async_session.commit()

    await async_session.refresh(existing)
    assert existing.status == PaymentStatus.SUCCEEDED
    assert existing.amount == 20
    assert existing.failure_code is None


@pytest.mark.asyncio
async def test_handle_payment_method_detached(payment_service, async_session, test_user):
    pm = PaymentMethod(
        user_id=test_user.id,
        stripe_payment_method_id="pm_detach",
        is_active=True,
        # Correct fields for PaymentMethod model
        card_brand="visa",
        card_last4="4242",
        card_exp_month=12,
        card_exp_year=2030,
        stripe_customer_id="cus_detach",
    )
    async_session.add(pm)
    await async_session.commit()

    data = {"id": "pm_detach"}
    await payment_service._handle_payment_method_detached(async_session, data)
    await async_session.commit()

    await async_session.refresh(pm)
    assert pm.is_active is False


@pytest.mark.asyncio
async def test_record_invoice_payment_duplicate(payment_service, async_session, test_user):
    # First create a history record
    hist = PaymentHistory(
        user_id=test_user.id, stripe_invoice_id="in_dup", amount=10, status=PaymentStatus.SUCCEEDED
    )
    async_session.add(hist)
    await async_session.commit()

    # Mock invoice object
    invoice = MagicMock()
    invoice.status = "paid"
    invoice.amount_paid = 1000
    invoice.id = "in_dup"

    # Act
    await payment_service._record_invoice_payment(async_session, test_user.id, None, invoice)

    # Assert
    # Just ensure no exception and no new record
    from sqlalchemy import func, select

    res = await async_session.execute(
        select(func.count())
        .select_from(PaymentHistory)
        .where(PaymentHistory.stripe_invoice_id == "in_dup")
    )
    count = res.scalar()
    assert count == 1
