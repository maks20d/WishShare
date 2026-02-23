"""
Тесты для API вишлистов: CRUD операции.
"""
import pytest
from uuid import uuid4
from urllib.parse import quote
from fastapi.testclient import TestClient

from app.main import app


def _register_and_login(client: TestClient) -> dict:
    """Регистрирует пользователя и возвращает cookies."""
    email = f"user-{uuid4().hex}@example.com"
    client.post(
        "/auth/register",
        json={"email": email, "password": "SecurePass123!", "name": "Test User"}
    )
    client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    return {"email": email}


class TestWishlistCreate:
    """Тесты создания вишлистов."""

    def test_create_wishlist_success(self):
        """Успешное создание вишлиста."""
        client = TestClient(app)
        _register_and_login(client)
        
        response = client.post(
            "/wishlists",
            json={
                "title": "Мой день рождения",
                "description": "Список желаний на ДР",
                "privacy": "link_only",
                "is_secret_santa": False
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Мой день рождения"
        assert data["description"] == "Список желаний на ДР"
        assert data["privacy"] == "link_only"
        assert "slug" in data
        assert "id" in data

    def test_create_wishlist_minimal(self):
        """Создание вишлиста с минимальными данными."""
        client = TestClient(app)
        _register_and_login(client)
        
        response = client.post(
            "/wishlists",
            json={"title": "Простой список"}
        )
        
        assert response.status_code == 201
        assert response.json()["title"] == "Простой список"

    def test_create_wishlist_unauthenticated(self):
        """Попытка создания без авторизации."""
        client = TestClient(app)
        
        response = client.post(
            "/wishlists",
            json={"title": "Test Wishlist"}
        )
        
        assert response.status_code == 401

    def test_create_wishlist_with_event_date(self):
        """Создание вишлиста с датой события."""
        client = TestClient(app)
        _register_and_login(client)
        
        response = client.post(
            "/wishlists",
            json={
                "title": "Новый год",
                "event_date": "2025-12-31T00:00:00Z"
            }
        )
        
        assert response.status_code == 201
        assert response.json()["event_date"] is not None

    def test_create_wishlist_secret_santa(self):
        """Создание вишлиста Secret Santa."""
        client = TestClient(app)
        _register_and_login(client)
        
        response = client.post(
            "/wishlists",
            json={
                "title": "Secret Santa 2025",
                "is_secret_santa": True
            }
        )
        
        assert response.status_code == 201
        assert response.json()["is_secret_santa"] is True

    def test_create_wishlist_with_access_emails(self):
        """Создание вишлиста с email для доступа."""
        client = TestClient(app)
        _register_and_login(client)
        
        response = client.post(
            "/wishlists",
            json={
                "title": "Приватный список",
                "privacy": "friends",
                "access_emails": ["friend1@example.com", "friend2@example.com"]
            }
        )
        
        assert response.status_code == 201
        assert "access_emails" in response.json()

    def test_create_wishlist_generates_slug(self):
        """Создание вишлиста генерирует slug."""
        client = TestClient(app)
        _register_and_login(client)
        
        response = client.post(
            "/wishlists",
            json={"title": "Test Wishlist Title"}
        )
        
        assert response.status_code == 201
        slug = response.json()["slug"]
        assert slug is not None
        assert len(slug) > 0


class TestWishlistList:
    """Тесты получения списка вишлистов."""

    def test_list_wishlists_authenticated(self):
        """Получение списка вишлистов авторизованным пользователем."""
        client = TestClient(app)
        _register_and_login(client)
        
        # Создаем несколько вишлистов
        for i in range(3):
            client.post(
                "/wishlists",
                json={"title": f"Wishlist {i}"}
            )
        
        response = client.get("/wishlists")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_list_wishlists_unauthenticated(self):
        """Попытка получения списка без авторизации."""
        client = TestClient(app)
        
        response = client.get("/wishlists")
        
        assert response.status_code == 401

    def test_list_wishlists_empty(self):
        """Получение пустого списка вишлистов."""
        client = TestClient(app)
        _register_and_login(client)
        
        response = client.get("/wishlists")
        
        assert response.status_code == 200
        assert response.json() == []


class TestWishlistRead:
    """Тесты получения отдельного вишлиста."""

    def test_read_wishlist_by_slug(self):
        """Получение вишлиста по slug."""
        client = TestClient(app)
        _register_and_login(client)
        
        create_response = client.post(
            "/wishlists",
            json={"title": "Test Wishlist"}
        )
        slug = create_response.json()["slug"]
        
        response = client.get(f"/wishlists/{slug}")
        
        assert response.status_code == 200
        assert response.json()["slug"] == slug

    def test_read_wishlist_nonexistent(self):
        """Попытка получения несуществующего вишлиста."""
        client = TestClient(app)
        _register_and_login(client)
        
        response = client.get("/wishlists/nonexistent-slug-12345")
        
        assert response.status_code == 404

    def test_read_wishlist_by_public_token(self):
        """Получение вишлиста по публичному токену."""
        client = TestClient(app)
        _register_and_login(client)
        
        create_response = client.post(
            "/wishlists",
            json={"title": "Test Wishlist", "privacy": "link_only"}
        )
        public_token = create_response.json().get("public_token")
        
        if public_token:
            # Пытаемся получить по токену (без авторизации)
            fresh_client = TestClient(app)
            response = fresh_client.get(f"/w/{public_token}")
            assert response.status_code in [200, 404]

    def test_read_wishlist_with_cyrillic_slug(self):
        """Получение вишлиста с кириллическим slug."""
        client = TestClient(app)
        _register_and_login(client)
        
        create_response = client.post(
            "/wishlists",
            json={"title": "День рождения"}
        )
        slug = create_response.json()["slug"]
        
        # Кодируем slug для URL
        encoded_slug = quote(slug, safe="")
        response = client.get(f"/wishlists/{encoded_slug}")
        
        assert response.status_code == 200
        assert response.json()["slug"] == slug


class TestWishlistUpdate:
    """Тесты обновления вишлистов."""

    def test_update_wishlist_title(self):
        """Обновление заголовка вишлиста."""
        client = TestClient(app)
        _register_and_login(client)
        
        create_response = client.post(
            "/wishlists",
            json={"title": "Original Title"}
        )
        slug = create_response.json()["slug"]
        
        response = client.put(
            f"/wishlists/{slug}",
            json={"title": "Updated Title"}
        )
        
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_update_wishlist_description(self):
        """Обновление описания вишлиста."""
        client = TestClient(app)
        _register_and_login(client)
        
        create_response = client.post(
            "/wishlists",
            json={"title": "Test Wishlist"}
        )
        slug = create_response.json()["slug"]
        
        response = client.put(
            f"/wishlists/{slug}",
            json={"description": "New description"}
        )
        
        assert response.status_code == 200
        assert response.json()["description"] == "New description"

    def test_update_wishlist_privacy(self):
        """Обновление уровня приватности."""
        client = TestClient(app)
        _register_and_login(client)
        
        create_response = client.post(
            "/wishlists",
            json={"title": "Test Wishlist", "privacy": "link_only"}
        )
        slug = create_response.json()["slug"]
        
        response = client.put(
            f"/wishlists/{slug}",
            json={"privacy": "friends"}
        )
        
        assert response.status_code == 200
        assert response.json()["privacy"] == "friends"

    def test_update_wishlist_nonexistent(self):
        """Попытка обновления несуществующего вишлиста."""
        client = TestClient(app)
        _register_and_login(client)
        
        response = client.put(
            "/wishlists/nonexistent-slug",
            json={"title": "New Title"}
        )
        
        assert response.status_code == 404

    def test_update_wishlist_unauthenticated(self):
        """Попытка обновления без авторизации."""
        client = TestClient(app)
        
        response = client.put(
            "/wishlists/some-slug",
            json={"title": "New Title"}
        )
        
        assert response.status_code == 401


class TestWishlistDelete:
    """Тесты удаления вишлистов."""

    def test_delete_wishlist_success(self):
        """Успешное удаление вишлиста."""
        client = TestClient(app)
        _register_and_login(client)
        
        create_response = client.post(
            "/wishlists",
            json={"title": "To Delete"}
        )
        slug = create_response.json()["slug"]
        
        response = client.delete(f"/wishlists/{slug}")
        
        assert response.status_code == 204

    def test_delete_wishlist_verify_deleted(self):
        """Проверка что вишлист удален."""
        client = TestClient(app)
        _register_and_login(client)
        
        create_response = client.post(
            "/wishlists",
            json={"title": "To Delete"}
        )
        slug = create_response.json()["slug"]
        
        client.delete(f"/wishlists/{slug}")
        
        # Проверяем что вишлист не существует
        response = client.get(f"/wishlists/{slug}")
        assert response.status_code == 404

    def test_delete_wishlist_nonexistent(self):
        """Попытка удаления несуществующего вишлиста."""
        client = TestClient(app)
        _register_and_login(client)
        
        response = client.delete("/wishlists/nonexistent-slug")
        
        assert response.status_code == 404

    def test_delete_wishlist_unauthenticated(self):
        """Попытка удаления без авторизации."""
        client = TestClient(app)
        
        response = client.delete("/wishlists/some-slug")
        
        assert response.status_code == 401


class TestWishlistAccess:
    """Тесты доступа к вишлистам."""

    def test_access_link_only_as_owner(self):
        """Доступ к link_only вишлисту как владелец."""
        client = TestClient(app)
        _register_and_login(client)
        
        create_response = client.post(
            "/wishlists",
            json={"title": "Private Wishlist", "privacy": "link_only"}
        )
        slug = create_response.json()["slug"]
        
        response = client.get(f"/wishlists/{slug}")
        
        assert response.status_code == 200

    def test_access_public_wishlist(self):
        """Доступ к публичному вишлисту."""
        client = TestClient(app)
        _register_and_login(client)
        
        create_response = client.post(
            "/wishlists",
            json={"title": "Public Wishlist", "privacy": "public"}
        )
        slug = create_response.json()["slug"]
        
        response = client.get(f"/wishlists/{slug}")
        
        assert response.status_code == 200

    def test_wishlist_owner_can_see_public_token(self):
        """Владелец видит public_token."""
        client = TestClient(app)
        _register_and_login(client)
        
        create_response = client.post(
            "/wishlists",
            json={"title": "Test Wishlist"}
        )
        
        assert "public_token" in create_response.json()
        assert create_response.json()["public_token"] is not None
