#!/usr/bin/env bash
set -e

# Стартовый скрипт для прод-контейнера (Railway).

cd /var/www

# На проде .env не коммитится — создаём из примера, переменные придут из окружения Railway
if [ ! -f .env ]; then
  cp .env.example .env
fi

# Ключ приложения — генерируем, если не задан через переменную окружения
if [ -z "$APP_KEY" ]; then
  php artisan key:generate --force
fi

# По умолчанию используем SQLite (не нужен отдельный сервер БД).
# Файл живёт в контейнере; для демо этого достаточно.
export DB_CONNECTION="${DB_CONNECTION:-sqlite}"
if [ "$DB_CONNECTION" = "sqlite" ]; then
  mkdir -p database
  touch database/database.sqlite
  export DB_DATABASE=/var/www/database/database.sqlite
fi

# Накатываем миграции и сид-пользователя (idempotent: --force для прода)
php artisan migrate --force --seed

# Кэшируем конфиг и роуты для скорости
php artisan config:cache
php artisan route:cache

# Запускаем сервер на порту, который выдаёт Railway ($PORT)
php artisan serve --host=0.0.0.0 --port="${PORT:-8000}"
