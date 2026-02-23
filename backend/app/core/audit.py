"""Audit logging for critical operations."""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from fastapi import Request


logger = logging.getLogger("wishshare.audit")


class AuditAction(str, Enum):
    """Audit action types."""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_COMPLETE = "password_reset_complete"
    EMAIL_VERIFY = "email_verify"
    
    # OAuth
    OAUTH_LOGIN = "oauth_login"
    OOGLE_LOGIN = "google_login"
    GITHUB_LOGIN = "github_login"
    
    # Wishlist operations
    WISHLIST_CREATE = "wishlist_create"
    WISHLIST_UPDATE = "wishlist_update"
    WISHLIST_DELETE = "wishlist_delete"
    
    # Gift operations
    GIFT_CREATE = "gift_create"
    GIFT_UPDATE = "gift_update"
    GIFT_DELETE = "gift_delete"
    
    # Contribution operations
    CONTRIBUTION_CREATE = "contribution_create"
    CONTRIBUTION_CANCEL = "contribution_cancel"
    
    # Rate limit
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


def audit_log(
    action: AuditAction,
    request: Request | None = None,
    user_id: int | str | None = None,
    details: dict[str, Any] | None = None,
    success: bool = True,
) -> None:
    """
    Log an audit event.
    
    Args:
        action: The action being performed
        request: FastAPI request object (for IP, user agent)
        user_id: ID of the user performing the action
        details: Additional details about the action
        success: Whether the action was successful
    """
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action.value,
        "success": success,
    }
    
    if user_id is not None:
        event["user_id"] = str(user_id)
    
    if request:
        # Extract client info
        client_host = None
        if request.client:
            client_host = request.client.host
        
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_host = forwarded.split(",")[0].strip()
        
        event["ip"] = client_host
        event["user_agent"] = request.headers.get("User-Agent", "")[:200]
        event["request_id"] = request.headers.get("X-Request-Id", "")
    
    if details:
        # Sanitize sensitive data
        sanitized = {}
        for key, value in details.items():
            if key in ("password", "token", "secret", "key", "authorization"):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        event["details"] = sanitized
    
    # Log at appropriate level
    if success:
        logger.info("AUDIT: %s", event)
    else:
        logger.warning("AUDIT: %s", event)


def audit_login_success(request: Request, user_id: int, email: str) -> None:
    """Log successful login."""
    audit_log(
        AuditAction.LOGIN,
        request=request,
        user_id=user_id,
        details={"email": email},
        success=True,
    )


def audit_login_failed(request: Request, email: str, reason: str) -> None:
    """Log failed login attempt."""
    audit_log(
        AuditAction.LOGIN_FAILED,
        request=request,
        details={"email": email, "reason": reason},
        success=False,
    )


def audit_logout(request: Request, user_id: int) -> None:
    """Log logout."""
    audit_log(
        AuditAction.LOGOUT,
        request=request,
        user_id=user_id,
    )


def audit_register(request: Request, user_id: int, email: str) -> None:
    """Log user registration."""
    audit_log(
        AuditAction.REGISTER,
        request=request,
        user_id=user_id,
        details={"email": email},
    )


def audit_password_change(request: Request, user_id: int) -> None:
    """Log password change."""
    audit_log(
        AuditAction.PASSWORD_CHANGE,
        request=request,
        user_id=user_id,
    )


def audit_password_reset_request(request: Request, email: str, exists: bool) -> None:
    """Log password reset request."""
    audit_log(
        AuditAction.PASSWORD_RESET_REQUEST,
        request=request,
        details={"email": email, "user_exists": exists},
    )


def audit_oauth_login(request: Request, user_id: int, provider: str, email: str) -> None:
    """Log OAuth login."""
    action = AuditAction.GOOGLE_LOGIN if provider == "google" else AuditAction.GITHUB_LOGIN
    audit_log(
        action,
        request=request,
        user_id=user_id,
        details={"provider": provider, "email": email},
    )


def audit_wishlist_action(
    action: AuditAction,
    request: Request,
    user_id: int,
    wishlist_id: int,
    details: dict[str, Any] | None = None,
) -> None:
    """Log wishlist operation."""
    event_details = {"wishlist_id": wishlist_id}
    if details:
        event_details.update(details)
    audit_log(action, request=request, user_id=user_id, details=event_details)


def audit_gift_action(
    action: AuditAction,
    request: Request,
    user_id: int,
    gift_id: int,
    wishlist_id: int,
    details: dict[str, Any] | None = None,
) -> None:
    """Log gift operation."""
    event_details = {"gift_id": gift_id, "wishlist_id": wishlist_id}
    if details:
        event_details.update(details)
    audit_log(action, request=request, user_id=user_id, details=event_details)


def audit_contribution_action(
    action: AuditAction,
    request: Request,
    user_id: int,
    contribution_id: int,
    gift_id: int,
    amount: float,
) -> None:
    """Log contribution operation."""
    audit_log(
        action,
        request=request,
        user_id=user_id,
        details={
            "contribution_id": contribution_id,
            "gift_id": gift_id,
            "amount": amount,
        },
    )


def audit_rate_limit_exceeded(request: Request, endpoint: str, retry_after: int) -> None:
    """Log rate limit exceeded."""
    audit_log(
        AuditAction.RATE_LIMIT_EXCEEDED,
        request=request,
        details={"endpoint": endpoint, "retry_after": retry_after},
        success=False,
    )