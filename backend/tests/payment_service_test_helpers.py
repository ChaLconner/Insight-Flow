from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from models.user import User
from services.payment_service import PaymentService


@contextmanager
def configured_stripe_settings():
    with patch("services.payment_service.get_settings") as mock:
        mock.return_value.stripe.is_configured = True
        mock.return_value.stripe.secret_key = "sk_test_123"
        yield mock


def make_mock_db_session():
    mock = AsyncMock()
    mock.execute = AsyncMock(return_value=MagicMock())
    mock.commit = AsyncMock()
    mock.refresh = AsyncMock()
    mock.add = MagicMock()
    mock.add_all = MagicMock()
    mock.rollback = AsyncMock()
    return mock


def make_payment_service():
    return PaymentService()


def make_test_user():
    user = MagicMock(spec=User)
    user.id = uuid4()
    user.email = "test@example.com"
    return user
