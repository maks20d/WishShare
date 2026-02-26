from datetime import datetime, timedelta, timezone
import logging
import secrets
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_dev_logger = logging.getLogger("wishshare.security")
_insecure_keys = {"CHANGE_ME", "your-secret-key-here-change-in-production", "secret", "jwt_secret", "changeme", ""}

if not settings.jwt_secret_key or settings.jwt_secret_key in _insecure_keys or len(settings.jwt_secret_key) < 32:
    env = getattr(settings, "environment", "local") or "local"
    if env.lower() == "local":
        settings.jwt_secret_key = secrets.token_urlsafe(64)
        _dev_logger.warning("JWT_SECRET_KEY was missing/insecure; generated ephemeral key for local dev")
    else:
        raise RuntimeError("JWT_SECRET_KEY must be set to a secure value (32+ chars) in production")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_delta_minutes: int | None = None) -> str:
    expire_minutes = expires_delta_minutes or settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    # SECURITY: Added 'type' field to distinguish access tokens from refresh tokens
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire, "type": "access", "jti": str(uuid4())}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def create_refresh_token(subject: str, expires_delta_minutes: int | None = None) -> str:
    expire_minutes = expires_delta_minutes or settings.refresh_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire, "type": "refresh", "jti": str(uuid4())}
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def create_password_reset_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.password_reset_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": email, "exp": expire, "type": "password_reset"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_email_verification_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.password_reset_token_expire_minutes
    )
    payload: dict[str, Any] = {"sub": email, "exp": expire, "type": "email_verify"}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _decode_token_raw(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None
    except Exception:
        return None


def decode_password_reset_token(token: str) -> str | None:
    payload = _decode_token_raw(token)
    if not payload or payload.get("type") != "password_reset":
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None


def decode_refresh_token(token: str) -> dict[str, Any] | None:
    payload = _decode_token_raw(token)
    if not payload or payload.get("type") != "refresh":
        return None
    return payload


def decode_email_verification_token(token: str) -> str | None:
    payload = _decode_token_raw(token)
    if not payload or payload.get("type") != "email_verify":
        return None
    subject = payload.get("sub")
    return subject if isinstance(subject, str) else None


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None
    except Exception:
        return None
