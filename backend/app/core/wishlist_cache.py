import json
import logging
import asyncio
import os
import time
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
        is_testing = (os.getenv("TESTING") or "").strip().lower() in {"1", "true", "yes"}
        self._allow_memory_fallback = (redis_dsn is None) and (not is_testing)
        self._redis_dsn = redis_dsn or settings.redis_dsn
        self._ttl_public = ttl_public or settings.wishlist_cache_ttl_public
        self._ttl_private = ttl_private or settings.wishlist_cache_ttl_private
        self._ttl_list = ttl_list or settings.wishlist_cache_ttl_list
        self._enabled = enabled if enabled is not None else settings.wishlist_cache_enabled
        self._redis: redis.Redis | None = None
        self._connect_lock = asyncio.Lock()
        self._cooldown_until_monotonic = 0.0
        self._connect_failures = 0
        self._memory_items: dict[str, tuple[float, str]] = {}
        self._memory_lists: dict[str, tuple[float, str]] = {}
        self._memory_max_items = 500
        self._memory_max_lists = 200
        self._hits = 0
        self._misses = 0
        self._errors = 0
        self._sets = 0

    def _list_keys_set_key(self, user_id: int) -> str:
        return f"wishlist:listkeys:{user_id}"

    def _in_cooldown(self) -> bool:
        return time.monotonic() < self._cooldown_until_monotonic

    def _mark_redis_failed(self, exc: Exception) -> None:
        self._redis = None
        self._connect_failures += 1
        cooldown = min(60.0, 1.0 * (2 ** min(self._connect_failures, 6)))
        self._cooldown_until_monotonic = time.monotonic() + cooldown
        logger.warning(
            "WishlistCache redis unavailable failures=%s cooldown_s=%.0f error=%s",
            self._connect_failures,
            cooldown,
            exc,
        )

    def _mem_get(self, store: dict[str, tuple[float, str]], key: str) -> str | None:
        now = time.monotonic()
        entry = store.get(key)
        if not entry:
            return None
        expires_at, payload = entry
        if expires_at <= now:
            store.pop(key, None)
            return None
        return payload

    def _mem_set(self, store: dict[str, tuple[float, str]], key: str, payload: str, ttl_s: int, max_size: int) -> None:
        now = time.monotonic()
        store[key] = (now + max(1, int(ttl_s)), payload)
        if len(store) <= max_size:
            return
        expired = [k for k, (exp, _) in store.items() if exp <= now]
        for k in expired:
            store.pop(k, None)
        if len(store) <= max_size:
            return
        overflow = len(store) - max_size
        for k in list(store.keys())[:overflow]:
            store.pop(k, None)

    async def _get_redis(self) -> redis.Redis | None:
        if not self._enabled:
            return None
        if not self._redis_dsn or not str(self._redis_dsn).strip():
            return None
        if self._redis is not None:
            return self._redis
        if self._in_cooldown():
            return None
        async with self._connect_lock:
            if self._redis is not None:
                return self._redis
            if self._in_cooldown():
                return None
            try:
                client = redis.from_url(
                    self._redis_dsn,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                    retry_on_timeout=True,
                    health_check_interval=30,
                )
                await client.ping()
                self._redis = client
                self._connect_failures = 0
                self._cooldown_until_monotonic = 0.0
                logger.info("WishlistCache connected redis=%s", self._redis_dsn)
            except Exception as exc:
                self._mark_redis_failed(exc)
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
                key = self._item_key(slug, role)
                if self._allow_memory_fallback:
                    cached = self._mem_get(self._memory_items, key)
                    if cached:
                        self._hits += 1
                        return json.loads(cached)
                self._misses += 1
                return None
            key = self._item_key(slug, role)
            data = await client.get(key)
            if not data:
                self._misses += 1
                return None
            self._hits += 1
            return json.loads(data)
        except redis.RedisError as exc:
            self._errors += 1
            self._mark_redis_failed(exc)
            return None
        except Exception as exc:
            self._errors += 1
            logger.debug("WishlistCache get_item parse error slug=%s role=%s error=%s", slug, role, exc)
            return None

    async def set_item(self, slug: str, role: str, payload: dict[str, Any], ttl: int | None = None) -> bool:
        try:
            client = await self._get_redis()
            if client is None:
                if not self._allow_memory_fallback:
                    return False
                value = json.dumps(payload, ensure_ascii=False)
                key = self._item_key(slug, role)
                self._mem_set(
                    self._memory_items,
                    key,
                    value,
                    ttl or self._ttl_for_role(role),
                    self._memory_max_items,
                )
                self._sets += 1
                return True
            value = json.dumps(payload, ensure_ascii=False)
            key = self._item_key(slug, role)
            await client.setex(key, ttl or self._ttl_for_role(role), value)
            self._sets += 1
            return True
        except redis.RedisError as exc:
            self._errors += 1
            self._mark_redis_failed(exc)
            return False
        except Exception as exc:
            self._errors += 1
            logger.debug("WishlistCache set_item error slug=%s role=%s error=%s", slug, role, exc)
            return False

    async def get_list(self, user_id: int, limit: int, offset: int) -> list[dict[str, Any]] | None:
        try:
            client = await self._get_redis()
            if client is None:
                key = self._list_key(user_id, limit, offset)
                if self._allow_memory_fallback:
                    cached = self._mem_get(self._memory_lists, key)
                    if cached:
                        self._hits += 1
                        return json.loads(cached)
                self._misses += 1
                return None
            key = self._list_key(user_id, limit, offset)
            data = await client.get(key)
            if not data:
                self._misses += 1
                return None
            self._hits += 1
            return json.loads(data)
        except redis.RedisError as exc:
            self._errors += 1
            self._mark_redis_failed(exc)
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
                if not self._allow_memory_fallback:
                    return False
                value = json.dumps(payload, ensure_ascii=False)
                key = self._list_key(user_id, limit, offset)
                effective_ttl = ttl or self._ttl_list
                self._mem_set(self._memory_lists, key, value, effective_ttl, self._memory_max_lists)
                self._sets += 1
                return True
            value = json.dumps(payload, ensure_ascii=False)
            key = self._list_key(user_id, limit, offset)
            keyset = self._list_keys_set_key(user_id)
            effective_ttl = ttl or self._ttl_list
            if isinstance(client, redis.Redis):
                pipe = client.pipeline()
                pipe.setex(key, effective_ttl, value)
                pipe.sadd(keyset, key)
                pipe.expire(keyset, max(60, effective_ttl + 300))
                await pipe.execute()
            else:
                await client.setex(key, effective_ttl, value)
                sadd = getattr(client, "sadd", None)
                if callable(sadd):
                    await sadd(keyset, key)
                expire = getattr(client, "expire", None)
                if callable(expire):
                    await expire(keyset, max(60, effective_ttl + 300))
            self._sets += 1
            return True
        except redis.RedisError as exc:
            self._errors += 1
            self._mark_redis_failed(exc)
            return False
        except Exception as exc:
            self._errors += 1
            logger.debug("WishlistCache set_list error user_id=%s error=%s", user_id, exc)
            return False

    async def invalidate_wishlist(self, slug: str) -> int:
        try:
            client = await self._get_redis()
            if client is None:
                if not self._allow_memory_fallback:
                    return 0
                deleted = 0
                for role in ("public", "friend", "owner"):
                    key = self._item_key(slug, role)
                    if self._memory_items.pop(key, None) is not None:
                        deleted += 1
                return deleted
            keys = [self._item_key(slug, "public"), self._item_key(slug, "friend"), self._item_key(slug, "owner")]
            return int(await client.delete(*keys))
        except redis.RedisError as exc:
            self._errors += 1
            self._mark_redis_failed(exc)
            return 0

    async def invalidate_lists(self, user_id: int) -> int:
        try:
            client = await self._get_redis()
            if client is None:
                if not self._allow_memory_fallback:
                    return 0
                prefix = f"wishlist:list:{user_id}:"
                keys = [k for k in self._memory_lists.keys() if k.startswith(prefix)]
                for k in keys:
                    self._memory_lists.pop(k, None)
                return len(keys)
            keyset = self._list_keys_set_key(user_id)
            try:
                keys = list(await client.smembers(keyset))
            except Exception:
                keys = []
            if not keys:
                scan_keys: list[str] = []
                async for key in client.scan_iter(match=f"wishlist:list:{user_id}:*"):
                    scan_keys.append(key)
                keys = scan_keys
            if not keys:
                await client.delete(keyset)
                return 0
            deleted = int(await client.delete(*keys, keyset))
            return deleted
        except redis.RedisError as exc:
            self._errors += 1
            self._mark_redis_failed(exc)
            return 0

    async def ping(self) -> bool:
        client = await self._get_redis()
        if client is None:
            return False
        try:
            await client.ping()
            return True
        except Exception as exc:
            self._mark_redis_failed(exc)
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
                "memory_fallback": self._allow_memory_fallback,
                "memory_items": len(self._memory_items),
                "memory_lists": len(self._memory_lists),
                "cooldown_s": max(0.0, self._cooldown_until_monotonic - time.monotonic()),
                "connect_failures": self._connect_failures,
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
