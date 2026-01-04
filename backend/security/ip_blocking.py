"""
IP Blocking Service - A+ Security Enhancement.

Provides automatic IP blocking for repeated rate limit violations
or suspicious activity. Uses Redis for distributed blocking across workers.

Features:
- Automatic temporary blocks for repeat offenders
- Escalating block durations
- Whitelist support for trusted IPs
- Async-first design
"""

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import ClassVar

logger = logging.getLogger("ip_blocking")

# Configuration
BLOCK_THRESHOLD = int(os.getenv("IP_BLOCK_THRESHOLD", "10"))  # Block after N violations
INITIAL_BLOCK_MINUTES = int(os.getenv("IP_BLOCK_INITIAL_MINUTES", "15"))
MAX_BLOCK_HOURS = int(os.getenv("IP_BLOCK_MAX_HOURS", "24"))
ESCALATION_MULTIPLIER = 2  # Double block time for each repeat offense


class IPBlockingService:
    """
    Service for managing IP-based blocking for repeat offenders.
    
    Usage:
        blocker = get_ip_blocker()
        
        # Check if IP is blocked
        if await blocker.is_blocked(ip):
            raise HTTPException(403, "Access temporarily blocked")
        
        # Record a violation
        await blocker.record_violation(ip, "rate_limit_exceeded")
    """
    
    # In-memory fallback (for development or when Redis is unavailable)
    _violation_counts: ClassVar[dict[str, int]] = {}
    _blocked_ips: ClassVar[dict[str, datetime]] = {}
    _block_counts: ClassVar[dict[str, int]] = {}  # For escalation
    
    # Whitelisted IPs (never block these)
    WHITELISTED_IPS: ClassVar[set[str]] = {
        "127.0.0.1",
        "::1",
        "localhost",
    }
    
    def __init__(self):
        self._redis_client = None
        self._use_redis = False
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection if available."""
        try:
            from services.cache_service import cache_service
            
            if hasattr(cache_service, 'backend') and hasattr(cache_service.backend, 'client'):
                self._redis_client = cache_service.backend.client
                self._use_redis = True
                logger.info("IP blocking service using Redis backend")
            else:
                logger.info("IP blocking service using in-memory backend")
        except Exception as e:
            logger.warning(f"Redis not available for IP blocking, using in-memory: {e}")
    
    def _is_whitelisted(self, ip: str) -> bool:
        """Check if IP is whitelisted."""
        if not ip:
            return False
        
        # Check exact match
        if ip in self.WHITELISTED_IPS:
            return True
        
        # Check environment-defined whitelist
        env_whitelist = os.getenv("IP_WHITELIST", "")
        if env_whitelist:
            whitelist = [x.strip() for x in env_whitelist.split(",")]
            if ip in whitelist:
                return True
        
        return False
    
    async def is_blocked(self, ip: str) -> tuple[bool, datetime | None]:
        """
        Check if an IP is currently blocked.
        
        Returns:
            Tuple of (is_blocked, blocked_until)
        """
        if not ip or self._is_whitelisted(ip):
            return False, None
        
        if self._use_redis and self._redis_client:
            return await self._is_blocked_redis(ip)
        else:
            return self._is_blocked_memory(ip)
    
    async def _is_blocked_redis(self, ip: str) -> tuple[bool, datetime | None]:
        """Check block status in Redis."""
        try:
            block_key = f"ip_block:{ip}"
            blocked_until_str = await self._redis_client.get(block_key)
            
            if blocked_until_str:
                blocked_until = datetime.fromisoformat(blocked_until_str.decode())
                if blocked_until > datetime.now(UTC):
                    return True, blocked_until
                else:
                    # Block expired, clean up
                    await self._redis_client.delete(block_key)
            
            return False, None
        except Exception as e:
            logger.error(f"Error checking Redis block status: {e}")
            return self._is_blocked_memory(ip)
    
    def _is_blocked_memory(self, ip: str) -> tuple[bool, datetime | None]:
        """Check block status in memory."""
        if ip in self._blocked_ips:
            blocked_until = self._blocked_ips[ip]
            if blocked_until > datetime.now(UTC):
                return True, blocked_until
            else:
                # Block expired
                del self._blocked_ips[ip]
        
        return False, None
    
    async def record_violation(self, ip: str, reason: str = "unknown") -> bool:
        """
        Record a violation for an IP address.
        
        Returns:
            True if the IP was blocked as a result
        """
        if not ip or self._is_whitelisted(ip):
            return False
        
        logger.warning(f"Security violation from {ip}: {reason}")
        
        if self._use_redis and self._redis_client:
            return await self._record_violation_redis(ip, reason)
        else:
            return self._record_violation_memory(ip, reason)
    
    async def _record_violation_redis(self, ip: str, reason: str) -> bool:
        """Record violation in Redis."""
        try:
            violation_key = f"ip_violations:{ip}"
            block_count_key = f"ip_block_count:{ip}"
            
            # Increment violation count with 1-hour expiry
            count = await self._redis_client.incr(violation_key)
            await self._redis_client.expire(violation_key, 3600)  # 1 hour window
            
            if count >= BLOCK_THRESHOLD:
                # Get block count for escalation
                block_count_str = await self._redis_client.get(block_count_key)
                block_count = int(block_count_str.decode()) if block_count_str else 0
                
                # Calculate block duration with escalation
                block_minutes = min(
                    INITIAL_BLOCK_MINUTES * (ESCALATION_MULTIPLIER ** block_count),
                    MAX_BLOCK_HOURS * 60
                )
                blocked_until = datetime.now(UTC) + timedelta(minutes=block_minutes)
                
                # Set the block
                block_key = f"ip_block:{ip}"
                await self._redis_client.setex(
                    block_key,
                    int(block_minutes * 60),  # TTL in seconds
                    blocked_until.isoformat()
                )
                
                # Increment block count for escalation (7-day expiry)
                await self._redis_client.incr(block_count_key)
                await self._redis_client.expire(block_count_key, 7 * 24 * 3600)
                
                # Reset violation count
                await self._redis_client.delete(violation_key)
                
                logger.warning(
                    f"IP {ip} blocked until {blocked_until} (violation: {reason}, "
                    f"block #{block_count + 1}, duration: {block_minutes}min)"
                )
                
                # Log to security audit
                try:
                    from utils.security_audit import security_audit
                    security_audit.log_suspicious_activity(
                        ip_address=ip,
                        description=f"IP blocked due to repeated violations: {reason}",
                    )
                except Exception:
                    pass
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error recording violation in Redis: {e}")
            return self._record_violation_memory(ip, reason)
    
    def _record_violation_memory(self, ip: str, reason: str) -> bool:
        """Record violation in memory."""
        # Increment count
        self._violation_counts[ip] = self._violation_counts.get(ip, 0) + 1
        count = self._violation_counts[ip]
        
        if count >= BLOCK_THRESHOLD:
            # Get block count for escalation
            block_count = self._block_counts.get(ip, 0)
            
            # Calculate block duration
            block_minutes = min(
                INITIAL_BLOCK_MINUTES * (ESCALATION_MULTIPLIER ** block_count),
                MAX_BLOCK_HOURS * 60
            )
            blocked_until = datetime.now(UTC) + timedelta(minutes=block_minutes)
            
            # Set block
            self._blocked_ips[ip] = blocked_until
            self._block_counts[ip] = block_count + 1
            
            # Reset violation count
            self._violation_counts[ip] = 0
            
            logger.warning(
                f"IP {ip} blocked until {blocked_until} (violation: {reason}, "
                f"block #{block_count + 1}, duration: {block_minutes}min)"
            )
            
            return True
        
        return False
    
    async def unblock(self, ip: str) -> bool:
        """
        Manually unblock an IP address.
        
        Returns:
            True if the IP was unblocked
        """
        if self._use_redis and self._redis_client:
            try:
                block_key = f"ip_block:{ip}"
                result = await self._redis_client.delete(block_key)
                if result:
                    logger.info(f"Manually unblocked IP: {ip}")
                return result > 0
            except Exception as e:
                logger.error(f"Error unblocking IP in Redis: {e}")
        
        # Memory fallback
        if ip in self._blocked_ips:
            del self._blocked_ips[ip]
            logger.info(f"Manually unblocked IP: {ip}")
            return True
        
        return False
    
    async def get_block_info(self, ip: str) -> dict | None:
        """Get information about an IP's block status."""
        is_blocked, blocked_until = await self.is_blocked(ip)
        
        if not is_blocked:
            return None
        
        return {
            "ip": ip,
            "blocked_until": blocked_until.isoformat() if blocked_until else None,
            "remaining_seconds": int((blocked_until - datetime.now(UTC)).total_seconds()) if blocked_until else 0,
        }


# Singleton instance
_ip_blocker: IPBlockingService | None = None


def get_ip_blocker() -> IPBlockingService:
    """Get the IP blocking service singleton."""
    global _ip_blocker
    if _ip_blocker is None:
        _ip_blocker = IPBlockingService()
    return _ip_blocker
