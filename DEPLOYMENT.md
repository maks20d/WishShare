# WishShare — Deployment Guide

Этот файл заменяет DEPLOY.md, DEPLOY_RENDER_VERCEL.md и старый DEPLOYMENT.md.

## Быстрый старт (локально)

```bash
cp .env.example .env
# Заполните .env (особенно JWT_SECRET_KEY — минимум 32 символа!)
docker compose up --build
```

Фронтенд: http://localhost:3000  
Бэкенд API: http://localhost:8000/docs

## Переменные окружения (обязательные)

| Переменная | Описание |
|---|---|
| `JWT_SECRET_KEY` | Случайная строка ≥32 символов. `openssl rand -hex 32` |
| `BACKEND_URL` | URL бэкенда (напр. `https://api.wishshare.app`) |
| `FRONTEND_URL` | URL фронтенда (напр. `https://wishshare.app`) |
| `BACKEND_CORS_ORIGINS` | Домен фронтенда через запятую |
| `POSTGRES_DSN` | `postgresql+asyncpg://user:pass@host:5432/db` (prod) |

## Production: Vercel (Frontend) + Render (Backend)

### Backend на Render

1. Создать Web Service из репозитория, корень: `backend/`
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Добавить env vars (см. таблицу выше)
5. Добавить PostgreSQL database addon

### Frontend на Vercel

1. Import репозитория, root directory: `frontend/`
2. Добавить переменные:
   - `NEXT_PUBLIC_BACKEND_URL` = URL вашего Render-сервиса

### Кросс-доменные cookie (CORS)

При разных доменах фронта и бэка обязательно:
- `BACKEND_CORS_ORIGINS` = `https://your-frontend.vercel.app`
- Backend должен быть на HTTPS (Render — автоматически)
- Запросы с `credentials: "include"` (уже настроено)
- Cookie: `SameSite=None; Secure` (уже настроено для `environment=production`)

### Установить `environment=production` на бэкенде

```
ENVIRONMENT=production
```

## Docker Compose (production)

```bash
docker compose -f docker-compose.yml up -d
```

## Генерация безопасного JWT_SECRET_KEY

```bash
openssl rand -hex 32
# или
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Миграции базы данных

```bash
cd backend
alembic upgrade head
```
