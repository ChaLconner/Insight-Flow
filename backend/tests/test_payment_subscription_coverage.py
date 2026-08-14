from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import stripe

from models.payment import PaymentMethod, Subscription, SubscriptionPlan, SubscriptionStatus
from schemas.payment import SubscriptionCreate, SubscriptionPlanEnum
from services.payment_service import PaymentService


@pytest.fixture
def payment_service():
    service = PaymentService()
    # Mock configuration check - must set _configured to True to test business logic
    service._configured = True
    return service


@pytest.fixture
def mock_stripe():
    with patch("services.payment_service.stripe") as mock:
        mock.error = stripe.error
        yield mock


@pytest.mark.asyncio
async def test_create_subscription_missing_payment_method(
    payment_service, async_session, test_user
):
    data = SubscriptionCreate(plan=SubscriptionPlanEnum.PRO)

    with pytest.raises(ValueError, match="A payment method is required"):
        await payment_service.create_or_update_subscription(
            async_session, test_user.id, data, "cus_test"
        )


@pytest.mark.asyncio
async def test_create_subscription_stripe_setup_error(
    payment_service, async_session, test_user, mock_stripe
):
    # Setup payment method
    pm = PaymentMethod(
        user_id=test_user.id,
        stripe_payment_method_id="pm_test",
        is_active=True,
        is_default=True,
        card_brand="visa",
        card_last4="4242",
        card_exp_month=12,
        card_exp_year=2030,
        stripe_customer_id="cus_test",
    )
    async_session.add(pm)
    await async_session.commit()

    # Mock stripe product list to fail or return empty then create fail
    mock_stripe.Product.list.side_effect = stripe.error.StripeError("Connection error")

    data = SubscriptionCreate(plan=SubscriptionPlanEnum.PRO)

    with pytest.raises(ValueError, match="Failed to set up subscription"):
        await payment_service.create_or_update_subscription(
            async_session, test_user.id, data, "cus_test"
        )


@pytest.mark.asyncio
async def test_resume_subscription_not_found(payment_service, async_session, test_user):
    with pytest.raises(ValueError, match="No subscription found"):
        await payment_service.resume_subscription(async_session, test_user.id)


@pytest.mark.asyncio
async def test_resume_subscription_free_plan(payment_service, async_session, test_user):
    sub = Subscription(
        user_id=test_user.id, plan=SubscriptionPlan.FREE, status=SubscriptionStatus.ACTIVE
    )
    async_session.add(sub)
    await async_session.commit()

    with pytest.raises(ValueError, match="Cannot resume a free"):
        await payment_service.resume_subscription(async_session, test_user.id)


@pytest.mark.asyncio
async def test_resume_subscription_invalid_status(payment_service, async_session, test_user):
    sub = Subscription(
        user_id=test_user.id,
        plan=SubscriptionPlan.PRO,
        stripe_subscription_id="sub_test",
        status=SubscriptionStatus.CANCELED,  # Already canceled fully
    )
    async_session.add(sub)
    await async_session.commit()

    with pytest.raises(ValueError, match="Cannot resume subscription with status"):
        await payment_service.resume_subscription(async_session, test_user.id)


@pytest.mark.asyncio
async def test_resume_subscription_stripe_error(
    payment_service, async_session, test_user, mock_stripe
):
    sub = Subscription(
        user_id=test_user.id,
        plan=SubscriptionPlan.PRO,
        stripe_subscription_id="sub_test",
        status=SubscriptionStatus.ACTIVE,
        cancel_at_period_end=True,
    )
    async_session.add(sub)
    await async_session.commit()

    mock_stripe.Subscription.modify.side_effect = stripe.error.InvalidRequestError("Err", "param")

    with pytest.raises(ValueError, match="Failed to resume subscription with payment provider"):
        await payment_service.resume_subscription(async_session, test_user.id)


@pytest.mark.asyncio
async def test_resume_subscription_unknown_stripe_status_fails_closed(
    payment_service, async_session, test_user
):
    sub = Subscription(
        user_id=test_user.id,
        plan=SubscriptionPlan.PRO,
        stripe_subscription_id="sub_test",
        status=SubscriptionStatus.ACTIVE,
        cancel_at_period_end=True,
    )
    async_session.add(sub)
    await async_session.commit()

    stripe_sub = MagicMock(status="future_provider_status")
    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as run_stripe:
        run_stripe.return_value = stripe_sub

        result = await payment_service.resume_subscription(async_session, test_user.id)

    assert result is not None
    assert result.cancel_at_period_end is False
    assert result.status == SubscriptionStatus.INCOMPLETE
