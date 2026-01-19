from datetime import datetime
from typing import ClassVar
from uuid import uuid4

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase

from models.mixins import ChangeHistoryMixin, SoftDeleteMixin, VersionedMixin


class Base(DeclarativeBase):
    pass


class TestModel(Base, SoftDeleteMixin, VersionedMixin, ChangeHistoryMixin):
    __tablename__ = "test_model"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    __history_fields__: ClassVar[list[str]] = ["name"]


def test_soft_delete_mixin():
    model = TestModel(id=1, name="Test")
    assert model.deleted_at is None
    assert model.is_deleted is False
    assert model.deleted_by_id is None

    # Act
    deleter_id = uuid4()
    model.soft_delete(deleted_by=deleter_id)

    # Assert
    assert model.deleted_at is not None
    assert model.is_deleted is True
    assert model.deleted_by_id == deleter_id

    # Restore
    model.restore()
    assert model.deleted_at is None
    assert model.is_deleted is False
    assert model.deleted_by_id is None


def test_versioned_mixin():
    model = TestModel(id=1, version=1)

    # Check
    assert model.check_version(1) is True
    assert model.check_version(2) is False

    # Increment
    new_ver = model.increment_version()
    assert new_ver == 2
    assert model.version == 2


def test_change_history_mixin():
    model = TestModel(id=1, name="Old")

    # Mock old state
    old_state = {"name": "Old"}

    # Change
    model.name = "New"

    # Get diff
    diff = model.get_diff(old_state)
    assert "name" in diff
    assert diff["name"] == ("Old", "New")

    # Patch ChangeHistory to allow instantiation
    from unittest.mock import MagicMock, patch

    user_id = uuid4()

    with patch("models.mixins.ChangeHistory") as MockChangeHistory:
        # Configure the mock instance returned by constructor
        mock_instance = MagicMock()
        mock_instance.entity_type = "TestModel"
        mock_instance.entity_id = 1
        mock_instance.changes = diff
        mock_instance.changed_by_id = user_id
        mock_instance.changed_at = datetime.now()

        MockChangeHistory.return_value = mock_instance

        model.create_history_entry(diff, user_id=user_id)

        # Verify it called constructor with correct args
        MockChangeHistory.assert_called_once()
        call_kwargs = MockChangeHistory.call_args.kwargs
        assert call_kwargs["entity_type"] == "TestModel"
        assert call_kwargs["entity_id"] == 1
        assert call_kwargs["changes"] == diff


def test_mixin_helpers():
    from models.mixins import (
        AuditMixin,
        create_soft_delete_index,
        create_tenant_index,
        setup_history_tracking,
    )

    # Test index helpers
    idx1 = create_soft_delete_index("table", "col1")
    assert idx1.name == "ix_table_col1_active"

    idx2 = create_tenant_index("table", "col2")
    assert idx2.name == "ix_table_tenant_col2"

    # Test AuditMixin setters
    class AuditModel(AuditMixin):
        pass

    am = AuditModel()
    uid = uuid4()
    am.set_created_by(uid)
    assert am.created_by_id == uid
    assert am.updated_by_id == uid

    am.set_updated_by(uuid4())
    assert am.updated_by_id != uid

    # Test history tracking setup
    setup_history_tracking(TestModel)

    # Test expressions/filters
    # Just calling them to ensure code coverage
    expr = TestModel.is_deleted
    assert expr is not None

    filt = TestModel.not_deleted_filter()
    assert filt is not None

    from models.mixins import TenantMixin

    class TenantModel(TenantMixin):
        pass

    tfilt = TenantModel.tenant_filter(uuid4())
    assert tfilt is not None


def test_change_history_mixin_uuid():
    # Test UUID conversion in get_diff
    TestModel(id=1, name="Old")  # name is str, but let's pretend?
    # Actually we need a field that is UUID?
    # Mixin iterates over __history_fields__.
    # If we add a UUID field to TestModel history fields?

    # Let's subclass TestModel or modify it
    class UUIDModel(TestModel):
        other_id = Column(String)  # Mocking as string col but treating as UUID in python?
        __history_fields__: ClassVar[list[str]] = ["other_id"]

    u1 = uuid4()
    u2 = uuid4()

    m = UUIDModel(other_id=u2)
    old_state = {"other_id": u1}

    # get_diff will see u1 (UUID) and u2 (UUID)
    # logic: if isinstance(old_value, UUID) -> str

    diff = m.get_diff(old_state)
    assert "other_id" in diff
    assert diff["other_id"] == (str(u1), str(u2))
