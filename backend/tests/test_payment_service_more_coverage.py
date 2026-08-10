from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import stripe
from payment_service_test_helpers import (
    configured_stripe_settings,
    make_mock_db_session,
    make_payment_service,
    make_test_user,
)

from models.payment import (
    PaymentHistory,
    PaymentStatus,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from models.webhook_log import WebhookEventLog
from schemas.payment import SubscriptionCreate, SubscriptionPlanEnum


@pytest.fixture
def mock_settings():
    with configured_stripe_settings() as mock:
        yield mock


@pytest.fixture
def mock_db_session():
    return make_mock_db_session()


@pytest.fixture
def payment_service(mock_settings):
    return make_payment_service()


@pytest.fixture
def test_user():
    return make_test_user()


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_process_webhook_payment_failed(payment_service, mock_db_session, test_user):
    event = {
        "id": "evt_fail",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "id": "in_fail",
                "customer": "cus_1",
                "amount_due": 1000,
                "last_payment_error": {"code": "card_declined", "message": "Decline"},
            }
        },
    }

    # Mock user lookup
    mock_db_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # Idempotency check
        MagicMock(scalar_one_or_none=MagicMock(return_value=test_user)),  # User lookup
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # Existing failure lookup
    ]

    test_user.id = uuid4()

    await payment_service.process_webhook(mock_db_session, event)

    # Check that payment history was added with FAILED status
    args = mock_db_session.add.call_args_list
    # First add is webhook log, second is payment history
    assert len(args) >= 2
    # Verify payment history in db.add calls
    history_added = False
    for call in args:
        if isinstance(call[0][0], PaymentHistory):
            history = call[0][0]
            if history.status == PaymentStatus.FAILED:
                assert history.failure_code == "card_declined"
                history_added = True
    assert history_added


@pytest.mark.asyncio
async def test_process_webhook_charge_refunded(payment_service, mock_db_session):
    event = {
        "id": "evt_ref",
        "type": "charge.refunded",
        "data": {
            "object": {"id": "ch_1", "amount_refunded": 500, "amount": 1000, "refunded": False}
        },
    }

    history = PaymentHistory(
        id=uuid4(), stripe_charge_id="ch_1", status=PaymentStatus.SUCCEEDED, amount=10.0
    )

    mock_db_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # Idempotency check
        MagicMock(scalar_one_or_none=MagicMock(return_value=history)),  # History lookup
    ]

    await payment_service.process_webhook(mock_db_session, event)

    assert history.refunded_amount == 5.0
    assert "Partial Refund" in history.description
    assert history.status == PaymentStatus.SUCCEEDED  # Not fully refunded yet


@pytest.mark.asyncio
async def test_process_webhook_subscription_deleted(payment_service, mock_db_session):
    event = {
        "id": "evt_del",
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_stripe"}},
    }

    sub = Subscription(
        id=uuid4(), stripe_subscription_id="sub_stripe", status=SubscriptionStatus.ACTIVE
    )

    mock_db_session.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # Idempotency check
        MagicMock(scalar_one_or_none=MagicMock(return_value=sub)),  # Subscription lookup
    ]

    await payment_service.process_webhook(mock_db_session, event)

    assert sub.status == SubscriptionStatus.CANCELED
    assert sub.plan == SubscriptionPlan.FREE
    assert sub.stripe_subscription_id is None


@pytest.mark.asyncio
async def test_process_webhook_idempotency(payment_service, mock_db_session):
    event = {"id": "evt_exist", "type": "charge.succeeded", "data": {}}

    existing_log = WebhookEventLog(processed=True)

    # Mock finding existing log
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = existing_log

    await payment_service.process_webhook(mock_db_session, event)

    # Should perform NO actions (no add)
    mock_db_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_execute_subscription_update_downgrade_free(
    payment_service, mock_db_session, test_user
):
    existing = Subscription(
        user_id=test_user.id,
        stripe_subscription_id="sub_old",
        plan=SubscriptionPlan.STARTER,
        status=SubscriptionStatus.ACTIVE,
    )

    data = SubscriptionCreate(plan="free")

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:
        await payment_service._execute_subscription_update(
            mock_db_session, test_user.id, data, "cus_1", existing, None, "idem"
        )

        # Should delete stripe subscription
        assert mock_stripe.call_count >= 1
        # Check if the subscription ID was passed
        args = mock_stripe.call_args[0]
        # args[0] is func, args[1] is id if positional, or in kwargs?
        # _run_stripe_cmd(func, *args)
        # stripe.Subscription.delete(sid)
        # So args[1] should be sid
        assert "sub_old" in args or "sub_old" in str(args)
        assert existing.plan == SubscriptionPlan.FREE
        assert existing.stripe_subscription_id is None


@pytest.mark.asyncio
async def test_execute_subscription_update_upgrade_existing(
    payment_service, mock_db_session, test_user
):
    existing = Subscription(
        user_id=test_user.id,
        stripe_subscription_id="sub_1",
        plan=SubscriptionPlan.STARTER,
        status=SubscriptionStatus.ACTIVE,
    )

    from schemas.payment import PLAN_DETAILS

    plan_info = PLAN_DETAILS[SubscriptionPlanEnum.PRO]
    data = SubscriptionCreate(plan="pro", payment_method_id=uuid4())

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:
        # Mock product/price lookup and modify
        # Note: we use regular functions for side_effect to allow AsyncMock to wrap them properly
        def side_effect(func, *args, **kwargs):
            if func == stripe.Product.list:
                return MagicMock(data=[])
            if func == stripe.Product.create:
                return MagicMock(id="prod_1")
            if func == stripe.Price.list:
                return MagicMock(data=[])
            if func == stripe.Price.create:
                return MagicMock(id="price_1")
            if func == stripe.Subscription.retrieve:
                # Return dict with inner Mock to support sub['items']['data'][0].id
                return {"items": {"data": [MagicMock(id="item_1")]}}
            if func == stripe.Subscription.modify:
                return MagicMock(id="sub_1", current_period_end=1700000000)
            return MagicMock()

        mock_stripe.side_effect = side_effect

        # Need to mock get_payment_method
        payment_service.get_payment_method = AsyncMock(
            return_value=MagicMock(stripe_payment_method_id="pm_s")
        )

        await payment_service._execute_subscription_update(
            mock_db_session, test_user.id, data, "cus_1", existing, plan_info, "idem"
        )

        assert existing.plan == SubscriptionPlan.PRO
        assert existing.price_amount == plan_info.price_monthly
