# =========================================================================
# Корневой Dockerfile для деплоя (Railway): собирает Vue-фронт и упаковывает
# его внутрь Laravel. На выходе один контейнер: API + статика SPA на одном порту.
# =========================================================================

# --- Стадия 1: сборка фронтенда (Vue) ---
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
# Собираем статику. baseURL API = /api (тот же домен), поэтому extra-env не нужен.
RUN npm run build

# --- Стадия 2: бэкенд (Laravel) + готовая статика фронта ---
# PHP 8.4: composer.lock собран на PHP 8.5 и требует Symfony-пакеты для PHP >=8.4
FROM php:8.4-cli

# Системные зависимости и расширения PHP
RUN apt-get update && apt-get install -y \
    git curl zip unzip libpng-dev libonig-dev libxml2-dev libsqlite3-dev \
    && docker-php-ext-install pdo_mysql pdo_sqlite mbstring exif pcntl bcmath gd \
    && rm -rf /var/lib/apt/lists/*

COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /var/www
COPY backend/ ./
RUN composer install --no-interaction --no-dev --optimize-autoloader

# Кладём собранный Vue в public/ — Laravel отдаёт его как SPA
COPY --from=frontend /app/dist/ ./public/

# Стартовый скрипт: подготовка БД и запуск сервера
COPY deploy/start.sh /start.sh
RUN chmod +x /start.sh

RUN chown -R www-data:www-data storage bootstrap/cache

CMD ["/start.sh"]
