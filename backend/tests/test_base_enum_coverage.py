"""
Tests for BaseEnum model utility.
Covers models/base_enum.py for increased coverage.
"""


from models.base_enum import BaseEnum


class ColorEnum(BaseEnum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class TestBaseEnum:
    """Tests for BaseEnum functionality."""

    def test_enum_creation(self):
        """Test that enum can be created correctly."""
        assert ColorEnum.RED == "red"
        assert ColorEnum.GREEN == "green"
        assert ColorEnum.BLUE == "blue"
        assert isinstance(ColorEnum.RED, str)

    def test_from_value_with_valid_string(self):
        """Test from_value with valid string value."""
        assert ColorEnum.from_value("red") == ColorEnum.RED
        assert ColorEnum.from_value("green") == ColorEnum.GREEN

    def test_from_value_with_case_insensitive_string(self):
        """Test from_value is case-insensitive."""
        assert ColorEnum.from_value("RED") == ColorEnum.RED
        assert ColorEnum.from_value("Green") == ColorEnum.GREEN

    def test_from_value_with_enum_instance(self):
        """Test from_value with actual enum instance (should verify the early return)."""
        # This covers: if isinstance(value, cls): return value
        assert ColorEnum.from_value(ColorEnum.BLUE) == ColorEnum.BLUE

    def test_from_value_with_invalid_value_returns_default(self):
        """Test from_value returns default for invalid value."""
        # Creates a ValueError internally caught
        assert ColorEnum.from_value("purple", default=ColorEnum.RED) == ColorEnum.RED
        assert ColorEnum.from_value("purple", default=None) is None

    def test_from_value_with_empty_value_returns_default(self):
        """Test from_value returns default for empty values."""
        # This covers: if not value: return default
        assert ColorEnum.from_value(None, default=ColorEnum.BLUE) == ColorEnum.BLUE
        assert ColorEnum.from_value("", default=ColorEnum.BLUE) == ColorEnum.BLUE

    def test_list_values(self):
        """Test list() returns all enum values."""
        values = ColorEnum.list()
        assert len(values) == 3
        assert "red" in values
        assert "green" in values
        assert "blue" in values
