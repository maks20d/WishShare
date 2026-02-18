# WishShare - Руководство по развертыванию

## Обзор

WishShare поддерживает несколько способов развертывания:

1. **Локальная разработка** - с помощью улучшенного скрипта `start.py`
2. **Docker контейнеры** - для разработки и production
3. **CI/CD автоматизация** - через GitHub Actions
4. **Ручной деплой** - с помощью скриптов развертывания

## 🚀 Быстрый старт

### Локальная разработка

```bash
# Кроссплатформенный запуск
python start.py

# С дополнительными опциями
python start.py --production --with-postgres --auto-restart

# Проверка зависимостей
python start.py --check-only
```

### Docker разработка

```bash
# Development окружение
docker-compose -f docker-compose.dev.yml up -d

# Production окружение
docker-compose up -d
```

## 📋 Требования

### Для локальной разработки
- Python 3.11+
- Node.js 20.9+
- Git

### Для Docker развертывания
- Docker 20.10+
- Docker Compose 2.0+

### Для production
- PostgreSQL 15+
- Redis 7+
- Nginx (опционально)

## 🔧 Конфигурация

### Переменные окружения

Скопируйте `.env.example` в `.env` и настройте:

```bash
cp .env.example .env
```

**Основные настройки:**
```env
# База данных
POSTGRES_DSN=postgresql+asyncpg://user:pass@host:5432/db

# Redis
REDIS_DSN=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key-here

# Frontend публичные URL
NEXT_PUBLIC_API_BASE_URL=https://your-domain.com/api
NEXT_PUBLIC_WS_BASE_URL=wss://your-domain.com/ws

# OAuth (опционально)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

## 🐳 Docker развертывание

### Development

```bash
# Запуск development окружения
docker-compose -f docker-compose.dev.yml up -d

# Просмотр логов
docker-compose -f docker-compose.dev.yml logs -f

# Остановка
docker-compose -f docker-compose.dev.yml down
```

**Development включает:**
- Backend с hot reload
- Frontend с hot reload
- Redis для кэширования
- SQLite базу данных

### Production

```bash
# Запуск production окружения
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

**Production включает:**
- PostgreSQL базу данных
- Redis для кэширования
- Nginx reverse proxy
- Health checks
- Автоматический перезапуск

### Управление контейнерами

```bash
# Статус контейнеров
docker-compose ps

# Перезапуск сервисов
docker-compose restart

# Обновление образов
docker-compose pull
docker-compose up -d

# Очистка
docker system prune -f
```

## 🔄 CI/CD

### GitHub Actions

Проект включает готовый CI/CD пайплайн:

**Что делает пайплайн:**
1. **Тестирование** - автоматические тесты для backend и frontend
2. **Сборка** - создание Docker образов
3. **Security scan** - проверка уязвимостей
4. **Деплой** - автоматический деплой в staging/production

**Ветки:**
- `develop` → автоматический деплой в staging
- `main` → автоматический деплой в production

**Требования:**
- Настроить GitHub secrets для production
- Настроить доступ к серверу деплоя

## 📦 Скрипты развертывания

### Автоматический деплой

**Linux/Mac:**
```bash
# Деплой в staging
./deploy.sh staging

# Деплой в production
./deploy.sh production

# Пропустить тесты
./deploy.sh production --skip-tests

# Принудительный деплой (без бэкапа)
./deploy.sh production --force
```

**Windows:**
```batch
REM Деплой в staging
deploy.bat staging

REM Деплой в production
deploy.bat production
```

**Что делают скрипты:**
1. Проверяют зависимости
2. Создают бэкап базы данных (production)
3. Запускают тесты
4. Собирают Docker образы
5. Останавливают старые контейнеры
6. Запускают новые контейнеры
7. Проверяют здоровье сервисов
8. Очищают старые образы

## 🌐 Production настройка

### Подготовка сервера

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Настройка Nginx (опционально)

```nginx
# /etc/nginx/sites-available/wishshare
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### SSL сертификаты

```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d your-domain.com
```

## 🔍 Мониторинг

### Health checks

```bash
# Проверка здоровья сервисов
curl http://localhost:8000/health
curl http://localhost:3000

# Docker health checks
docker-compose ps
```

### Логи

```bash
# Просмотр всех логов
docker-compose logs -f

# Просмотр логов конкретного сервиса
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Метрики

Проект включает встроенные health checks:
- Backend: `/health` эндпоинт
- Frontend: HTTP статус 200
- Database: PostgreSQL health check
- Redis: Redis ping

## 🛠️ Устранение проблем

### Частые проблемы

**1. Порты заняты**
```bash
# Проверка занятых портов
netstat -tulpn | grep :8000
netstat -tulpn | grep :3000

# Изменение портов в docker-compose.yml
```

**2. Проблемы с базой данных**
```bash
# Проверка статуса PostgreSQL
docker-compose exec postgres pg_isready

# Сброс базы данных
docker-compose down -v
docker-compose up -d postgres
```

**3. Проблемы с Redis**
```bash
# Проверка Redis
docker-compose exec redis redis-cli ping

# Сброс Redis
docker-compose restart redis
```

**4. Проблемы с памятью**
```bash
# Очистка Docker
docker system prune -a -f

# Увеличение swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Резервное копирование

```bash
# Бэкап базы данных
docker exec wishshare-postgres pg_dump -U wishshare wishshare > backup.sql

# Восстановление
docker exec -i wishshare-postgres psql -U wishshare wishshare < backup.sql

# Автоматический бэкап
echo "0 2 * * * docker exec wishshare-postgres pg_dump -U wishshare wishshare > /backups/backup_\$(date +\%Y\%m\%d_\%H\%M\%S).sql" | crontab -
```

## 📚 Дополнительные ресурсы

### Документация
- [FastAPI документация](https://fastapi.tiangolo.com/)
- [Next.js документация](https://nextjs.org/docs)
- [Docker документация](https://docs.docker.com/)

### Мониторинг
- [Prometheus + Grafana](https://prometheus.io/docs/grafana/)
- [Docker monitoring](https://docs.docker.com/config/daemon/logging/)

### Безопасность
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Docker security](https://docs.docker.com/engine/security/)

## 🤝 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs -f`
2. Проверьте health checks: `curl http://localhost:8000/health`
3. Проверьте требования: `python start.py --check-only`
4. Создайте issue в GitHub репозитории

---

**Важно:** Перед production деплоем обязательно протестируйте на staging окружении и создайте бэкап данных.
