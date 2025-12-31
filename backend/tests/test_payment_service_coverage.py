
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY, call
from uuid import uuid4
from decimal import Decimal
from datetime import datetime
import stripe
import json

from services.payment_service import PaymentService
from models.payment import PaymentMethod, Subscription, SubscriptionPlan, SubscriptionStatus, PaymentStatus, PaymentHistory
from schemas.payment import PaymentMethodCreate, SubscriptionPlanEnum, SubscriptionCreate, PLAN_DETAILS
from models.webhook_log import WebhookEventLog

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
    user.stripe_customer_id = None 
    return user

@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    db = AsyncMock()
    # Mock result for execute
    mock_result = MagicMock()
    db.execute = AsyncMock(return_value=mock_result)
    
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db

@pytest.fixture
def service():
    """Create a configured PaymentService with mocked Stripe."""
    with patch("services.payment_service.get_settings") as mock_settings:
        mock_settings.return_value.stripe.is_configured = True
        mock_settings.return_value.stripe.secret_key = "sk_test_123"
        
        service = PaymentService()
        service._run_stripe_cmd = AsyncMock()
        return service

# ============================================================================
# Customer Management Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_or_create_stripe_customer_existing_on_user(service, mock_db, mock_user):
    mock_user.stripe_customer_id = "cus_existing123"
    service._run_stripe_cmd.return_value = MagicMock(id="cus_existing123")
    result = await service.get_or_create_stripe_customer(mock_db, mock_user.id, mock_user.email, user=mock_user)
    assert result == "cus_existing123"

@pytest.mark.asyncio
async def test_get_or_create_stripe_customer_search_by_email(service, mock_db, mock_user):
    """Test when no ID anywhere, but found by email in Stripe."""
    mock_user.stripe_customer_id = None
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    
    found_customer = MagicMock(id="cus_found_email")
    search_result = MagicMock()
    search_result.data = [found_customer]
    
    service._run_stripe_cmd.return_value = search_result
    
    result = await service.get_or_create_stripe_customer(mock_db, mock_user.id, mock_user.email, user=mock_user)
    
    assert result == "cus_found_email"
    assert mock_db.commit.called

@pytest.mark.asyncio
async def test_get_or_create_stripe_customer_create_new(service, mock_db, mock_user):
    """Test creating a brand new customer."""
    mock_user.stripe_customer_id = None
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    
    async def side_effect(func, *args, **kwargs):
        if func == stripe.Customer.list:
            return MagicMock(data=[])
        if func == stripe.Customer.create:
            return MagicMock(id="cus_created_new")
        return None
        
    service._run_stripe_cmd.side_effect = side_effect
    
    result = await service.get_or_create_stripe_customer(mock_db, mock_user.id, mock_user.email, user=mock_user)
    
    assert result == "cus_created_new"

# ============================================================================
# Payment Method Management Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_setup_intent_success(service, mock_db, mock_user):
    mock_user.stripe_customer_id = "cus_123"
    service.get_or_create_stripe_customer = AsyncMock(return_value="cus_123")
    mock_intent = MagicMock()
    mock_intent.client_secret = "seti_secret_123"
    service._run_stripe_cmd.return_value = mock_intent
    result = await service.create_setup_intent(mock_db, mock_user.id, mock_user.email, user=mock_user)
    assert result.client_secret == "seti_secret_123"

@pytest.mark.asyncio
async def test_attach_payment_method_full(service, mock_db, mock_user):
    """Test attaching a payment method with full details."""
    pm_id = "pm_123"
    cus_id = "cus_123"
    
    data = PaymentMethodCreate(
        payment_method_id=pm_id,
        customer_id=cus_id,
        set_as_default=True,
        billing_name="John Doe",
        billing_email="john@example.com"
    )
    
    stripe_pm = MagicMock()
    stripe_pm.customer = None
    stripe_pm.card.brand = "visa"
    stripe_pm.card.last4 = "4242"
    stripe_pm.card.exp_month = 12
    stripe_pm.card.exp_year = 2030
    stripe_pm.billing_details.address.line1 = "123 St"
    service._run_stripe_cmd.return_value = stripe_pm
    
    async def run_stripe(*args, **kwargs):
        if args[0] == stripe.PaymentMethod.retrieve:
            return stripe_pm
        return None
    service._run_stripe_cmd.side_effect = run_stripe

    result = await service.attach_payment_method(mock_db, mock_user.id, data, cus_id)
    
    assert mock_db.add.call_count == 1
    assert mock_db.commit.called

@pytest.mark.asyncio
async def test_delete_payment_method_with_promotion(service, mock_db, mock_user):
    """Test deleting default method promotes another."""
    pm_id = uuid4()
    
    pm_to_delete = PaymentMethod(
        id=pm_id, user_id=mock_user.id, is_default=True, 
        stripe_payment_method_id="pm_del", stripe_customer_id="cus_123"
    )
    
    other_pm = PaymentMethod(
        id=uuid4(), user_id=mock_user.id, is_default=False, 
        stripe_payment_method_id="pm_other", stripe_customer_id="cus_123"
    )
    
    service.get_payment_method = AsyncMock(return_value=pm_to_delete)
    service.list_payment_methods = AsyncMock(return_value=[other_pm]) 
    service.set_default_payment_method = AsyncMock()
    
    with patch("services.payment_service.payment_lock") as mock_lock:
        mock_lock.return_value.__aenter__.return_value = None
        mock_lock.return_value.__aexit__.return_value = None
        
        result = await service.delete_payment_method(mock_db, pm_id, mock_user.id)
        
        assert result is True
        service.set_default_payment_method.assert_awaited_once_with(mock_db, other_pm.id, mock_user.id)

# ============================================================================
# Subscription Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_subscription_free_plan(service, mock_db, mock_user):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    data = SubscriptionCreate(plan=SubscriptionPlanEnum.FREE)
    with patch("services.payment_service.payment_lock") as mock_lock:
        mock_lock.return_value.__aenter__.return_value = None
        sub = await service.create_or_update_subscription(mock_db, mock_user.id, data, "cus_123")
        assert sub.plan == SubscriptionPlan.FREE

@pytest.mark.asyncio
async def test_upgrade_subscription_to_pro(service, mock_db, mock_user):
    current_sub = Subscription(
        id=uuid4(), user_id=mock_user.id, plan=SubscriptionPlan.FREE, 
        status=SubscriptionStatus.ACTIVE, stripe_customer_id="cus_123"
    )
    mock_db.execute.return_value.scalar_one_or_none.return_value = current_sub
    
    pm = MagicMock()
    pm.stripe_payment_method_id = "pm_card_123"
    service.get_payment_method = AsyncMock(return_value=pm)
    
    data = SubscriptionCreate(plan=SubscriptionPlanEnum.PRO, payment_method_id=uuid4())
    
    product = MagicMock(id="prod_pro")
    product.metadata = {"plan_id": "pro"}
    price = MagicMock(id="price_pro")
    price.unit_amount = 699 
    
    stripe_sub = MagicMock(id="sub_new_stripe")
    stripe_sub.current_period_start = 1000000000
    stripe_sub.current_period_end = 1000002000
    stripe_sub.latest_invoice = MagicMock(status="paid", amount_paid=699, id="in_123")
    
    async def side_effect(func, *args, **kwargs):
        if func == stripe.Product.list:
            return MagicMock(data=[product])
        if func == stripe.Price.list:
            return MagicMock(data=[price])
        if func == stripe.Subscription.create:
            return stripe_sub
        return MagicMock()
        
    service._run_stripe_cmd.side_effect = side_effect
    
    with patch("services.payment_service.payment_lock") as mock_lock:
        mock_lock.return_value.__aenter__.return_value = None
        sub = await service.create_or_update_subscription(mock_db, mock_user.id, data, "cus_123")
        assert sub.plan == SubscriptionPlan.PRO

@pytest.mark.asyncio
async def test_cancel_subscription_end_of_period(service, mock_db, mock_user):
    sub = Subscription(
        id=uuid4(), user_id=mock_user.id, stripe_subscription_id="sub_123",
        status=SubscriptionStatus.ACTIVE, cancel_at_period_end=False
    )
    mock_db.execute.return_value.scalar_one_or_none.return_value = sub
    
    with patch("services.payment_service.payment_lock") as mock_lock:
        mock_lock.return_value.__aenter__.return_value = None
        result = await service.cancel_subscription(mock_db, mock_user.id, cancel_immediately=False)
        assert result.cancel_at_period_end is True

@pytest.mark.asyncio
async def test_resume_subscription(service, mock_db, mock_user):
    sub = Subscription(
        id=uuid4(), user_id=mock_user.id, stripe_subscription_id="sub_123",
        status=SubscriptionStatus.ACTIVE, cancel_at_period_end=True
    )
    mock_db.execute.return_value.scalar_one_or_none.return_value = sub
    stripe_sub = MagicMock(status="active")
    service._run_stripe_cmd.return_value = stripe_sub
    
    with patch("services.payment_service.payment_lock") as mock_lock:
        mock_lock.return_value.__aenter__.return_value = None
        result = await service.resume_subscription(mock_db, mock_user.id)
        assert result.cancel_at_period_end is False

# ============================================================================
# History Tests
# ============================================================================

@pytest.mark.asyncio
async def test_list_payment_history_filters(service, mock_db, mock_user):
    mock_result = mock_db.execute.return_value
    mock_result.scalar.return_value = 10 
    mock_result.scalars.return_value.all.return_value = [] 
    
    items, total = await service.list_payment_history(
        mock_db, mock_user.id, status_filter="succeeded", start_date=datetime.now()
    )
    assert total == 10

@pytest.mark.asyncio
async def test_get_payment_history_stats(service, mock_db, mock_user):
    row = MagicMock()
    row.total_spent = 100.50
    row.total_payments = 5
    row.successful_payments = 4
    row.failed_payments = 1
    row.pending_payments = 0
    row.refunded_payments = 0
    
    mock_result = mock_db.execute.return_value
    mock_result.fetchone.return_value = row
    
    stats = await service.get_payment_history_stats(mock_db, mock_user.id)
    assert stats["total_spent"] == 100.50

# ============================================================================
# Webhook Tests
# ============================================================================

@pytest.mark.asyncio
async def test_process_webhook_idempotency(service, mock_db):
    event = {"id": "evt_123", "type": "ping", "data": {"object": {}}}
    existing_log = WebhookEventLog(processed=True)
    mock_db.execute.return_value.scalar_one_or_none.return_value = existing_log
    await service.process_webhook(mock_db, event)
    assert not mock_db.add.called

@pytest.mark.asyncio
async def test_process_webhook_subscription_deleted(service, mock_db):
    event = {
        "id": "evt_del", 
        "type": "customer.subscription.deleted", 
        "data": {"object": {"id": "sub_123"}}
    }
    
    sub = Subscription(id=uuid4(), stripe_subscription_id="sub_123", plan=SubscriptionPlan.PRO)
    
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)), # Webhook log
        MagicMock(scalar_one_or_none=MagicMock(return_value=sub)), # Subscription lookup
    ]
    
    await service.process_webhook(mock_db, event)
    assert sub.plan == SubscriptionPlan.FREE

@pytest.mark.asyncio
async def test_handle_payment_succeeded(service, mock_db):
    invoice = {
        "id": "in_123", 
        "customer": "cus_123", 
        "amount_paid": 1000, 
        "currency": "usd",
        "status": "paid",
        "payment_intent": "pi_123"
    }
    
    user = MagicMock(id=uuid4(), stripe_customer_id="cus_123")
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=MagicMock(return_value=user)),
        MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    ]
    
    await service._handle_payment_succeeded(mock_db, invoice)
    assert mock_db.add.called
    added_history = mock_db.add.call_args[0][0]
    assert added_history.amount == 10.0

@pytest.mark.asyncio
async def test_handle_charge_refunded(service, mock_db):
    charge = {
        "id": "ch_123",
        "amount_refunded": 1000,
        "amount": 1000,
        "refunded": True
    }
    
    history = PaymentHistory(
        id=uuid4(), stripe_charge_id="ch_123", 
        status=PaymentStatus.SUCCEEDED, amount=10.0
    )
    
    mock_db.execute.return_value.scalar_one_or_none.return_value = history
    await service._handle_charge_refunded(mock_db, charge)
    assert history.status == PaymentStatus.REFUNDED

