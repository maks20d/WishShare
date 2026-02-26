import json
from unittest.mock import AsyncMock

import pytest

from app.core.wishlist_cache import WishlistCache


@pytest.mark.anyio
async def test_get_returns_none_when_redis_unavailable():
    cache = WishlistCache(redis_dsn="redis://nonexistent:6379")
    result = await cache.get_item("slug", "public")
    assert result is None


@pytest.mark.anyio
async def test_set_returns_false_when_redis_unavailable():
    cache = WishlistCache(redis_dsn="redis://nonexistent:6379")
    ok = await cache.set_item("slug", "public", {"title": "Test"})
    assert ok is False


@pytest.mark.anyio
async def test_list_cache_roundtrip():
    cache = WishlistCache()
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps([{"slug": "a"}]))
    mock_redis.setex = AsyncMock(return_value=True)
    cache._redis = mock_redis

    stored = await cache.get_list(1, 20, 0)
    assert stored == [{"slug": "a"}]

    ok = await cache.set_list(1, 20, 0, [{"slug": "b"}])
    assert ok is True


@pytest.mark.anyio
async def test_invalidate_lists_handles_no_redis():
    cache = WishlistCache(redis_dsn="redis://nonexistent:6379")
    deleted = await cache.invalidate_lists(1)
    assert deleted == 0
