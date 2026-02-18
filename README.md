# WishShare

Социальный вишлист с приватными ссылками, коллективными сборами и realtime‑обновлениями.

## Возможности
- Регистрация и вход по email
- Создание и управление вишлистами
- Подарки с резервом или коллективным сбором
- Приватность: по ссылке, для друзей, публичный
- Realtime обновления через WebSocket

## Технологии
- Frontend: Next.js 16, React 19, TypeScript, Zustand, TanStack Query, Tailwind CSS
- Backend: FastAPI, SQLAlchemy (async), SQLite/PostgreSQL, JWT

## Установка

### Требования
- Python 3.11+
- Node.js 20+

### Быстрый старт (Windows)
```bash
run.bat
```

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Открыть: http://localhost:3000

## Конфигурация
Скопируйте пример и обновите значения:
```bash
copy .env.example .env
```

Ключевые переменные:
- BACKEND_URL, FRONTEND_URL
- BACKEND_CORS_ORIGINS
- JWT_SECRET_KEY

## Куки авторизации и кросс-домен
При раздельном хостинге фронтенда и бэкенда (например, Vercel + Render) для cookie `access_token` требуется:
- BACKEND_URL и FRONTEND_URL должны быть https
- BACKEND_CORS_ORIGINS должен включать домен фронтенда
- Запросы должны отправляться с `credentials: "include"`

Если фронтенд работает на другом домене и используется http, браузер заблокирует cookie.

## Примеры использования
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"user@example.com\",\"password\":\"Test1234!\",\"name\":\"User\"}"
```

```bash
curl -X GET http://localhost:8000/wishlists
```

## Тесты
```bash
cd frontend
npm run test
```

```bash
cd backend
python -m pytest
```
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

### PostgreSQL для production

Вместо SQLite используйте PostgreSQL:

```bash
# Установка PostgreSQL
# macOS: brew install postgresql
# Ubuntu: sudo apt install postgresql
# Windows: https://www.postgresql.org/download/windows/

# Создание базы для приложения
createdb wishshare

# Обновление .env
POSTGRES_DSN=postgresql+asyncpg://postgres:password@localhost:5432/wishshare
```

## TODO / Планы развития

- [ ] Email уведомления (новые вклады, резервы)
- [ ] Система комментариев к подаркам
- [ ] Уведомления в реальном времени изнутри приложения
- [ ] Поддержка установки приложения (PWA)
- [ ] Мобильное приложение (React Native)
- [ ] Analytics и метрики использования
- [ ] Интеграция с платежными системами (для благотворительности)
- [ ] Сортировка и фильтрация вишлистов
- [ ] Импорт вишлистов из других источников

## Лицензия

MIT License - см. LICENSE файл для деталей

## Связь

Для вопросов, багов или предложений создавайте issues в репозитории.
