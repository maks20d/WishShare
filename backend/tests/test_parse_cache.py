"""
Тесты для модуля кэширования парсинга URL.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.core.parse_cache import ParseCache


class TestParseCacheNormalizeUrl:
    """Тесты нормализации URL."""

    def test_normalize_url_removes_trailing_slash(self):
        """Удаление trailing slash."""
        cache = ParseCache()
        
        assert cache._normalize_url("https://example.com/") == "https://example.com"
        assert cache._normalize_url("https://example.com/path/") == "https://example.com/path"

    def test_normalize_url_removes_utm_params(self):
        """Удаление UTM параметров."""
        cache = ParseCache()
        
        url = "https://example.com/product?utm_source=google&utm_medium=cpc"
        normalized = cache._normalize_url(url)
        
        assert "utm_source" not in normalized
        assert "utm_medium" not in normalized

    def test_normalize_url_removes_multiple_tracking_params(self):
        """Удаление различных tracking параметров."""
        cache = ParseCache()
        
        tracking_params = [
            "utm_source",
            "utm_medium", 
            "utm_campaign",
            "utm_term",
            "utm_content",
            "at",
            "__rr",
            "_openstat",
            "from",
            "ref"
        ]
        
        for param in tracking_params:
            url = f"https://example.com?{param}=value"
            normalized = cache._normalize_url(url)
            assert param not in normalized, f"Parameter {param} should be removed"

    def test_normalize_url_preserves_other_params(self):
        """Сохранение обычных параметров."""
        cache = ParseCache()
        
        url = "https://example.com/product?id=123&category=electronics"
        normalized = cache._normalize_url(url)
        
        assert "id=123" in normalized
        assert "category=electronics" in normalized

    def test_normalize_url_handles_mixed_params(self):
        """Обработка смешанных параметров."""
        cache = ParseCache()
        
        url = "https://example.com?id=123&utm_source=google&category=tech"
        normalized = cache._normalize_url(url)
        
        assert "id=123" in normalized
        assert "category=tech" in normalized
        assert "utm_source" not in normalized


class TestParseCacheKeyGeneration:
    """Тесты генерации ключей кэша."""

    def test_get_key_returns_consistent_format(self):
        """Ключ имеет формат parse:hash."""
        cache = ParseCache()
        
        key = cache._get_key("https://example.com")
        
        assert key.startswith("parse:")
        assert len(key) > 6  # "parse:" + md5 hash

    def test_get_key_same_for_normalized_urls(self):
        """Одинаковые ключи для нормализованных URL."""
        cache = ParseCache()
        
        url1 = "https://example.com/product"
        url2 = "https://example.com/product?utm_source=google"
        
        key1 = cache._get_key(url1)
        key2 = cache._get_key(url2)
        
        assert key1 == key2

    def test_get_key_different_for_different_urls(self):
        """Разные ключи для разных URL."""
        cache = ParseCache()
        
        key1 = cache._get_key("https://example.com/product1")
        key2 = cache._get_key("https://example.com/product2")
        
        assert key1 != key2


class TestParseCacheGet:
    """Тесты получения данных из кэша."""

    @pytest.mark.anyio
    async def test_get_returns_none_when_redis_unavailable(self):
        """Возвращает None когда Redis недоступен."""
        cache = ParseCache(redis_dsn="redis://nonexistent:6379")
        
        result = await cache.get("https://example.com")
        
        assert result is None

    @pytest.mark.anyio
    async def test_get_increments_misses_on_cache_miss(self):
        """Увеличивает счетчик промахов при отсутствии в кэше."""
        cache = ParseCache(redis_dsn="redis://nonexistent:6379")
        
        initial_misses = cache._misses
        await cache.get("https://example.com")
        
        assert cache._misses == initial_misses + 1


class TestParseCacheSet:
    """Тесты сохранения данных в кэш."""

    @pytest.mark.anyio
    async def test_set_returns_false_when_redis_unavailable(self):
        """Возвращает False когда Redis недоступен."""
        cache = ParseCache(redis_dsn="redis://nonexistent:6379")
        
        result = await cache.set("https://example.com", {"title": "Test"})
        
        assert result is False

    @pytest.mark.anyio
    async def test_set_adds_cached_at_timestamp(self):
        """Добавляет timestamp при сохранении."""
        cache = ParseCache()
        
        # Мокаем Redis
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock(return_value=True)
        cache._redis = mock_redis
        
        data = {"title": "Test Product"}
        await cache.set("https://example.com", data)
        
        # Проверяем что setex был вызван
        assert mock_redis.setex.called
        call_args = mock_redis.setex.call_args
        stored_data = json.loads(call_args[0][2])  # Третий аргумент - JSON данные
        
        assert "_cached_at" in stored_data


class TestParseCacheDelete:
    """Тесты удаления данных из кэша."""

    @pytest.mark.anyio
    async def test_delete_returns_false_when_redis_unavailable(self):
        """Возвращает False когда Redis недоступен."""
        cache = ParseCache(redis_dsn="redis://nonexistent:6379")
        
        result = await cache.delete("https://example.com")
        
        assert result is False

    @pytest.mark.anyio
    async def test_delete_calls_redis_delete(self):
        """Вызывает delete на Redis."""
        cache = ParseCache()
        
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=1)
        cache._redis = mock_redis
        
        result = await cache.delete("https://example.com")
        
        assert result is True
        assert mock_redis.delete.called


class TestParseCacheClearAll:
    """Тесты очистки всего кэша."""

    @pytest.mark.anyio
    async def test_clear_all_returns_zero_when_redis_unavailable(self):
        """Возвращает 0 когда Redis недоступен."""
        cache = ParseCache(redis_dsn="redis://nonexistent:6379")
        
        result = await cache.clear_all()
        
        assert result == 0

    @pytest.mark.anyio
    async def test_clear_all_scans_parse_keys(self):
        """Сканирует ключи с префиксом parse:."""
        cache = ParseCache()
        
        mock_redis = AsyncMock()
        # Create async iterator for scan_iter
        async def async_scan_iter(*args, **kwargs):
            for key in ["parse:abc123", "parse:def456"]:
                yield key
        mock_redis.scan_iter = async_scan_iter
        mock_redis.delete = AsyncMock(return_value=2)
        cache._redis = mock_redis
        
        result = await cache.clear_all()
        
        assert result == 2


class TestParseCacheStats:
    """Тесты статистики кэша."""

    @pytest.mark.anyio
    async def test_get_stats_returns_basic_stats(self):
        """Возвращает базовую статистику."""
        cache = ParseCache(redis_dsn="redis://nonexistent:6379")
        
        stats = await cache.get_stats()
        
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "redis_connected" in stats
        assert "enabled" in stats

    @pytest.mark.anyio
    async def test_get_stats_calculates_hit_rate(self):
        """Вычисляет процент попаданий."""
        cache = ParseCache(redis_dsn="redis://nonexistent:6379")
        
        cache._hits = 80
        cache._misses = 20
        
        stats = await cache.get_stats()
        
        assert stats["hit_rate"] == 80.0

    @pytest.mark.anyio
    async def test_get_stats_handles_zero_requests(self):
        """Обрабатывает случай отсутствия запросов."""
        cache = ParseCache(redis_dsn="redis://nonexistent:6379")
        
        cache._hits = 0
        cache._misses = 0
        
        stats = await cache.get_stats()
        
        assert stats["hit_rate"] == 0


class TestParseCacheClose:
    """Тесты закрытия соединения."""

    @pytest.mark.anyio
    async def test_close_handles_none_redis(self):
        """Обрабатывает None Redis соединение."""
        cache = ParseCache()
        cache._redis = None
        
        # Не должно выбросить исключение
        await cache.close()
        
        assert cache._redis is None

    @pytest.mark.anyio
    async def test_close_calls_redis_close(self):
        """Вызывает close на Redis соединении."""
        cache = ParseCache()
        
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        cache._redis = mock_redis
        
        await cache.close()
        
        assert mock_redis.close.called
        assert cache._redis is None


class TestParseCacheIntegration:
    """Интеграционные тесты кэша."""

    @pytest.mark.anyio
    async def test_cache_workflow_without_redis(self):
        """Полный цикл работы без Redis."""
        cache = ParseCache(redis_dsn="redis://nonexistent:6379")
        
        # Get должен вернуть None
        result = await cache.get("https://example.com")
        assert result is None
        
        # Set должен вернуть False
        success = await cache.set("https://example.com", {"title": "Test"})
        assert success is False
        
        # Delete должен вернуть False
        deleted = await cache.delete("https://example.com")
        assert deleted is False
        
        # Stats должны показывать misses
        stats = await cache.get_stats()
        assert stats["misses"] >= 1
        assert stats["redis_connected"] is False

    def test_default_ttl_value(self):
        """Значение TTL по умолчанию."""
        cache = ParseCache()
        
        assert cache._default_ttl == 24 * 60 * 60  # 24 часа

    def test_custom_ttl_value(self):
        """Кастомное значение TTL."""
        cache = ParseCache(default_ttl=3600)
        
        assert cache._default_ttl == 3600
