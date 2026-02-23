"""
Тесты для модуля безопасности: хэширование паролей, JWT токены.
"""
import pytest
from datetime import timedelta

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    create_password_reset_token,
    create_email_verification_token,
    decode_password_reset_token,
    decode_refresh_token,
    decode_email_verification_token,
    decode_access_token,
)


class TestPasswordHashing:
    """Тесты хэширования паролей."""

    def test_password_hash_creates_different_hashes(self):
        """Разные хэши для одинаковых паролей (salt)."""
        password = "MySecurePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
        assert hash1 != password
        assert hash2 != password

    def test_verify_password_correct(self):
        """Успешная проверка правильного пароля."""
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Неуспешная проверка неправильного пароля."""
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)
        
        assert verify_password("WrongPassword", hashed) is False
        assert verify_password("", hashed) is False
        assert verify_password(password.upper(), hashed) is False

    def test_password_hash_bcrypt_format(self):
        """Хэш имеет формат bcrypt."""
        password = "test123"
        hashed = get_password_hash(password)
        
        # bcrypt hashes start with $2b$
        assert hashed.startswith("$2b$")


class TestAccessToken:
    """Тесты access токенов."""

    def test_create_access_token_contains_subject(self):
        """Токен содержит subject."""
        user_id = "123"
        token = create_access_token(user_id)
        payload = decode_access_token(token)
        
        assert payload is not None
        assert payload.get("sub") == user_id

    def test_create_access_token_has_expiry(self):
        """Токен имеет срок действия."""
        user_id = "123"
        token = create_access_token(user_id)
        payload = decode_access_token(token)
        
        assert payload is not None
        assert "exp" in payload

    def test_create_access_token_custom_expiry(self):
        """Токен с кастомным сроком действия."""
        user_id = "123"
        token = create_access_token(user_id, expires_delta_minutes=60)
        payload = decode_access_token(token)
        
        assert payload is not None
        assert payload.get("sub") == user_id

    def test_decode_invalid_token_returns_none(self):
        """Декодирование невалидного токена возвращает None."""
        invalid_tokens = [
            "invalid.token.here",
            "",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
        ]
        
        for token in invalid_tokens:
            result = decode_access_token(token) if token else decode_access_token("")
            assert result is None


class TestRefreshToken:
    """Тесты refresh токенов."""

    def test_create_refresh_token_contains_subject(self):
        """Refresh токен содержит subject."""
        user_id = "456"
        token = create_refresh_token(user_id)
        payload = decode_refresh_token(token)
        
        assert payload is not None
        assert payload.get("sub") == user_id

    def test_refresh_token_has_type(self):
        """Refresh токен имеет тип 'refresh'."""
        user_id = "456"
        token = create_refresh_token(user_id)
        payload = decode_refresh_token(token)
        
        assert payload is not None
        assert payload.get("type") == "refresh"

    def test_decode_access_token_as_refresh_fails(self):
        """Access токен не может быть декодирован как refresh."""
        user_id = "456"
        access_token = create_access_token(user_id)
        payload = decode_refresh_token(access_token)
        
        # Access token не имеет type="refresh", поэтому должен вернуть None
        assert payload is None

    def test_refresh_token_custom_expiry(self):
        """Refresh токен с кастомным сроком действия."""
        user_id = "456"
        token = create_refresh_token(user_id, expires_delta_minutes=43200)  # 30 дней
        payload = decode_refresh_token(token)
        
        assert payload is not None
        assert payload.get("sub") == user_id


class TestPasswordResetToken:
    """Тесты токенов сброса пароля."""

    def test_create_password_reset_token_contains_email(self):
        """Токен сброса содержит email."""
        email = "user@example.com"
        token = create_password_reset_token(email)
        decoded = decode_password_reset_token(token)
        
        assert decoded == email

    def test_password_reset_token_has_type(self):
        """Токен сброса имеет тип 'password_reset'."""
        email = "user@example.com"
        token = create_password_reset_token(email)
        payload = decode_access_token(token)
        
        assert payload is not None
        assert payload.get("type") == "password_reset"

    def test_decode_invalid_password_reset_token(self):
        """Декодирование невалидного токена сброса."""
        # Access токен не является токеном сброса пароля
        access_token = create_access_token("123")
        result = decode_password_reset_token(access_token)
        
        assert result is None

    def test_decode_empty_password_reset_token(self):
        """Декодирование пустого токена сброса."""
        result = decode_password_reset_token("")
        assert result is None


class TestEmailVerificationToken:
    """Тесты токенов верификации email."""

    def test_create_email_verification_token_contains_email(self):
        """Токен верификации содержит email."""
        email = "verify@example.com"
        token = create_email_verification_token(email)
        decoded = decode_email_verification_token(token)
        
        assert decoded == email

    def test_email_verification_token_has_type(self):
        """Токен верификации имеет тип 'email_verify'."""
        email = "verify@example.com"
        token = create_email_verification_token(email)
        payload = decode_access_token(token)
        
        assert payload is not None
        assert payload.get("type") == "email_verify"

    def test_decode_invalid_email_verification_token(self):
        """Декодирование невалидного токена верификации."""
        # Access токен не является токеном верификации
        access_token = create_access_token("123")
        result = decode_email_verification_token(access_token)
        
        assert result is None

    def test_decode_empty_email_verification_token(self):
        """Декодирование пустого токена верификации."""
        result = decode_email_verification_token("")
        assert result is None


class TestTokenEdgeCases:
    """Граничные случаи для токенов."""

    def test_token_with_special_characters_in_subject(self):
        """Токен с спецсимволами в subject."""
        # user_id обычно числовой, но проверим строку
        user_id = "user-123_abc"
        token = create_access_token(user_id)
        payload = decode_access_token(token)
        
        assert payload is not None
        assert payload.get("sub") == user_id

    def test_token_with_unicode_email(self):
        """Токен с Unicode в email."""
        email = "пользователь@пример.рф"
        
        # Токен сброса пароля
        reset_token = create_password_reset_token(email)
        assert decode_password_reset_token(reset_token) == email
        
        # Токен верификации
        verify_token = create_email_verification_token(email)
        assert decode_email_verification_token(verify_token) == email

    def test_multiple_tokens_for_same_subject(self):
        """Разные токены для одного subject (разные exp)."""
        user_id = "123"
        token1 = create_access_token(user_id)
        token2 = create_access_token(user_id)
        
        # Токены должны быть разными из-за разного времени создания
        assert token1 != token2
        
        # Но оба должны декодироваться с одним subject
        assert decode_access_token(token1).get("sub") == user_id
        assert decode_access_token(token2).get("sub") == user_id
