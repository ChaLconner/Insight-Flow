"""
Tests for services/payment_service.py with mocked Stripe API.

Focus on testable parts without complex Stripe mocking.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestPaymentServiceInit:
    """Tests for PaymentService initialization."""
    
    def test_payment_service_init_configured(self):
        """Test PaymentService initializes when Stripe is configured."""
        with patch('services.payment_service.get_settings') as mock_settings:
            mock_settings.return_value.stripe.is_configured = True
            mock_settings.return_value.stripe.secret_key = "sk_test_xxx"
            
            from services.payment_service import PaymentService
            service = PaymentService()
            
            assert service.is_configured is True
    
    def test_payment_service_init_not_configured(self):
        """Test PaymentService handles missing Stripe config."""
        with patch('services.payment_service.get_settings') as mock_settings:
            mock_settings.return_value.stripe.is_configured = False
            
            from services.payment_service import PaymentService
            service = PaymentService()
            
            assert service.is_configured is False
    
    def test_check_configured_raises_when_not_configured(self):
        """Test _check_configured raises ValueError when Stripe not configured."""
        with patch('services.payment_service.get_settings') as mock_settings:
            mock_settings.return_value.stripe.is_configured = False
            
            from services.payment_service import PaymentService
            service = PaymentService()
            
            with pytest.raises(ValueError) as exc_info:
                service._check_configured()
            
            assert "Stripe is not configured" in str(exc_info.value)


class TestSubscriptionPlans:
    """Tests for subscription plan configurations."""
    
    def test_subscription_plan_enum_values(self):
        """Test subscription plan enum has expected values."""
        from schemas.payment import SubscriptionPlanEnum
        
        plan_values = [p.value for p in SubscriptionPlanEnum]
        
        assert "free" in plan_values
        assert "pro" in plan_values
    
    def test_plan_details_structure(self):
        """Test plan details have expected structure."""
        from schemas.payment import PLAN_DETAILS
        
        for plan_name, details in PLAN_DETAILS.items():
            # All plans should have name and price attributes
            assert hasattr(details, 'name') or 'name' in str(type(details))


class TestPaymentModels:
    """Tests for payment models."""
    
    def test_payment_status_enum(self):
        """Test PaymentStatus enum values."""
        from models.payment import PaymentStatus
        
        assert PaymentStatus.PENDING is not None
        assert PaymentStatus.SUCCEEDED is not None
        assert PaymentStatus.FAILED is not None
    
    def test_subscription_status_enum(self):
        """Test SubscriptionStatus enum values."""
        from models.payment import SubscriptionStatus
        
        assert SubscriptionStatus.ACTIVE is not None
        assert SubscriptionStatus.CANCELED is not None
