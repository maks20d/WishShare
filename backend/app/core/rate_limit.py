"""
Simple in-memory rate limiter for authentication endpoints.
For production with multiple workers, replace with Redis-backed slowapi.
"""
import time
import logging
from collections import defaultdict
from fastapi import HTTPException, Request, status

logger = logging.getLogger("wishshare.rate_limit")

# {ip: [timestamp, ...]}
_login_attempts: dict[str, list[float]] = defaultdict(list)

WINDOW_SECONDS = 60
MAX_ATTEMPTS = 10  # per IP per window


def check_rate_limit(request: Request, *, endpoint: str = "auth") -> None:
    """
    Raises HTTP 429 if the client IP has exceeded the allowed attempts
    within the rolling time window.
    """
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window_start = now - WINDOW_SECONDS

    attempts = _login_attempts[ip]
    # Purge old entries
    attempts[:] = [t for t in attempts if t >= window_start]

    if len(attempts) >= MAX_ATTEMPTS:
        logger.warning(
            "Rate limit exceeded endpoint=%s ip=%s attempts=%d",
            endpoint, ip, len(attempts),
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Please wait {WINDOW_SECONDS} seconds.",
            headers={"Retry-After": str(WINDOW_SECONDS)},
        )

    attempts.append(now)
