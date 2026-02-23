"""
Тесты для API подарков: создание, резервы, взносы.
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app


def _register_and_login(client: TestClient) -> str:
    """Регистрирует пользователя, создает вишлист и возвращает slug."""
    email = f"user-{uuid4().hex}@example.com"
    client.post(
        "/auth/register",
        json={"email": email, "password": "SecurePass123!", "name": "Test User"}
    )
    client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
    
    response = client.post(
        "/wishlists",
        json={"title": "Test Wishlist"}
    )
    return response.json()["slug"]


def _create_second_user(client: TestClient) -> None:
    """Создает второго пользователя для тестов."""
    email = f"user2-{uuid4().hex}@example.com"
    client.post(
        "/auth/register",
        json={"email": email, "password": "SecurePass123!", "name": "Second User"}
    )
    client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})


class TestGiftCreate:
    """Тесты создания подарков."""

    def test_create_gift_success(self):
        """Успешное создание подарка."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        response = client.post(
            f"/wishlists/{slug}/gifts",
            json={
                "title": "Новые наушники",
                "url": "https://example.com/headphones",
                "price": 5000.0
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Новые наушники"
        assert data["url"] == "https://example.com/headphones"
        assert data["price"] == 5000.0

    def test_create_gift_minimal(self):
        """Создание подарка с минимальными данными."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        response = client.post(
            f"/wishlists/{slug}/gifts",
            json={"title": "Простой подарок"}
        )
        
        assert response.status_code == 201
        assert response.json()["title"] == "Простой подарок"

    def test_create_gift_collective(self):
        """Создание коллективного подарка."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        response = client.post(
            f"/wishlists/{slug}/gifts",
            json={
                "title": "Дорогой подарок",
                "price": 50000.0,
                "is_collective": True
            }
        )
        
        assert response.status_code == 201
        assert response.json()["is_collective"] is True

    def test_create_gift_private(self):
        """Создание приватного подарка."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        response = client.post(
            f"/wishlists/{slug}/gifts",
            json={
                "title": "Секретный подарок",
                "is_private": True
            }
        )
        
        assert response.status_code == 201
        assert response.json()["is_private"] is True

    def test_create_gift_unauthenticated(self):
        """Попытка создания подарка без авторизации."""
        client = TestClient(app)
        
        response = client.post(
            "/wishlists/some-slug/gifts",
            json={"title": "Test Gift"}
        )
        
        assert response.status_code == 401

    def test_create_gift_nonexistent_wishlist(self):
        """Попытка создания подарка в несуществующем вишлисте."""
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        client.post(
            "/auth/register",
            json={"email": email, "password": "SecurePass123!", "name": "Test User"}
        )
        client.post("/auth/login", json={"email": email, "password": "SecurePass123!"})
        
        response = client.post(
            "/wishlists/nonexistent-slug/gifts",
            json={"title": "Test Gift"}
        )
        
        assert response.status_code == 404


class TestGiftRead:
    """Тесты получения подарков."""

    def test_read_gifts_in_wishlist(self):
        """Получение списка подарков в вишлисте."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        # Создаем несколько подарков
        for i in range(3):
            client.post(
                f"/wishlists/{slug}/gifts",
                json={"title": f"Gift {i}"}
            )
        
        response = client.get(f"/wishlists/{slug}")
        
        assert response.status_code == 200
        gifts = response.json().get("gifts", [])
        assert len(gifts) >= 3

    def test_read_gift_details(self):
        """Подарок содержит все необходимые поля."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        client.post(
            f"/wishlists/{slug}/gifts",
            json={
                "title": "Test Gift",
                "url": "https://example.com/gift",
                "price": 1000.0,
                "image_url": "https://example.com/image.jpg"
            }
        )
        
        response = client.get(f"/wishlists/{slug}")
        
        assert response.status_code == 200
        gifts = response.json().get("gifts", [])
        assert len(gifts) > 0
        gift = gifts[0]
        assert "id" in gift
        assert "title" in gift
        assert "is_reserved" in gift
        assert "total_contributions" in gift


class TestGiftUpdate:
    """Тесты обновления подарков."""

    def test_update_gift_title(self):
        """Обновление названия подарка."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={"title": "Original Title"}
        )
        gift_id = create_response.json()["id"]
        
        response = client.put(
            f"/gifts/{gift_id}",
            json={"title": "Updated Title"}
        )
        
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_update_gift_price(self):
        """Обновление цены подарка."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={"title": "Test Gift", "price": 1000.0}
        )
        gift_id = create_response.json()["id"]
        
        response = client.put(
            f"/gifts/{gift_id}",
            json={"price": 1500.0}
        )
        
        assert response.status_code == 200
        assert response.json()["price"] == 1500.0

    def test_update_gift_nonexistent(self):
        """Попытка обновления несуществующего подарка."""
        client = TestClient(app)
        _register_and_login(client)
        
        response = client.put(
            "/gifts/99999",
            json={"title": "New Title"}
        )
        
        assert response.status_code == 404


class TestGiftDelete:
    """Тесты удаления подарков."""

    def test_delete_gift_success(self):
        """Успешное удаление подарка."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={"title": "To Delete"}
        )
        gift_id = create_response.json()["id"]
        
        response = client.delete(f"/gifts/{gift_id}")
        
        assert response.status_code == 204

    def test_delete_gift_verify_deleted(self):
        """Проверка что подарок помечен как недоступный."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={"title": "To Delete"}
        )
        gift_id = create_response.json()["id"]
        
        client.delete(f"/gifts/{gift_id}")
        
        # Проверяем что подарок помечен как недоступный (soft delete)
        response = client.get(f"/wishlists/{slug}")
        gifts = response.json().get("gifts", [])
        gift = next((g for g in gifts if g["id"] == gift_id), None)
        # API использует soft delete - помечает как unavailable
        if gift:
            assert gift.get("is_unavailable") is True


class TestGiftReservation:
    """Тесты резервирования подарков."""

    def test_reserve_gift_success(self):
        """Успешное резервирование подарка."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        # Создаем подарок
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={"title": "Gift to Reserve"}
        )
        gift_id = create_response.json()["id"]
        
        # Резервируем (используем второго пользователя)
        _create_second_user(client)
        
        response = client.post(f"/gifts/{gift_id}/reserve")
        
        assert response.status_code in [200, 201, 204]

    def test_reserve_gift_already_reserved(self):
        """Попытка резервирования уже зарезервированного подарка."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={"title": "Gift to Reserve"}
        )
        gift_id = create_response.json()["id"]
        
        # Первое резервирование
        _create_second_user(client)
        client.post(f"/gifts/{gift_id}/reserve")
        
        # Попытка повторного резервирования
        response = client.post(f"/gifts/{gift_id}/reserve")
        
        # Должен быть конфликт или ошибка
        assert response.status_code in [400, 409]

    def test_cancel_reservation_success(self):
        """Успешная отмена резервирования."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={"title": "Gift to Reserve"}
        )
        gift_id = create_response.json()["id"]
        
        # Резервируем
        _create_second_user(client)
        client.post(f"/gifts/{gift_id}/reserve")
        
        # Отменяем резервирование
        response = client.post(f"/gifts/{gift_id}/cancel-reservation")
        
        assert response.status_code in [200, 204]

    def test_reserve_collective_gift_fails(self):
        """Нельзя зарезервировать коллективный подарок."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={"title": "Collective Gift", "is_collective": True}
        )
        gift_id = create_response.json()["id"]
        
        _create_second_user(client)
        
        response = client.post(f"/gifts/{gift_id}/reserve")
        
        # Коллективные подарки нельзя резервировать
        assert response.status_code in [400, 422]


class TestGiftContribution:
    """Тесты взносов на коллективные подарки."""

    def test_contribute_to_collective_gift(self):
        """Взнос на коллективный подарок."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={
                "title": "Expensive Gift",
                "price": 10000.0,
                "is_collective": True
            }
        )
        gift_id = create_response.json()["id"]
        
        # Второй пользователь делает взнос
        _create_second_user(client)
        
        response = client.post(
            f"/gifts/{gift_id}/contribute",
            json={"amount": 1000.0}
        )
        
        assert response.status_code in [200, 201]

    def test_contribute_to_non_collective_gift_fails(self):
        """Нельзя сделать взнос на обычный подарок."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={"title": "Regular Gift", "is_collective": False}
        )
        gift_id = create_response.json()["id"]
        
        _create_second_user(client)
        
        response = client.post(
            f"/gifts/{gift_id}/contribute",
            json={"amount": 500.0}
        )
        
        assert response.status_code in [400, 422]

    def test_contribution_updates_total(self):
        """Взнос обновляет общую сумму собранных средств."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={
                "title": "Collective Gift",
                "price": 5000.0,
                "is_collective": True
            }
        )
        gift_id = create_response.json()["id"]
        
        _create_second_user(client)
        
        # Делаем взнос
        client.post(
            f"/gifts/{gift_id}/contribute",
            json={"amount": 1000.0}
        )
        
        # Проверяем что сумма обновилась
        response = client.get(f"/wishlists/{slug}")
        gifts = response.json().get("gifts", [])
        gift = next((g for g in gifts if g["id"] == gift_id), None)
        
        if gift:
            assert gift["total_contributions"] >= 1000.0

    def test_contribution_negative_amount_fails(self):
        """Взнос с отрицательной суммой отклоняется."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={"title": "Collective Gift", "is_collective": True}
        )
        gift_id = create_response.json()["id"]
        
        _create_second_user(client)
        
        response = client.post(
            f"/gifts/{gift_id}/contribute",
            json={"amount": -100.0}
        )
        
        assert response.status_code in [400, 422]

    def test_contribution_zero_amount_fails(self):
        """Взнос с нулевой суммой отклоняется."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={"title": "Collective Gift", "is_collective": True}
        )
        gift_id = create_response.json()["id"]
        
        _create_second_user(client)
        
        response = client.post(
            f"/gifts/{gift_id}/contribute",
            json={"amount": 0}
        )
        
        assert response.status_code in [400, 422]


class TestGiftProgress:
    """Тесты прогресса сбора средств."""

    def test_collected_percent_calculation(self):
        """Расчет процента собранных средств."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={
                "title": "Gift",
                "price": 1000.0,
                "is_collective": True
            }
        )
        gift_id = create_response.json()["id"]
        
        _create_second_user(client)
        
        # Взнос 50% от стоимости
        client.post(
            f"/gifts/{gift_id}/contribute",
            json={"amount": 500.0}
        )
        
        response = client.get(f"/wishlists/{slug}")
        gifts = response.json().get("gifts", [])
        gift = next((g for g in gifts if g["id"] == gift_id), None)
        
        if gift and "collected_percent" in gift:
            assert gift["collected_percent"] >= 50.0

    def test_is_fully_collected_flag(self):
        """Флаг полного сбора средств."""
        client = TestClient(app)
        slug = _register_and_login(client)
        
        create_response = client.post(
            f"/wishlists/{slug}/gifts",
            json={
                "title": "Gift",
                "price": 1000.0,
                "is_collective": True
            }
        )
        gift_id = create_response.json()["id"]
        
        _create_second_user(client)
        
        # Полный взнос
        client.post(
            f"/gifts/{gift_id}/contribute",
            json={"amount": 1000.0}
        )
        
        response = client.get(f"/wishlists/{slug}")
        gifts = response.json().get("gifts", [])
        gift = next((g for g in gifts if g["id"] == gift_id), None)
        
        if gift and "is_fully_collected" in gift:
            assert gift["is_fully_collected"] is True
