import json
import logging
from datetime import timedelta
from typing import Any

import redis.asyncio as redis

from app.core.config import settings


logger = logging.getLogger("wishshare.wishlist_cache")


class WishlistCache:
    def __init__(
        self,
        redis_dsn: str | None = None,
        ttl_public: int | None = None,
        ttl_private: int | None = None,
        ttl_list: int | None = None,
        enabled: bool | None = None,
    ) -> None:
        self._redis_dsn = redis_dsn or settings.redis_dsn
        self._ttl_public = ttl_public or settings.wishlist_cache_ttl_public
        self._ttl_private = ttl_private or settings.wishlist_cache_ttl_private
        self._ttl_list = ttl_list or settings.wishlist_cache_ttl_list
        self._enabled = enabled if enabled is not None else settings.wishlist_cache_enabled
        self._redis: redis.Redis | None = None
        self._hits = 0
        self._misses = 0
        self._errors = 0
        self._sets = 0

    async def _get_redis(self) -> redis.Redis | None:
        if not self._enabled:
            return None
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    self._redis_dsn,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                await self._redis.ping()
                logger.info("WishlistCache connected redis=%s", self._redis_dsn)
            except Exception as exc:
                logger.warning("WishlistCache redis unavailable: %s", exc)
                self._redis = None
        return self._redis

    def _item_key(self, slug: str, role: str) -> str:
        return f"wishlist:item:{slug}:{role}"

    def _list_key(self, user_id: int, limit: int, offset: int) -> str:
        return f"wishlist:list:{user_id}:{limit}:{offset}"

    def _ttl_for_role(self, role: str) -> int:
        if role == "public":
            return self._ttl_public
        return self._ttl_private

    async def get_item(self, slug: str, role: str) -> dict[str, Any] | None:
        try:
            client = await self._get_redis()
            if client is None:
                self._misses += 1
                return None
            data = await client.get(self._item_key(slug, role))
            if not data:
                self._misses += 1
                return None
            self._hits += 1
            return json.loads(data)
        except redis.RedisError as exc:
            self._errors += 1
            logger.warning("WishlistCache get_item failed slug=%s role=%s error=%s", slug, role, exc)
            return None
        except Exception as exc:
            self._errors += 1
            logger.debug("WishlistCache get_item parse error slug=%s role=%s error=%s", slug, role, exc)
            return None

    async def set_item(self, slug: str, role: str, payload: dict[str, Any], ttl: int | None = None) -> bool:
        try:
            client = await self._get_redis()
            if client is None:
                return False
            value = json.dumps(payload, ensure_ascii=False)
            key = self._item_key(slug, role)
            await client.setex(key, ttl or self._ttl_for_role(role), value)
            self._sets += 1
            return True
        except redis.RedisError as exc:
            self._errors += 1
            logger.warning("WishlistCache set_item failed slug=%s role=%s error=%s", slug, role, exc)
            return False
        except Exception as exc:
            self._errors += 1
            logger.debug("WishlistCache set_item error slug=%s role=%s error=%s", slug, role, exc)
            return False

    async def get_list(self, user_id: int, limit: int, offset: int) -> list[dict[str, Any]] | None:
        try:
            client = await self._get_redis()
            if client is None:
                self._misses += 1
                return None
            data = await client.get(self._list_key(user_id, limit, offset))
            if not data:
                self._misses += 1
                return None
            self._hits += 1
            return json.loads(data)
        except redis.RedisError as exc:
            self._errors += 1
            logger.warning("WishlistCache get_list failed user_id=%s error=%s", user_id, exc)
            return None
        except Exception as exc:
            self._errors += 1
            logger.debug("WishlistCache get_list parse error user_id=%s error=%s", user_id, exc)
            return None

    async def set_list(
        self,
        user_id: int,
        limit: int,
        offset: int,
        payload: list[dict[str, Any]],
        ttl: int | None = None,
    ) -> bool:
        try:
            client = await self._get_redis()
            if client is None:
                return False
            value = json.dumps(payload, ensure_ascii=False)
            key = self._list_key(user_id, limit, offset)
            await client.setex(key, ttl or self._ttl_list, value)
            self._sets += 1
            return True
        except redis.RedisError as exc:
            self._errors += 1
            logger.warning("WishlistCache set_list failed user_id=%s error=%s", user_id, exc)
            return False
        except Exception as exc:
            self._errors += 1
            logger.debug("WishlistCache set_list error user_id=%s error=%s", user_id, exc)
            return False

    async def invalidate_wishlist(self, slug: str) -> int:
        try:
            client = await self._get_redis()
            if client is None:
                return 0
            keys = [self._item_key(slug, "public"), self._item_key(slug, "friend"), self._item_key(slug, "owner")]
            return int(await client.delete(*keys))
        except redis.RedisError as exc:
            self._errors += 1
            logger.warning("WishlistCache invalidate_wishlist failed slug=%s error=%s", slug, exc)
            return 0

    async def invalidate_lists(self, user_id: int) -> int:
        try:
            client = await self._get_redis()
            if client is None:
                return 0
            keys = []
            async for key in client.scan_iter(match=f"wishlist:list:{user_id}:*"):
                keys.append(key)
            if not keys:
                return 0
            return int(await client.delete(*keys))
        except redis.RedisError as exc:
            self._errors += 1
            logger.warning("WishlistCache invalidate_lists failed user_id=%s error=%s", user_id, exc)
            return 0

    async def ping(self) -> bool:
        client = await self._get_redis()
        if client is None:
            return False
        try:
            await client.ping()
            return True
        except Exception:
            return False

    async def get_stats(self) -> dict[str, Any]:
        try:
            client = await self._get_redis()
            total = self._hits + self._misses
            stats = {
                "hits": self._hits,
                "misses": self._misses,
                "errors": self._errors,
                "sets": self._sets,
                "hit_rate": round(self._hits / total * 100, 2) if total else 0,
                "enabled": client is not None,
                "ttl_public": self._ttl_public,
                "ttl_private": self._ttl_private,
                "ttl_list": self._ttl_list,
                "total_keys": 0,
            }
            if client is not None:
                count = 0
                async for _ in client.scan_iter(match="wishlist:*"):
                    count += 1
                stats["total_keys"] = count
            return stats
        except Exception as exc:
            logger.warning("WishlistCache get_stats failed error=%s", exc)
            return {
                "hits": self._hits,
                "misses": self._misses,
                "errors": self._errors,
                "sets": self._sets,
                "hit_rate": 0,
                "enabled": False,
                "total_keys": 0,
                "error": str(exc),
            }


wishlist_cache = WishlistCache()
