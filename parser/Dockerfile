# Официальный образ Playwright: Chromium и все системные зависимости уже внутри.
# Версия тега должна совпадать с версией playwright в requirements.txt (1.44.0).
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Браузеры уже есть в образе, но команда idempotent — гарантирует нужный Chromium
RUN playwright install chromium

COPY . .

# Слушаем на :: (IPv6) — приватная сеть Railway работает по IPv6.
# Двойной стек на Linux принимает и IPv4-mapped, поэтому локально тоже ОК.
CMD ["sh", "-c", "uvicorn main:app --host :: --port ${PORT:-8001}"]
