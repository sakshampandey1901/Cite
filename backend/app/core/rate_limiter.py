"""Rate limiting middleware using Redis."""
import redis
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter using Redis for distributed rate limiting."""

    def __init__(self):
        """Initialize Redis connection."""
        self.redis_client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self):
        """Connect to Redis with error handling."""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis for rate limiting")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis connection failed: {e}. Rate limiting will be disabled.")
            self.redis_client = None
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            self.redis_client = None

    def _parse_rate_limit(self, rate_limit_str: str) -> Tuple[int, int]:
        """
        Parse rate limit string (e.g., '10/hour', '30/minute').

        Returns:
            Tuple of (max_requests, window_seconds)
        """
        try:
            count, period = rate_limit_str.split('/')
            count = int(count)

            period_map = {
                'second': 1,
                'minute': 60,
                'hour': 3600,
                'day': 86400
            }

            window_seconds = period_map.get(period.lower(), 3600)
            return count, window_seconds
        except Exception as e:
            logger.error(f"Failed to parse rate limit '{rate_limit_str}': {e}")
            return 10, 3600  # Default: 10 per hour

    def check_rate_limit(
        self,
        user_id: str,
        action: str,
        rate_limit_str: str
    ) -> None:
        """
        Check if user has exceeded rate limit for the action.

        Args:
            user_id: User identifier
            action: Action name (e.g., 'upload', 'assist')
            rate_limit_str: Rate limit string (e.g., '10/hour')

        Raises:
            HTTPException: If rate limit exceeded
        """
        # If Redis is not available, skip rate limiting with warning
        if self.redis_client is None:
            logger.warning(
                f"Rate limiting bypassed for user {user_id} action {action} "
                "(Redis unavailable)"
            )
            return

        max_requests, window_seconds = self._parse_rate_limit(rate_limit_str)
        key = f"ratelimit:{user_id}:{action}"

        try:
            # Get current count
            current = self.redis_client.get(key)

            if current is None:
                # First request in window
                self.redis_client.setex(key, window_seconds, 1)
                logger.debug(f"Rate limit initialized for {user_id}:{action} (1/{max_requests})")
                return

            current_count = int(current)

            if current_count >= max_requests:
                # Rate limit exceeded
                ttl = self.redis_client.ttl(key)
                wait_time = ttl if ttl > 0 else window_seconds

                logger.warning(
                    f"Rate limit exceeded for user {user_id} action {action}: "
                    f"{current_count}/{max_requests}"
                )

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "action": action,
                        "limit": max_requests,
                        "window": f"{window_seconds}s",
                        "retry_after": wait_time,
                        "message": f"Too many {action} requests. Please try again in {wait_time} seconds."
                    }
                )

            # Increment counter
            new_count = self.redis_client.incr(key)
            logger.debug(f"Rate limit updated for {user_id}:{action} ({new_count}/{max_requests})")

        except HTTPException:
            # Re-raise rate limit exceptions
            raise
        except redis.RedisError as e:
            # Redis errors should not break the application
            logger.error(f"Redis error during rate limiting: {e}")
            logger.warning(f"Rate limiting bypassed for user {user_id} action {action}")
        except Exception as e:
            logger.error(f"Unexpected error during rate limiting: {e}")
            # Fail open: allow request if rate limiter fails
            logger.warning(f"Rate limiting bypassed for user {user_id} action {action}")

    def reset_rate_limit(self, user_id: str, action: str) -> bool:
        """
        Reset rate limit for a user action (admin function).

        Args:
            user_id: User identifier
            action: Action name

        Returns:
            True if reset successful, False otherwise
        """
        if self.redis_client is None:
            logger.warning("Cannot reset rate limit: Redis unavailable")
            return False

        try:
            key = f"ratelimit:{user_id}:{action}"
            deleted = self.redis_client.delete(key)
            logger.info(f"Reset rate limit for {user_id}:{action}")
            return bool(deleted)
        except redis.RedisError as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False

    def get_rate_limit_status(self, user_id: str, action: str, rate_limit_str: str) -> dict:
        """
        Get current rate limit status for a user action.

        Args:
            user_id: User identifier
            action: Action name
            rate_limit_str: Rate limit string

        Returns:
            Dictionary with rate limit status
        """
        max_requests, window_seconds = self._parse_rate_limit(rate_limit_str)

        if self.redis_client is None:
            return {
                "enabled": False,
                "reason": "Redis unavailable"
            }

        try:
            key = f"ratelimit:{user_id}:{action}"
            current = self.redis_client.get(key)
            ttl = self.redis_client.ttl(key)

            if current is None:
                remaining = max_requests
                reset_in = window_seconds
            else:
                remaining = max(0, max_requests - int(current))
                reset_in = ttl if ttl > 0 else window_seconds

            return {
                "enabled": True,
                "action": action,
                "limit": max_requests,
                "remaining": remaining,
                "reset_in_seconds": reset_in,
                "window_seconds": window_seconds
            }
        except redis.RedisError as e:
            logger.error(f"Failed to get rate limit status: {e}")
            return {
                "enabled": False,
                "reason": f"Redis error: {str(e)}"
            }


# Global rate limiter instance
rate_limiter = RateLimiter()
