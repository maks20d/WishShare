"""Rate limiting implementation using in-memory storage with sliding window."""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable
import logging

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.config import settings


logger = logging.getLogger("wishshare.rate_limit")

MAX_ENTRIES = 10000
CLEANUP_INTERVAL = 100


@dataclass
class RateLimitEntry:
    """Track requests for a single client."""
    timestamps: list[float] = field(default_factory=list)
    last_access: float = field(default_factory=time.time)


class InMemoryRateLimiter:
    """In-memory rate limiter with sliding window algorithm and memory management."""
    
    def __init__(self):
        self._entries: dict[str, RateLimitEntry] = {}
        self._request_count = 0
    
    def _cleanup_old_requests(self, entry: RateLimitEntry, window_seconds: int) -> None:
        """Remove timestamps outside the current window."""
        cutoff = time.time() - window_seconds
        entry.timestamps = [ts for ts in entry.timestamps if ts > cutoff]
    
    def _cleanup_stale_entries(self, max_age_seconds: int = 3600) -> None:
        """Remove entries that haven't been accessed recently."""
        now = time.time()
        cutoff = now - max_age_seconds
        stale_keys = [
            key for key, entry in self._entries.items()
            if entry.last_access < cutoff and len(entry.timestamps) == 0
        ]
        for key in stale_keys:
            del self._entries[key]
        
        if stale_keys:
            logger.debug("Cleaned up %d stale rate limit entries", len(stale_keys))
    
    def _enforce_max_entries(self) -> None:
        """Remove oldest entries if we exceed max limit."""
        if len(self._entries) <= MAX_ENTRIES:
            return
        
        sorted_entries = sorted(
            self._entries.items(),
            key=lambda x: x[1].last_access
        )
        
        entries_to_remove = len(self._entries) - MAX_ENTRIES + 100
        for key, _ in sorted_entries[:entries_to_remove]:
            del self._entries[key]
        
        logger.warning(
            "Rate limit entries exceeded %d, removed %d oldest entries",
            MAX_ENTRIES, entries_to_remove
        )
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        """
        Check if request is allowed under rate limit.
        
        Returns:
            tuple[bool, int]: (is_allowed, retry_after_seconds)
        """
        now = time.time()
        
        entry = self._entries.get(key)
        if entry is None:
            entry = RateLimitEntry()
            self._entries[key] = entry
        
        entry.last_access = now
        
        self._cleanup_old_requests(entry, window_seconds)
        
        if len(entry.timestamps) >= max_requests:
            oldest = min(entry.timestamps)
            retry_after = int(oldest + window_seconds - now) + 1
            return False, max(1, retry_after)
        
        entry.timestamps.append(now)
        
        self._request_count += 1
        if self._request_count % CLEANUP_INTERVAL == 0:
            self._cleanup_stale_entries(window_seconds * 2)
            self._enforce_max_entries()
        
        return True, 0
    
    def reset(self, key: str) -> None:
        """Reset rate limit for a key (useful for testing)."""
        if key in self._entries:
            del self._entries[key]
    
    def get_stats(self) -> dict:
        """Get current rate limiter statistics."""
        return {
            "total_entries": len(self._entries),
            "total_requests_tracked": self._request_count,
            "max_entries": MAX_ENTRIES,
        }


# Global rate limiter instance
limiter = InMemoryRateLimiter()


def get_client_identifier(request: Request) -> str:
    """Get unique identifier for the client."""
    # Try X-Forwarded-For header first (for reverse proxy)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP (original client)
        client_ip = forwarded.split(",")[0].strip()
        return f"ip:{client_ip}"
    
    # Fall back to direct client IP
    if request.client:
        return f"ip:{request.client.host}"
    
    # Last resort: use a hash of available headers
    user_agent = request.headers.get("User-Agent", "")
    return f"ua:{hash(user_agent)}"


def rate_limit(
    max_requests: int | None = None,
    window_seconds: int | None = None,
    key_prefix: str = "",
) -> Callable:
    """
    Rate limit decorator/middleware for FastAPI endpoints.
    
    Args:
        max_requests: Maximum requests allowed in window (default from settings)
        window_seconds: Window duration in seconds (default from settings)
        key_prefix: Optional prefix for the rate limit key
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, request: Request = None, **kwargs):
            if not settings.rate_limit_enabled:
                return await func(*args, **kwargs)
            
            # Get request object from args or kwargs
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                if request is None:
                    request = kwargs.get("request")
            
            if request is None:
                # Can't rate limit without request, allow
                return await func(*args, **kwargs)
            
            # Build rate limit key
            client_id = get_client_identifier(request)
            path = request.url.path
            key = f"{key_prefix}:{client_id}:{path}"
            
            # Check rate limit
            allowed, retry_after = limiter.is_allowed(
                key,
                max_requests or settings.rate_limit_requests,
                window_seconds or settings.rate_limit_window_seconds,
            )
            
            if not allowed:
                logger.warning(
                    "Rate limit exceeded for %s on %s, retry_after=%ds",
                    client_id,
                    path,
                    retry_after,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def check_rate_limit(
    request: Request,
    max_requests: int | None = None,
    window_seconds: int | None = None,
    key_suffix: str = "",
) -> None:
    """
    Imperative rate limit check.
    
    Raises HTTPException if rate limit exceeded.
    """
    if not settings.rate_limit_enabled:
        return
    
    client_id = get_client_identifier(request)
    path = request.url.path
    key = f"{client_id}:{path}:{key_suffix}"
    
    allowed, retry_after = limiter.is_allowed(
        key,
        max_requests or settings.rate_limit_requests,
        window_seconds or settings.rate_limit_window_seconds,
    )
    
    if not allowed:
        logger.warning(
            "Rate limit exceeded for %s on %s, retry_after=%ds",
            client_id,
            path,
            retry_after,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )