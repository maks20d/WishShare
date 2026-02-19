from typing import Annotated
import logging

from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.models import User


DbSessionDep = Annotated[AsyncSession, Depends(get_db)]
logger = logging.getLogger("wishshare.auth")


async def get_current_user(
    request: Request,
    db: DbSessionDep,
    access_token: str | None = Cookie(default=None, alias="access_token"),
) -> User:
    logger.debug(
        "get_current_user: path=%s cookies=%s auth_header=%s",
        request.url.path,
        list(request.cookies.keys()),
        request.headers.get("Authorization", "None")[:50] if request.headers.get("Authorization") else "None",
    )
    
    token = access_token
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()

    if not token:
        logger.info(
            "Auth token missing path=%s ip=%s ua=%s",
            request.url.path,
            request.client.host if request.client else None,
            request.headers.get("user-agent"),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    logger.debug("get_current_user: token found, length=%d", len(token) if token else 0)
    
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        logger.info("Auth token invalid path=%s", request.url.path)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        user_id = int(payload["sub"])
        logger.debug("get_current_user: decoded user_id=%s", user_id)
    except (TypeError, ValueError):
        logger.info("Auth token subject invalid path=%s", request.url.path)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None
    
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
    except Exception as e:
        logger.exception("get_current_user: DB error when fetching user_id=%s", user_id)
        raise HTTPException(status_code=500, detail="Database error")
    
    if not user:
        logger.info("Auth user missing path=%s user_id=%s", request.url.path, user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    logger.debug("get_current_user: successfully authenticated user_id=%s email=%s", user.id, user.email)
    return user


async def get_optional_user(
    request: Request,
    db: DbSessionDep,
    access_token: str | None = Cookie(default=None, alias="access_token"),
) -> User | None:
    token = access_token
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user
