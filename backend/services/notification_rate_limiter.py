"""
Rate limiter for notifications to prevent spam.
Limits notifications per user per time window.
"""

import threading
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from utils.logger import setup_logger

logger = setup_logger("notification_rate_limiter")


class NotificationRateLimiter:
    """
    Rate limiter for notifications.
    Prevents sending too many notifications to a single user.
    """

    def __init__(
        self, max_per_hour: int = 20, max_per_day: int = 50, max_same_type_per_hour: int = 5
    ):
        self.max_per_hour = max_per_hour
        self.max_per_day = max_per_day
        self.max_same_type_per_hour = max_same_type_per_hour

        # Track notifications: user_id -> list of (timestamp, type)
        self._notifications: dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()

    def _cleanup_old_entries(self, user_id: str):
        """Remove entries older than 24 hours."""
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        self._notifications[user_id] = [
            (ts, t) for ts, t in self._notifications[user_id] if ts > cutoff
        ]

    def can_send(self, user_id: str, notification_type: str) -> tuple[bool, str]:
        """
        Check if a notification can be sent to the user.
        Returns (can_send, reason) tuple.
        """
        with self._lock:
            user_key = str(user_id)
            self._cleanup_old_entries(user_key)

            now = datetime.now(UTC)
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(hours=24)

            entries = self._notifications[user_key]

            # Count notifications in last hour
            hourly_count = sum(1 for ts, _ in entries if ts > hour_ago)
            if hourly_count >= self.max_per_hour:
                logger.warning(
                    f"Rate limit: User {user_key} exceeded hourly limit ({hourly_count}/{self.max_per_hour})"
                )
                return False, f"Hourly limit reached ({self.max_per_hour}/hour)"

            # Count notifications in last 24 hours
            daily_count = sum(1 for ts, _ in entries if ts > day_ago)
            if daily_count >= self.max_per_day:
                logger.warning(
                    f"Rate limit: User {user_key} exceeded daily limit ({daily_count}/{self.max_per_day})"
                )
                return False, f"Daily limit reached ({self.max_per_day}/day)"

            # Count same type notifications in last hour
            same_type_count = sum(
                1 for ts, t in entries if ts > hour_ago and t == notification_type
            )
            if same_type_count >= self.max_same_type_per_hour:
                logger.warning(
                    f"Rate limit: User {user_key} exceeded type limit for {notification_type}"
                )
                return False, f"Too many {notification_type} notifications"

            return True, "OK"

    def record_notification(self, user_id: str, notification_type: str):
        """Record that a notification was sent."""
        with self._lock:
            user_key = str(user_id)
            now = datetime.now(UTC)
            self._notifications[user_key].append((now, notification_type))

    def get_user_stats(self, user_id: str) -> dict:
        """Get notification stats for a user."""
        with self._lock:
            user_key = str(user_id)
            self._cleanup_old_entries(user_key)

            now = datetime.now(UTC)
            hour_ago = now - timedelta(hours=1)
            day_ago = now - timedelta(hours=24)

            entries = self._notifications[user_key]

            return {
                "hourly_count": sum(1 for ts, _ in entries if ts > hour_ago),
                "daily_count": sum(1 for ts, _ in entries if ts > day_ago),
                "hourly_limit": self.max_per_hour,
                "daily_limit": self.max_per_day,
            }


# Global rate limiter instance
_rate_limiter: NotificationRateLimiter | None = None


def get_rate_limiter() -> NotificationRateLimiter:
    """Get or create the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = NotificationRateLimiter()
    return _rate_limiter
