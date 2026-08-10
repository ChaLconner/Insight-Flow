from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from models.payment import (
    PaymentHistory,
    PaymentMethod,
)
from services.payment_service import PaymentService


@pytest.fixture
def payment_service():
    with patch("services.payment_service.get_settings") as mock_settings:
        mock_settings.return_value.stripe.is_configured = True
        mock_settings.return_value.stripe.secret_key = "sk_test_123"
        service = PaymentService()
        # Mock _run_stripe_cmd to avoid thread executor complexity in tests
        # We will patch it per test or globally here if possible,
        # but better to let it run and mock stripe functions if we want to test the executor logic,
        # OR just mock _run_stripe_cmd to simply await the function result.

        # Let's mock _run_stripe_cmd to simplify
        async def mock_run_cmd(func, *args, **kwargs):
            return func(*args, **kwargs)

        service._run_stripe_cmd = mock_run_cmd
        return service


@pytest.fixture
def mock_db_session():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_get_or_create_stripe_customer_cached_on_user_obj(payment_service, mock_db_session):
    user_id = uuid4()
    user = MagicMock()
    user.stripe_customer_id = "cus_cached_123"

    # Needs to verify it exists
    with patch("stripe.Customer.retrieve") as mock_retrieve:
        mock_retrieve.return_value = MagicMock(id="cus_cached_123")

        cid = await payment_service.get_or_create_stripe_customer(
            mock_db_session, user_id, "test@test.com", user=user
        )

        assert cid == "cus_cached_123"
        mock_retrieve.assert_called_once_with("cus_cached_123")


@pytest.mark.asyncio
async def test_get_payment_method_only_returns_active_methods(payment_service, mock_db_session):
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = result

    await payment_service.get_payment_method(mock_db_session, uuid4(), uuid4())

    statement = str(mock_db_session.execute.call_args.args[0])
    assert "payment_methods.is_active" in statement


@pytest.mark.asyncio
async def test_get_or_create_stripe_customer_create_new(payment_service, mock_db_session):
    user_id = uuid4()
    user = MagicMock()
    user.stripe_customer_id = None

    # Mock DB lookups returning None
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = result_mock

    # Mock Stripe search returning empty
    result_list = MagicMock()
    result_list.data = []

    # Mock Stripe create
    new_cus = MagicMock(id="cus_new_123")

    with (
        patch("stripe.Customer.list", return_value=result_list),
        patch("stripe.Customer.create", return_value=new_cus) as mock_create,
    ):
        cid = await payment_service.get_or_create_stripe_customer(
            mock_db_session, user_id, "test@test.com", user=user
        )

        assert cid == "cus_new_123"
        mock_create.assert_called_once()
        # Verify DB update
        assert mock_db_session.execute.call_count >= 1


@pytest.mark.asyncio
async def test_create_setup_intent_success(payment_service, mock_db_session):
    user_id = uuid4()
    email = "test@test.com"

    # Mock customer retrieval
    payment_service.get_or_create_stripe_customer = AsyncMock(return_value="cus_123")

    # Mock SetupIntent create
    intent_mock = MagicMock(client_secret="seti_secret_123")

    with patch("stripe.SetupIntent.create", return_value=intent_mock):
        response = await payment_service.create_setup_intent(mock_db_session, user_id, email)

        assert response.client_secret == "seti_secret_123"
        assert response.customer_id == "cus_123"


@pytest.mark.asyncio
async def test_attach_payment_method(payment_service, mock_db_session):
    user_id = uuid4()
    data = MagicMock(
        payment_method_id="pm_123", set_as_default=True, billing_address=None, billing_name="Test"
    )
    customer_id = "cus_123"

    # Mock Stripe PM retrieve
    pm_stripe = MagicMock()
    pm_stripe.customer = None
    pm_stripe.card.brand = "visa"
    pm_stripe.card.last4 = "4242"
    pm_stripe.billing_details.address.line1 = None  # prevent attribute error

    with (
        patch("stripe.PaymentMethod.retrieve", return_value=pm_stripe),
        patch("stripe.PaymentMethod.attach") as mock_attach,
        patch("stripe.Customer.modify") as mock_modify,
    ):
        result = await payment_service.attach_payment_method(
            mock_db_session, user_id, data, customer_id
        )

        assert result.stripe_payment_method_id == "pm_123"
        mock_attach.assert_called_once()
        # Since default=True, should modify customer
        mock_modify.assert_called_once()
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_attach_payment_method_rejects_foreign_customer(payment_service, mock_db_session):
    user_id = uuid4()
    data = MagicMock(payment_method_id="pm_123", set_as_default=True)
    customer_id = "cus_123"

    pm_stripe = MagicMock()
    pm_stripe.customer = "cus_foreign"

    with (
        patch("stripe.PaymentMethod.retrieve", return_value=pm_stripe),
        pytest.raises(ValueError, match="current customer"),
    ):
        await payment_service.attach_payment_method(mock_db_session, user_id, data, customer_id)


@pytest.mark.asyncio
async def test_list_payment_history(payment_service, mock_db_session):
    user_id = uuid4()

    # Mock Count
    mock_db_session.execute.extract_mock_name()  # reset
    count_res = MagicMock()
    count_res.scalar.return_value = 5

    # Mock Items
    items_res = MagicMock()
    items_res.scalars.return_value.all.return_value = [
        PaymentHistory(id=uuid4()),
        PaymentHistory(id=uuid4()),
    ]

    mock_db_session.execute.side_effect = [count_res, items_res]

    items, total = await payment_service.list_payment_history(mock_db_session, user_id)

    assert total == 5
    assert len(items) == 2


@pytest.mark.asyncio
async def test_get_payment_history_stats(payment_service, mock_db_session):
    user_id = uuid4()

    row = MagicMock()
    row.total_spent = Decimal("100.50")
    row.total_payments = 10
    row.successful_payments = 9
    row.failed_payments = 1
    row.pending_payments = 0
    row.refunded_payments = 0
    row.currency_count = 1
    row.currency = "usd"

    res = MagicMock()
    res.fetchone.return_value = row
    mock_db_session.execute.return_value = res

    stats = await payment_service.get_payment_history_stats(mock_db_session, user_id)

    assert stats["total_spent"] == 100.50
    assert stats["failed_payments"] == 1


@pytest.mark.asyncio
async def test_delete_payment_method(payment_service, mock_db_session):
    user_id = uuid4()
    pm_id = uuid4()

    # Mock get_payment_method
    pm = PaymentMethod(
        id=pm_id, stripe_payment_method_id="pm_stripe_123", is_default=False, user_id=user_id
    )
    payment_service.get_payment_method = AsyncMock(return_value=pm)

    with patch("stripe.PaymentMethod.detach") as mock_detach:
        result = await payment_service.delete_payment_method(mock_db_session, pm_id, user_id)

        assert result is True
        mock_detach.assert_called_once()
        assert pm.is_active is False  # Soft deleted


@pytest.mark.asyncio
async def test_delete_payment_method_auto_promote(payment_service, mock_db_session):
    user_id = uuid4()
    pm_id = uuid4()

    pm = PaymentMethod(
        id=pm_id, stripe_payment_method_id="pm_stripe_123", is_default=True, user_id=user_id
    )
    other_pm = PaymentMethod(
        id=uuid4(), stripe_payment_method_id="pm_stripe_456", is_default=False, user_id=user_id
    )

    payment_service.get_payment_method = AsyncMock(return_value=pm)
    payment_service.list_payment_methods = AsyncMock(return_value=[other_pm, pm])
    payment_service.set_default_payment_method = AsyncMock()

    with patch("stripe.PaymentMethod.detach"):
        result = await payment_service.delete_payment_method(mock_db_session, pm_id, user_id)

        assert result is True
        payment_service.set_default_payment_method.assert_called_once_with(
            mock_db_session, other_pm.id, user_id
        )
