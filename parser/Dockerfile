# Официальный образ Playwright: Chromium и все системные зависимости уже внутри.
# Версия тега должна совпадать с версией playwright в requirements.txt (1.44.0).
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Браузеры уже есть в образе, но команда idempotent — гарантирует нужный Chromium
RUN playwright install chromium

COPY . .

# Railway передаёт порт через $PORT; локально — 8001
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}"]
