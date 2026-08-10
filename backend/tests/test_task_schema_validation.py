"""Validation tests for task update payload bounds."""

import pytest
from pydantic import ValidationError

from schemas.task import TaskUpdate


def test_task_update_preserves_create_field_bounds() -> None:
    """Updates must not bypass title and description limits."""

    assert TaskUpdate(title="Valid", description="D" * 2000).title == "Valid"

    with pytest.raises(ValidationError):
        TaskUpdate(title="")

    with pytest.raises(ValidationError):
        TaskUpdate(title="T" * 151)

    with pytest.raises(ValidationError):
        TaskUpdate(description="D" * 2001)
