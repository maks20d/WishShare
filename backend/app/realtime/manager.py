import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class WishlistConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, list[tuple[WebSocket, str]]] = defaultdict(list)

    async def connect(self, slug: str, websocket: WebSocket, role: str) -> None:
        self._connections[slug].append((websocket, role))
        logger.info("WS connect slug=%s role=%s total=%s", slug, role, len(self._connections[slug]))

    def disconnect(self, slug: str, websocket: WebSocket) -> None:
        if slug not in self._connections:
            return
        self._connections[slug] = [
            (ws, r) for (ws, r) in self._connections[slug] if ws is not websocket
        ]
        if not self._connections[slug]:
            self._connections.pop(slug, None)
        else:
            logger.info("WS disconnect slug=%s total=%s", slug, len(self._connections[slug]))

    async def broadcast_gift_event(
        self,
        slug: str,
        event_type: str,
        payload_for_owner: dict[str, Any],
        payload_for_friend: dict[str, Any],
        payload_for_public: dict[str, Any],
    ) -> None:
        if slug not in self._connections:
            return

        to_remove: list[WebSocket] = []
        for websocket, role in list(self._connections[slug]):
            try:
                if role == "owner":
                    payload = payload_for_owner
                elif role == "friend":
                    payload = payload_for_friend
                else:
                    payload = payload_for_public
                await websocket.send_json(
                    {
                        "type": event_type,
                        "gift": payload,
                    }
                )
            except Exception:
                logger.exception("WS broadcast failed slug=%s role=%s", slug, role)
                to_remove.append(websocket)

        if to_remove:
            self._connections[slug] = [
                (ws, r) for (ws, r) in self._connections[slug] if ws not in to_remove
            ]
            if not self._connections[slug]:
                self._connections.pop(slug, None)
            else:
                logger.info("WS pruned slug=%s total=%s", slug, len(self._connections[slug]))


logger = logging.getLogger("wishshare.ws")
manager = WishlistConnectionManager()
