# Render + Vercel деплой (готовый чеклист)

## 1. Репозиторий
- Запушить проект в GitHub/GitLab/Bitbucket.
- В корне репозитория присутствуют `backend/`, `frontend/`, `render.yaml`.

## 2. Backend на Render
1. Render → New → Blueprint → выбрать репозиторий.
2. Подтвердить создание сервиса `wishshare-backend`.
3. Задать переменные окружения:

```
POSTGRES_DSN=postgresql+asyncpg://user:pass@host:5432/db
REDIS_DSN=redis://:password@host:6379/0
JWT_SECRET_KEY=случайная_строка
BACKEND_URL=https://<your-backend>.onrender.com
FRONTEND_URL=https://<your-frontend>.vercel.app
BACKEND_CORS_ORIGINS=https://<your-frontend>.vercel.app
```

4. Дождаться деплоя и проверить:

```
https://<your-backend>.onrender.com/health
```

## 3. Frontend на Vercel
1. Vercel → New Project → выбрать репозиторий.
2. Root Directory: `frontend`.
3. Environment Variables:

```
NEXT_PUBLIC_API_BASE_URL=https://<your-backend>.onrender.com
NEXT_PUBLIC_WS_BASE_URL=wss://<your-backend>.onrender.com/ws
```

4. Deploy и открыть `https://<your-frontend>.vercel.app`.

## 4. Финальная сверка
- Логин/регистрация работают и создают cookie.
- `/dashboard` доступен после логина.
- `/wishlist/<slug>` грузится и получает данные.
- WebSocket подключается к `wss://<your-backend>.onrender.com/ws/<slug>`.

## 5. Обновления
- Любой push в main запускает автодеплой на Render и Vercel.
