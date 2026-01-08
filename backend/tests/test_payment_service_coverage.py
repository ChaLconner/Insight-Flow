from datetime import datetime
from decimal import Decimal
from unittest.mock import ANY as Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import stripe

from models.payment import PaymentMethod, Subscription, SubscriptionPlan, SubscriptionStatus
from schemas.payment import SubscriptionPlanEnum
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
    mock.execute = AsyncMock()
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock()
    return mock


@pytest.fixture
def payment_service(mock_settings):
    return PaymentService()


@pytest.mark.asyncio
async def test_initialization_not_configured():
    with patch("services.payment_service.get_settings") as mock_settings:
        mock_settings.return_value.stripe.is_configured = False
        service = PaymentService()
        assert service.is_configured is False

        with pytest.raises(ValueError, match="Stripe is not configured"):
            service._check_configured()


@pytest.mark.asyncio
async def test_get_or_create_customer_cached_on_user(payment_service, mock_db_session):
    user_id = uuid4()
    email = "test@example.com"

    # User object with cached ID
    user = MagicMock()
    user.stripe_customer_id = "cus_cached_123"

    # Mock Stripe retrieval to succeed
    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:
        customer = await payment_service.get_or_create_stripe_customer(
            mock_db_session, user_id, email, user=user
        )

        assert customer == "cus_cached_123"
        # Should verify against Stripe
        mock_stripe.assert_called_with(stripe.Customer.retrieve, "cus_cached_123")


@pytest.mark.asyncio
async def test_get_or_create_customer_create_new(payment_service, mock_db_session):
    user_id = uuid4()
    email = "new@example.com"

    # DB returns no user/sub/pm
    res = MagicMock()
    res.scalar_one_or_none.return_value = None
    res.data = []  # For list search
    mock_db_session.execute.return_value = res

    # Mock Stripe
    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:
        # Search returns empty
        mock_stripe.side_effect = [
            None,  # Search by email (list) - wait, logic is _run_stripe_cmd(stripe.Customer.list...)
            # returns search_result object
            MagicMock(id="cus_new_123"),  # Create result
        ]

        # Configure search result mock
        search_result = MagicMock()
        search_result.data = []

        # We need to be careful about side_effect sequence:
        # 1. Customer.list (search by email)
        # 2. Customer.create

        def stripe_side_effect(func, *args, **kwargs):
            if func == stripe.Customer.list:
                return search_result
            if func == stripe.Customer.create:
                return MagicMock(id="cus_new_123")
            return None

        mock_stripe.side_effect = stripe_side_effect

        customer_id = await payment_service.get_or_create_stripe_customer(
            mock_db_session, user_id, email
        )

        assert customer_id == "cus_new_123"
        # Should persist to DB
        mock_db_session.execute.assert_called()
        mock_db_session.commit.assert_called()


@pytest.mark.asyncio
async def test_create_setup_intent_success(payment_service, mock_db_session):
    user_id = uuid4()
    email = "test@example.com"

    # Mock get_or_create_stripe_customer to simple return
    payment_service.get_or_create_stripe_customer = AsyncMock(return_value="cus_123")

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:
        mock_intent = MagicMock()
        mock_intent.client_secret = "seti_secret_123"
        mock_stripe.return_value = mock_intent

        resp = await payment_service.create_setup_intent(mock_db_session, user_id, email)

        assert resp.client_secret == "seti_secret_123"
        assert resp.customer_id == "cus_123"


@pytest.mark.asyncio
async def test_create_setup_intent_retry_invalid_customer(payment_service, mock_db_session):
    user_id = uuid4()
    email = "test@example.com"

    payment_service.get_or_create_stripe_customer = AsyncMock(return_value="cus_invalid")

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:
        # Fail first time, succeed second time (create customer -> create intent)

        # We need to simulate the sequence of calls:
        # 1. SetupIntent.create -> Raise InvalidRequestError
        # 2. Customer.create -> Return new customer
        # 3. SetupIntent.create -> Return success

        new_customer = MagicMock(id="cus_new_123")
        success_intent = MagicMock(client_secret="seti_new_secret")

        # Side effect to handle different calls
        def side_effect(func, *args, **kwargs):
            if func == stripe.SetupIntent.create:
                if kwargs.get("customer") == "cus_invalid":
                    raise stripe.error.InvalidRequestError("No such customer", "customer")
                return success_intent
            if func == stripe.Customer.create:
                return new_customer
            return None

        mock_stripe.side_effect = side_effect

        resp = await payment_service.create_setup_intent(mock_db_session, user_id, email)

        assert resp.customer_id == "cus_new_123"
        assert resp.client_secret == "seti_new_secret"

        # Verify clean up calls
        assert mock_db_session.execute.call_count >= 3  # Update sub, delete pm, update user


@pytest.mark.asyncio
async def test_attach_payment_method(payment_service, mock_db_session):
    user_id = uuid4()
    customer_id = "cus_123"
    pm_data = MagicMock()
    pm_data.payment_method_id = "pm_123"
    pm_data.set_as_default = True
    pm_data.billing_address = None
    pm_data.billing_name = "Test User"
    pm_data.billing_email = "test@example.com"
    pm_data.billing_phone = None

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:
        # Mock Stripe PM retrieval
        stripe_pm = MagicMock()
        stripe_pm.customer = None  # Not attached yet
        stripe_pm.card.brand = "visa"
        stripe_pm.card.last4 = "4242"
        # ... other card fields defaults
        stripe_pm.billing_details.name = "Stripe Name"

        mock_stripe.side_effect = [
            stripe_pm,  # Retrieve
            None,  # Attach
            None,  # Modify Customer (set default)
        ]

        result = await payment_service.attach_payment_method(
            mock_db_session, user_id, pm_data, customer_id
        )

        assert result.stripe_payment_method_id == "pm_123"
        assert result.is_default is True
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_payment_method_soft_delete(payment_service, mock_db_session):
    user_id = uuid4()
    pm_id = uuid4()

    # Mock existing PM
    pm = PaymentMethod(
        id=pm_id, user_id=user_id, stripe_payment_method_id="pm_strip_1", is_default=False
    )

    res = MagicMock()
    res.scalar_one_or_none.return_value = pm
    mock_db_session.execute.return_value = res

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:
        # Mock payment lock
        with patch("services.payment_service.payment_lock") as mock_lock:
            mock_lock.return_value.__aenter__.return_value = None

            result = await payment_service.delete_payment_method(mock_db_session, pm_id, user_id)

            assert result is True
            assert pm.is_active is False

            # Verify call arguments loosely to avoid function object mismatch
            assert mock_stripe.called
            args, _ = mock_stripe.call_args
            assert args[1] == "pm_strip_1"  # Check the ID is passed correctly
            mock_db_session.commit.assert_called()


@pytest.mark.asyncio
async def test_create_subscription_paid_new(payment_service, mock_db_session):
    user_id = uuid4()
    customer_id = "cus_123"
    data = MagicMock()
    data.plan = SubscriptionPlanEnum.PRO
    data.payment_method_id = "pm_card_123"

    # Mock locking and existing sub
    with patch("services.payment_service.payment_lock") as mock_lock:
        mock_lock.return_value.__aenter__.return_value = None

        # Mock DB Payment Method Retrieval
        pm_mock = MagicMock()
        pm_mock.stripe_payment_method_id = "pm_stripe_123"
        payment_service.get_payment_method = AsyncMock(return_value=pm_mock)

        # PaymentService.get_subscription -> None (New sub)
        payment_service.get_subscription = AsyncMock(return_value=None)

        with patch.object(
            payment_service, "_run_stripe_cmd", new_callable=AsyncMock
        ) as mock_stripe:
            # Mock Stripe Create Sub
            mock_sub = MagicMock()
            mock_sub.id = "sub_stripe_123"
            mock_sub.status = "active"
            mock_sub.current_period_end = 1700000000
            mock_sub.current_period_start = 1600000000
            mock_sub.cancel_at_period_end = False

            mock_stripe.return_value = mock_sub

            result = await payment_service.create_or_update_subscription(
                mock_db_session, user_id, data, customer_id
            )

            assert result.plan == SubscriptionPlan.PRO
            assert result.stripe_subscription_id == "sub_stripe_123"
            mock_db_session.add.assert_called()
            mock_db_session.commit.assert_called()


@pytest.mark.asyncio
async def test_payment_history_stats(payment_service, mock_db_session):
    user_id = uuid4()

    # Mock raw SQL result
    row = MagicMock()
    row.total_spent = Decimal("100.50")
    row.total_payments = 5
    row.successful_payments = 4
    row.failed_payments = 1
    row.pending_payments = 0
    row.refunded_payments = 0

    mock_res = MagicMock()
    mock_res.fetchone.return_value = row
    mock_db_session.execute.return_value = mock_res

    stats = await payment_service.get_payment_history_stats(mock_db_session, user_id)

    assert stats["total_spent"] == 100.50
    assert stats["total_payments"] == 5
    assert stats["successful_payments"] == 4
    assert stats["failed_payments"] == 1


@pytest.mark.asyncio
async def test_list_payment_history_filters(payment_service, mock_db_session):
    user_id = uuid4()

    # Mock result items
    items = [MagicMock(), MagicMock()]
    mock_res_items = MagicMock()
    mock_res_items.scalars.return_value.all.return_value = items

    # Mock count result
    mock_res_count = MagicMock()
    mock_res_count.scalar.return_value = 10

    mock_db_session.execute.side_effect = [mock_res_count, mock_res_items]

    # Test with filters
    items_Res, total = await payment_service.list_payment_history(
        mock_db_session, user_id, status_filter="succeeded", start_date=datetime.now()
    )

    assert len(items_Res) == 2
    assert total == 10
    assert mock_db_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_set_default_payment_method(payment_service, mock_db_session):
    user_id = uuid4()
    pm_id = uuid4()

    # Mock get PM
    pm = MagicMock()
    pm.id = pm_id
    pm.is_default = False
    pm.stripe_payment_method_id = "pm_stripe_1"
    pm.stripe_customer_id = "cus_1"

    # Mock get sub (active)
    sub = MagicMock()
    sub.status = SubscriptionStatus.ACTIVE
    sub.stripe_subscription_id = "sub_stripe_1"

    # Sequence of DB calls:
    # 1. get_payment_method
    # 2. update (unset defaults)
    # 3. get_subscription
    # 4. commit
    # 5. refresh

    mock_res_pm = MagicMock()
    mock_res_pm.scalar_one_or_none.return_value = pm

    mock_res_sub = MagicMock()
    mock_res_sub.scalar_one_or_none.return_value = sub

    # Configure execute return values based on query structure (hard to match exactly)
    # Simplification: we mock get_payment_method and get_subscription methods on service

    payment_service.get_payment_method = AsyncMock(return_value=pm)
    payment_service.get_subscription = AsyncMock(return_value=sub)

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:
        await payment_service.set_default_payment_method(mock_db_session, pm_id, user_id)

        # Verified calls
        assert pm.is_default is True
        # Stripe Update Sub
        args_sub, _ = mock_stripe.call_args_list[1]
        assert args_sub[1] == "sub_stripe_1"


@pytest.mark.asyncio
async def test_delete_default_payment_method_with_promotion(payment_service, mock_db_session):
    user_id = uuid4()
    pm_id = uuid4()

    # Mock PM to be deleted (is_default=True)
    pm = PaymentMethod(
        id=pm_id, user_id=user_id, stripe_payment_method_id="pm_val", is_default=True
    )

    # Mock other PMs
    other_pm = PaymentMethod(
        id=uuid4(), user_id=user_id, stripe_payment_method_id="pm_other", is_default=False
    )

    # Setup mocks
    payment_service.get_payment_method = AsyncMock(return_value=pm)
    payment_service.list_payment_methods = AsyncMock(return_value=[pm, other_pm])
    payment_service.set_default_payment_method = AsyncMock()

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock):
        with patch("services.payment_service.payment_lock") as mock_lock:
            mock_lock.return_value.__aenter__.return_value = None

            result = await payment_service.delete_payment_method(mock_db_session, pm_id, user_id)

            assert result is True
            assert pm.is_active is False

            # Verify promotion called
            payment_service.set_default_payment_method.assert_called_with(
                mock_db_session, other_pm.id, user_id
            )


@pytest.mark.asyncio
async def test_attach_payment_method_commit_error(payment_service, mock_db_session):
    user_id = uuid4()
    customer_id = "cus_123"
    pm_data = MagicMock()
    pm_data.payment_method_id = "pm_123"

    with patch.object(payment_service, "_run_stripe_cmd", new_callable=AsyncMock) as mock_stripe:
        mock_stripe.return_value.card.brand = "visa"
        mock_stripe.return_value.customer = "cus_123"

        # Mock DB commit to fail
        mock_db_session.commit.side_effect = Exception("DB Error")

        # Mock security logger to avoid actual logging errors
        with patch("services.payment_service.security_logger") as mock_logger:
            with pytest.raises(Exception, match="DB Error"):
                await payment_service.attach_payment_method(
                    mock_db_session, user_id, pm_data, customer_id
                )

            mock_logger.log_payment_operation.assert_called_with(
                operation="add_payment_method", user_id=user_id, success=False, details=Any
            )


@pytest.mark.asyncio
async def test_create_subscription_free_plan(payment_service, mock_db_session):
    user_id = uuid4()
    customer_id = "cus_123"
    data = MagicMock()
    data.plan = SubscriptionPlanEnum.FREE

    # Existing paid subscription
    existing = Subscription(
        user_id=user_id,
        plan=SubscriptionPlan.PRO,
        stripe_subscription_id="sub_123",
        status=SubscriptionStatus.ACTIVE,
    )

    payment_service.get_subscription = AsyncMock(return_value=existing)

    with patch("services.payment_service.payment_lock") as mock_lock:
        mock_lock.return_value.__aenter__.return_value = None

        with patch.object(
            payment_service, "_run_stripe_cmd", new_callable=AsyncMock
        ) as mock_stripe:
            result = await payment_service.create_or_update_subscription(
                mock_db_session, user_id, data, customer_id
            )

            assert result.plan == SubscriptionPlan.FREE
            assert result.stripe_subscription_id is None

            # Verify Stripe cancellation
            # Check if called at least once with these args
            # Using loop to find the specific call because there might be other calls
            # Check if called at least once with these args
            # Using loop to find the specific call because there might be other calls
            found = False
            for call in mock_stripe.call_args_list:
                args, _ = call
                if len(args) > 1 and args[1] == "sub_123":
                    found = True
                    break
            assert found, "Stripe Subscription.delete not called with sub_123"
