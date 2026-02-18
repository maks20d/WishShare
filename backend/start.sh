#!/bin/bash
set -e

echo "Running database migrations..."
if [ -f "alembic.ini" ] && [ -d "alembic/versions" ]; then
  alembic upgrade head
else
  echo "Alembic config not found; skipping migrations."
fi
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
