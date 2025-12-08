import enum
from typing import Optional, Type, TypeVar, Any

T = TypeVar('T', bound='BaseEnum')

class BaseEnum(str, enum.Enum):
    """Base class for string enums with helper methods."""
    
    @classmethod
    def from_value(cls: Type[T], value: Any, default: Optional[T] = None) -> Optional[T]:
        """Safely convert string or value to enum."""
        if not value:
            return default
        
        # specific handling if value is already an enum instance
        if isinstance(value, cls):
            return value
            
        try:
            val_str = str(value).lower()
            return cls(val_str)
        except ValueError:
            return default

    @classmethod
    def list(cls) -> list[str]:
        """Return list of values."""
        return [c.value for c in cls]
