import json
import os
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "WishShare API"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    environment: str = "local"
    backend_cors_origins_raw: str = ""  # Comma-separated or JSON array
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "allow",
    }

    @property
    def backend_cors_origins(self) -> list[str]:
        """Parse CORS origins from raw string."""
        raw = os.getenv("BACKEND_CORS_ORIGINS", self.backend_cors_origins_raw).strip()
        if not raw:
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed if str(item).strip()]
            except Exception:
                pass
        return [item.strip() for item in raw.split(",") if item.strip()]

    postgres_dsn: str = "sqlite+aiosqlite:///./wishshare.db"
    redis_dsn: str = "redis://localhost:6379/0"

    access_token_expire_minutes: int = 60 * 24 * 7
    refresh_token_expire_minutes: int = 60 * 24 * 30
    password_reset_token_expire_minutes: int = 30
    jwt_secret_key: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"

    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@wishshare.local"
    smtp_use_tls: bool = True
    email_notifications_enabled: bool = True

    rate_limit_enabled: bool = True
    rate_limit_requests: int = 10
    rate_limit_window_seconds: int = 60
    rate_limit_login_requests: int = 5

    parser_browser_fallback: bool = True
    parser_browser_domains: str = (
        "ozon.ru,wildberries.ru,wb.ru,lamoda.ru,dns-shop.ru,"
        "market.yandex.ru,yandex.ru,aliexpress.com,aliexpress.ru,amazon.com,amazon.ru"
    )
    parser_browser_timeout_ms: int = 45000
    log_level: str = "INFO"
    log_file: str = ""

    sentry_dsn: str | None = None


settings = Settings()
