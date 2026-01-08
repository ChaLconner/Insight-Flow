from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import stripe
from sqlalchemy.exc import IntegrityError

from models.payment import (
    PaymentMethod,
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from models.user import User
from schemas.payment import PaymentMethodCreate, SubscriptionCreate, SubscriptionPlanEnum
from services.payment_service import PaymentService


# Fixtures
@pytest.fixture
def mock_settings():
    with patch("services.payment_service.get_settings") as mock:
        mock.return_value.stripe.is_configured = True
        mock.return_value.stripe.secret_key = "sk_test_123"
        yield mock


@pytest.fixture
def mock_db_session():
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=MagicMock())
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock()
    mock.add = MagicMock()
    mock.add_all = MagicMock()
    mock.rollback = AsyncMock()
    return mock


@pytest.fixture
def payment_service(mock_settings):
    return PaymentService()


@pytest.fixture
def test_user():
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    return user


@pytest.mark.asyncio
async def test_get_or_create_customer_no_such_customer_error(payment_service, mock_db_session):
    user_id = uuid4()
    email = "test@example.com"
    user = MagicMock()
    user.stripe_customer_id = "cus_stale"

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:

        def side_effect(func, *args, **kwargs):
            if func == stripe.Customer.retrieve:
                raise stripe.error.InvalidRequestError("No such customer", "id")
            if func == stripe.Customer.create:
                return MagicMock(id="cus_new")
            if func == stripe.Customer.list:
                return MagicMock(data=[])
            return MagicMock()

        mock_stripe.side_effect = side_effect

        customer_id = await payment_service.get_or_create_stripe_customer(
            mock_db_session, user_id, email, user=user
        )
        assert customer_id == "cus_new"


@pytest.mark.asyncio
async def test_resume_subscription_errors(payment_service, mock_db_session):
    user_id = uuid4()
    payment_service.get_subscription = AsyncMock(return_value=None)
    with patch("services.payment_service.payment_lock") as mock_lock:
        mock_lock.return_value.__aenter__.return_value = None
        with pytest.raises(ValueError, match="No subscription found"):
            await payment_service.resume_subscription(mock_db_session, user_id)


@pytest.mark.asyncio
async def test_webhook_duplicate_payment_error(payment_service, mock_db_session):
    invoice = {
        "id": "in_1",
        "customer": "c",
        "amount_paid": 10,
        "subscription": "s",
        "status": "paid",
    }
    mock_db_session.execute.side_effect = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
    mock_db_session.commit.side_effect = IntegrityError("Dup", "p", "o")
    await payment_service._handle_payment_succeeded(mock_db_session, invoice)
    mock_db_session.rollback.assert_called()


@pytest.mark.asyncio
async def test_get_or_create_customer_search_by_email(payment_service, mock_db_session, test_user):
    test_user.stripe_customer_id = None
    mock_list_result = MagicMock()
    mock_list_result.data = [MagicMock(id="cus_found")]

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:

        def side_effect(func, *args, **kwargs):
            if func == stripe.Customer.list:
                return mock_list_result
            return MagicMock()

        mock_stripe.side_effect = side_effect

        # Mock initial db lookups to return None so it falls through to search
        # 1. User lookup (if user_id provided to get_or_create) - skipped if provided object has it?
        # test_user passed in has stripe_customer_id=None.
        # But get_or_create also checks db for user, subscription, payment_method.
        # We need db.execute to return None for those 3 queries.
        # Then search happens.

        # NOTE: mock_db_session.execute returns MagicMock by default (set in fixture).
        # We need it to return None explicitly for the first few calls?
        # OR we can just return None for EVERYTHING except the search which doesn't use db.
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        customer_id = await payment_service.get_or_create_stripe_customer(
            mock_db_session, test_user.id, "email", "Name", test_user
        )
        assert customer_id == "cus_found"


@pytest.mark.asyncio
async def test_create_setup_intent_stale_customer_retry(payment_service, mock_db_session):
    user_id = uuid4()

    with (
        patch("services.payment_service.generate_setup_intent_key", return_value="key"),
        patch.object(
            payment_service,
            "get_or_create_stripe_customer",
            new=AsyncMock(return_value="cus_stale"),
        ),
        patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe,
    ):

        def side_effect(func, *args, **kwargs):
            if func == stripe.SetupIntent.create:
                if kwargs.get("customer") == "cus_stale":
                    raise stripe.error.InvalidRequestError("No such customer", "param")
                return MagicMock(client_secret="sec", customer="cus_new")
            if func == stripe.Customer.create:
                return MagicMock(id="cus_new")
            return MagicMock()

        mock_stripe.side_effect = side_effect

        response = await payment_service.create_setup_intent(mock_db_session, user_id, "email")

        assert response.customer_id == "cus_new"


@pytest.mark.asyncio
async def test_attach_payment_method_commit_fail(payment_service, mock_db_session, test_user):
    # Added optional fields to pass validation
    pm_create = PaymentMethodCreate(
        payment_method_id="pm_123", set_as_default=False, billing_name="Test", customer_id="cus_1"
    )

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:
        mock_stripe.return_value = MagicMock(
            customer=None, card=MagicMock(brand="Visa", last4="4242")
        )
        mock_db_session.commit.side_effect = Exception("DB Fail")

        with patch("services.payment_service.security_logger"):
            with pytest.raises(Exception, match="DB Fail"):
                await payment_service.attach_payment_method(
                    mock_db_session, test_user.id, pm_create, "cus_1"
                )


@pytest.mark.asyncio
async def test_delete_payment_method_success(payment_service, mock_db_session, test_user):
    pm = PaymentMethod(
        id=uuid4(),
        user_id=test_user.id,
        stripe_payment_method_id="pm_del",
        is_active=True,
        is_default=False,
    )
    payment_service.get_payment_method = AsyncMock(return_value=pm)
    payment_service.list_payment_methods = AsyncMock(return_value=[])

    with (
        patch("services.payment_service.payment_lock") as mock_lock,
        patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock),
    ):
        mock_lock.return_value.__aenter__.return_value = None
        result = await payment_service.delete_payment_method(mock_db_session, pm.id, test_user.id)
        assert result is True


@pytest.mark.asyncio
async def test_execute_subscription_update_create_product_price(
    payment_service, mock_db_session, test_user
):
    payment_service.get_payment_method = AsyncMock(
        return_value=MagicMock(stripe_payment_method_id="pm_1")
    )

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:

        def side_effect(func, *args, **kwargs):
            if func == stripe.Product.list:
                return MagicMock(data=[])
            if func == stripe.Product.create:
                return MagicMock(id="prod_new")
            if func == stripe.Price.list:
                return MagicMock(data=[])
            if func == stripe.Price.create:
                return MagicMock(id="price_new")
            if func == stripe.Subscription.modify:
                return MagicMock(id="sub_updated", latest_invoice=MagicMock(id="inv_1"))
            return MagicMock()

        mock_stripe.side_effect = side_effect

        existing = Subscription(
            user_id=test_user.id,
            stripe_subscription_id="sub_ex",
            plan=SubscriptionPlan.STARTER,
            status=SubscriptionStatus.ACTIVE,
        )

        from services.payment_service import PLAN_DETAILS

        plan_info = PLAN_DETAILS[SubscriptionPlanEnum.PRO]

        data = SubscriptionCreate(plan="pro", payment_method_id=uuid4())

        await payment_service._execute_subscription_update(
            mock_db_session, test_user.id, data, "cus_1", existing, plan_info, "idemkey"
        )

        assert mock_stripe.call_count >= 1


@pytest.mark.asyncio
async def test_list_payment_methods(payment_service, mock_db_session):
    user_id = uuid4()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [PaymentMethod(id=uuid4())]
    mock_db_session.execute.return_value = mock_result

    res = await payment_service.list_payment_methods(mock_db_session, user_id)
    assert len(res) == 1


@pytest.mark.asyncio
async def test_set_default_payment_method_updates_subscription(payment_service, mock_db_session):
    user_id = uuid4()
    pm_id = uuid4()
    pm = PaymentMethod(
        id=pm_id,
        user_id=user_id,
        stripe_payment_method_id="pm_stripe",
        is_default=False,
        stripe_customer_id="cus_1",
    )

    sub = Subscription(
        user_id=user_id, stripe_subscription_id="sub_1", status=SubscriptionStatus.ACTIVE
    )

    payment_service.get_payment_method = AsyncMock(return_value=pm)
    payment_service.get_subscription = AsyncMock(return_value=sub)

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:
        await payment_service.set_default_payment_method(mock_db_session, pm_id, user_id)
        assert mock_stripe.call_count >= 1
        assert pm.is_default is True
