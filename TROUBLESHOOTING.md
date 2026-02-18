# Решение проблем запуска

## Проблема: Скрипт зависает при создании виртуального окружения

### Решение 1: Запустите создание venv вручную

Откройте новый терминал и выполните:

```bash
cd backend
python -m venv .venv
```

Если это работает, значит проблема в скрипте. Попробуйте использовать `start-simple.bat` после ручной установки.

### Решение 2: Проверьте Python

Убедитесь, что Python установлен правильно:

```bash
python --version
python -m pip --version
```

Если команды не работают, переустановите Python и убедитесь, что опция "Add Python to PATH" отмечена при установке.

### Решение 3: Используйте упрощенный скрипт

Если зависимости уже установлены, используйте `start-simple.bat`:

```bash
start-simple.bat
```

## Проблема: Кодировка отображается неправильно

Скрипт теперь использует UTF-8 кодировку (`chcp 65001`). Если проблема сохраняется:

1. Убедитесь, что терминал поддерживает UTF-8
2. Используйте PowerShell вместо CMD
3. Или используйте `start.py` (Python скрипт)

## Проблема: "Python not found"

### Windows:
1. Установите Python с https://www.python.org/
2. При установке отметьте "Add Python to PATH"
3. Перезапустите терминал

### Проверка:
```bash
python --version
```

Если не работает, попробуйте:
```bash
py --version
python3 --version
```

## Проблема: "Node.js not found"

1. Установите Node.js с https://nodejs.org/
2. Перезапустите терминал
3. Проверьте: `node --version`

## Проблема: Зависимости не устанавливаются

### Backend:
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
# или
source .venv/bin/activate  # Linux/Mac

pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

### Frontend:
```bash
cd frontend
npm install
```

## Проблема: Порт уже занят

### Backend (8000):
Измените порт в `start.bat`:
```bat
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Frontend (3000):
Создайте `frontend/.env.local`:
```
PORT=3001
```

## Проблема: Playwright не устанавливается

```bash
cd backend
.venv\Scripts\activate  # Windows
playwright install chromium
```

Если не работает:
```bash
python -m playwright install chromium
```

## Альтернативный запуск

Если скрипты не работают, запустите вручную:

### Терминал 1 (Backend):
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Терминал 2 (Frontend):
```bash
cd frontend
npm install
npm run dev
```

## Получение помощи

Если проблема не решена:

1. Проверьте логи в окнах консоли
2. Убедитесь, что все зависимости установлены
3. Попробуйте запустить сервисы вручную
4. Проверьте версии Python и Node.js
