import logging
from urllib.parse import parse_qs, unquote, urlparse

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSessionDep
from app.core.security import decode_access_token
from app.models.models import User, Wishlist, WishlistAccessEmail
from app.realtime.manager import manager


router = APIRouter(tags=["ws"])
logger = logging.getLogger("wishshare.ws")


@router.websocket("/ws/{wishlist_slug:path}")
async def wishlist_ws(
    websocket: WebSocket,
    wishlist_slug: str,
    db: DbSessionDep,
) -> None:
    await websocket.accept()
    decoded_slug = unquote(unquote(wishlist_slug))
    logger.info("WS accepted slug=%s", decoded_slug)

    query_params = parse_qs(urlparse(str(websocket.url)).query)
    token = None
    auth_header = websocket.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
    elif "token" in query_params:
        token = query_params["token"][0]
    elif "access_token" in websocket.cookies:
        token = websocket.cookies.get("access_token")

    viewer: User | None = None
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            try:
                user_id = int(payload["sub"])
            except (TypeError, ValueError):
                user_id = None
            if user_id is not None:
                result = await db.execute(select(User).where(User.id == user_id))
                viewer = result.scalar_one_or_none()

    result = await db.execute(select(Wishlist).where(Wishlist.slug == decoded_slug))
    wishlist = result.scalar_one_or_none()
    if not wishlist:
        logger.warning("WS wishlist not found slug=%s", decoded_slug)
        await websocket.close(code=1008)
        return

    if wishlist.privacy == "friends":
        if not viewer:
            logger.warning("WS auth required slug=%s", decoded_slug)
            await websocket.close(code=1008)
            return
        if viewer.id != wishlist.owner_id:
            access_result = await db.execute(
                select(WishlistAccessEmail.email).where(WishlistAccessEmail.wishlist_id == wishlist.id)
            )
            allowed = {
                (row[0] or "").strip().lower()
                for row in access_result.all()
                if row[0]
            }
            viewer_email = (viewer.email or "").strip().lower()
            if not viewer_email or viewer_email not in allowed:
                logger.warning("WS access denied slug=%s user_id=%s", decoded_slug, viewer.id)
                await websocket.close(code=1008)
                return

    role = "public"
    if viewer and viewer.id == wishlist.owner_id:
        role = "owner"
    elif viewer:
        role = "friend"

    await manager.connect(decoded_slug, websocket, role)
    logger.info("WS connected slug=%s role=%s", decoded_slug, role)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WS disconnected slug=%s", decoded_slug)
        manager.disconnect(decoded_slug, websocket)
