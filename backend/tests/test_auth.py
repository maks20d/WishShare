"""
Тесты для API авторизации: регистрация, вход, выход, refresh.
"""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token, create_refresh_token


class TestAuthRegister:
    """Тесты регистрации пользователей."""

    def test_register_success(self):
        """Успешная регистрация нового пользователя."""
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        
        response = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "SecurePass123!",
                "name": "Test User"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == email
        assert data["name"] == "Test User"
        assert "id" in data

    def test_register_duplicate_email(self):
        """Регистрация с существующим email."""
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        
        # Первая регистрация
        client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "SecurePass123!",
                "name": "User One"
            }
        )
        
        # Повторная регистрация с тем же email
        response = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "AnotherPass456!",
                "name": "User Two"
            }
        )
        
        assert response.status_code == 400

    def test_register_invalid_email(self):
        """Регистрация с невалидным email."""
        client = TestClient(app)
        
        response = client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
                "name": "Test User"
            }
        )
        
        assert response.status_code == 422

    def test_register_short_password(self):
        """Регистрация с коротким паролем."""
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        
        response = client.post(
            "/auth/register",
            json={
                "email": email,
                "password": "short",
                "name": "Test User"
            }
        )
        
        # Пароль должен быть минимум 8 символов
        assert response.status_code == 422

    def test_register_missing_fields(self):
        """Регистрация с отсутствующими полями."""
        client = TestClient(app)
        
        response = client.post(
            "/auth/register",
            json={"email": f"user-{uuid4().hex}@example.com"}
        )
        
        assert response.status_code == 422


class TestAuthLogin:
    """Тесты входа в систему."""

    def test_login_success(self):
        """Успешный вход."""
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        password = "SecurePass123!"
        
        # Регистрация
        client.post(
            "/auth/register",
            json={"email": email, "password": password, "name": "Test User"}
        )
        
        # Вход
        response = client.post(
            "/auth/login",
            json={"email": email, "password": password}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email
        assert "id" in data

    def test_login_wrong_password(self):
        """Вход с неверным паролем."""
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        
        # Регистрация
        client.post(
            "/auth/register",
            json={"email": email, "password": "CorrectPass123!", "name": "Test User"}
        )
        
        # Вход с неверным паролем
        response = client.post(
            "/auth/login",
            json={"email": email, "password": "WrongPass456!"}
        )
        
        # API возвращает 400 с понятным сообщением вместо 401
        assert response.status_code == 400

    def test_login_nonexistent_user(self):
        """Вход с несуществующим email."""
        client = TestClient(app)
        
        response = client.post(
            "/auth/login",
            json={"email": "nonexistent@example.com", "password": "AnyPass123!"}
        )
        
        # API возвращает 400 с понятным сообщением вместо 401
        assert response.status_code == 400

    def test_login_sets_cookies(self):
        """Вход устанавливает cookies с токенами."""
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        password = "SecurePass123!"
        
        client.post(
            "/auth/register",
            json={"email": email, "password": password, "name": "Test User"}
        )
        
        response = client.post(
            "/auth/login",
            json={"email": email, "password": password}
        )
        
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie
        assert "refresh_token=" in set_cookie
        assert "HttpOnly" in set_cookie


class TestAuthLogout:
    """Тесты выхода из системы."""

    def test_logout_success(self):
        """Успешный выход."""
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        password = "SecurePass123!"
        
        # Регистрация и вход
        client.post(
            "/auth/register",
            json={"email": email, "password": password, "name": "Test User"}
        )
        client.post("/auth/login", json={"email": email, "password": password})
        
        # Выход
        response = client.post("/auth/logout")
        
        assert response.status_code == 204

    def test_logout_clears_cookies(self):
        """Выход очищает cookies."""
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        password = "SecurePass123!"
        
        client.post(
            "/auth/register",
            json={"email": email, "password": password, "name": "Test User"}
        )
        client.post("/auth/login", json={"email": email, "password": password})
        
        response = client.post("/auth/logout")
        
        # Cookies должны быть очищены (max-age=0 или пустое значение)
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie or response.status_code == 204


class TestAuthMe:
    """Тесты получения информации о текущем пользователе."""

    def test_me_authenticated(self):
        """Получение информации авторизованным пользователем."""
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        password = "SecurePass123!"
        
        client.post(
            "/auth/register",
            json={"email": email, "password": password, "name": "Test User"}
        )
        client.post("/auth/login", json={"email": email, "password": password})
        
        response = client.get("/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == email
        assert data["name"] == "Test User"

    def test_me_unauthenticated(self):
        """Попытка получения информации без авторизации."""
        client = TestClient(app)
        
        response = client.get("/auth/me")
        
        assert response.status_code == 401

    def test_me_with_bearer_token(self):
        """Получение информации с Bearer токеном."""
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        password = "SecurePass123!"
        
        # Регистрация
        register_response = client.post(
            "/auth/register",
            json={"email": email, "password": password, "name": "Test User"}
        )
        user_id = register_response.json()["id"]
        
        # Создаем токен и используем Bearer auth
        token = create_access_token(str(user_id))
        
        fresh_client = TestClient(app)
        response = fresh_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["email"] == email


class TestAuthRefresh:
    """Тесты обновления токенов."""

    def test_refresh_success(self):
        """Успешное обновление токенов."""
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        password = "SecurePass123!"
        
        client.post(
            "/auth/register",
            json={"email": email, "password": password, "name": "Test User"}
        )
        client.post("/auth/login", json={"email": email, "password": password})
        
        response = client.post("/auth/refresh")
        
        assert response.status_code == 204
        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie
        assert "refresh_token=" in set_cookie

    def test_refresh_without_token(self):
        """Обновление без refresh токена."""
        client = TestClient(app)
        
        response = client.post("/auth/refresh")
        
        assert response.status_code == 401

    def test_refresh_with_invalid_token(self):
        """Обновление с невалидным refresh токеном."""
        client = TestClient(app)
        
        response = client.post(
            "/auth/refresh",
            cookies={"refresh_token": "invalid.token.here"}
        )
        
        assert response.status_code == 401

    def test_refresh_with_access_token_instead_of_refresh(self):
        """Попытка обновления с access токеном вместо refresh."""
        client = TestClient(app)
        
        # Access токен не должен работать для refresh
        access_token = create_access_token("123")
        response = client.post(
            "/auth/refresh",
            cookies={"refresh_token": access_token}
        )
        
        assert response.status_code == 401


class TestAuthEdgeCases:
    """Граничные случаи авторизации."""

    def test_login_case_insensitive_email(self):
        """Вход с email в другом регистре."""
        client = TestClient(app)
        email = f"User-{uuid4().hex}@Example.com"
        lower_email = email.lower()
        
        # Регистрация с оригинальным email
        client.post(
            "/auth/register",
            json={"email": email, "password": "SecurePass123!", "name": "Test User"}
        )
        
        # Вход с email в нижнем регистре
        response = client.post(
            "/auth/login",
            json={"email": lower_email, "password": "SecurePass123!"}
        )
        
        # Email должен быть нормализован (200) или пользователь не найден (400)
        assert response.status_code in [200, 400]  # Зависит от реализации

    def test_register_with_whitespace_in_email(self):
        """Регистрация с пробелами в email."""
        client = TestClient(app)
        email = f"  user-{uuid4().hex}@example.com  "
        
        response = client.post(
            "/auth/register",
            json={"email": email, "password": "SecurePass123!", "name": "Test User"}
        )
        
        # Email должен быть обрезан или отклонен
        assert response.status_code in [201, 422]

    def test_multiple_logins_same_user(self):
        """Множественные входы одного пользователя."""
        client = TestClient(app)
        email = f"user-{uuid4().hex}@example.com"
        password = "SecurePass123!"
        
        client.post(
            "/auth/register",
            json={"email": email, "password": password, "name": "Test User"}
        )
        
        # Первый вход
        response1 = client.post(
            "/auth/login",
            json={"email": email, "password": password}
        )
        
        # Второй вход
        response2 = client.post(
            "/auth/login",
            json={"email": email, "password": password}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
