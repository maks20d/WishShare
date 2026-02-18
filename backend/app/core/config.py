from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "WishShare API"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    backend_cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database configuration
    # For development: sqlite+aiosqlite:///./wishshare.db
    # For production: postgresql+asyncpg://user:password@localhost/wishshare
    postgres_dsn: str = "postgresql+asyncpg://wishshare:password@localhost:5432/wishshare"
    
    # For PostgreSQL configuration, use:
    # postgres_user: str = "wishshare"
    # postgres_password: str = "password"
    # postgres_host: str = "localhost"
    # postgres_port: int = 5432
    # postgres_db: str = "wishshare"
    # And construct DSN as: postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}
    
    redis_dsn: str = "redis://localhost:6379/0"

    access_token_expire_minutes: int = 60 * 24 * 7
    password_reset_token_expire_minutes: int = 30
    jwt_secret_key: str = "CHANGE_ME"
    jwt_algorithm: str = "HS256"

    # OAuth settings
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""

    # SMTP settings (optional, for password reset emails)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@wishshare.local"
    smtp_use_tls: bool = True

    # Parser/browser fallback (for anti-bot protected marketplaces)
    parser_browser_fallback: bool = True
    parser_browser_domains: str = (
        "ozon.ru,wildberries.ru,wb.ru,lamoda.ru,dns-shop.ru,"
        "market.yandex.ru,yandex.ru,aliexpress.com,aliexpress.ru,amazon.com,amazon.ru"
    )
    parser_browser_timeout_ms: int = 45000
    log_level: str = "INFO"
    log_file: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
