import time
from typing import Dict, Any, Optional
from utils.logger import setup_logger

logger = setup_logger("cache_service")

class InMemoryCache:
    _instance = None
    MAX_SIZE = 1000
    _lock = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InMemoryCache, cls).__new__(cls)
            cls._instance.cache = {}
            cls._instance.default_timeout = 300
            import threading
            cls._instance._lock = threading.Lock()
        return cls._instance

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if key in self.cache:
                cached_data = self.cache[key]
                current_time = time.time()
                
                # Use stored timeout or fallback to default
                timeout = cached_data.get("timeout", self.default_timeout)
                
                if current_time - cached_data["timestamp"] < timeout:
                    return cached_data
                else:
                    # Expired
                    del self.cache[key]
            return None

    def set(self, key: str, value: Dict[str, Any], timeout: Optional[int] = None):
        with self._lock:
            # Evict if full (FIFO)
            if len(self.cache) >= self.MAX_SIZE and key not in self.cache:
                # Remove oldest item (Python dicts preserve insertion order)
                try:
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                except StopIteration:
                    pass

            self.cache[key] = {
                **value,
                "timestamp": time.time(),
                "timeout": timeout if timeout is not None else self.default_timeout
            }

    def clear(self):
        with self._lock:
            self.cache.clear()
        logger.info("Cache cleared")

    def invalidate_pattern(self, pattern: str):
        keys_to_remove = [key for key in self.cache.keys() if pattern in key]
        for key in keys_to_remove:
            del self.cache[key]
        logger.info(f"Invalidated {len(keys_to_remove)} keys matching '{pattern}'")

# Global instance
cache_service = InMemoryCache()
