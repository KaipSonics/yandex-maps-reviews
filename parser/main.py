"""
Парсер Яндекс.Карт на Python + Playwright.

Почему Playwright, а не requests/BeautifulSoup:
- Яндекс загружает отзывы динамически через JavaScript (бесконечная прокрутка)
- Playwright запускает настоящий браузер, который выполняет JS как обычный пользователь
- Яндекс защищается от ботов по заголовкам и поведению — Playwright выглядит как человек

Почему отдельный сервис, а не часть Laravel:
- PHP плохо управляет браузерными процессами
- Python + Playwright — стандарт индустрии для такого парсинга
- Laravel просто делает HTTP-запрос сюда и получает готовые данные
"""

import re
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

app = FastAPI()


class ParseRequest(BaseModel):
    url: str


class Review(BaseModel):
    author: str
    date: str
    text: str
    rating: int


class ParseResult(BaseModel):
    organization_name: str
    average_rating: float
    ratings_count: int
    reviews_count: int
    reviews: list[Review]


def extract_org_id(url: str) -> str | None:
    """
    Пытается извлечь ID организации из полного URL вида
    https://yandex.ru/maps/org/mcdonalds/12345678/...
    Для короткой ссылки (/maps/-/CODE) вернёт None — ID определим
    уже после перехода по редиректу, из итогового адреса страницы.
    """
    match = re.search(r'/org/[^/]+/(\d+)', url)
    return match.group(1) if match else None


@app.post("/parse", response_model=ParseResult)
async def parse_reviews(request: ParseRequest):
    """
    Принимает URL карточки организации, возвращает все отзывы.
    Laravel вызывает этот эндпоинт через HTTP POST.
    """
    try:
        result = await scrape_yandex_maps(request.url)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")


async def scrape_yandex_maps(url: str) -> ParseResult:
    """
    Основная функция парсинга.

    Стратегия обхода защиты Яндекса:
    1. Запускаем реальный Chromium (не headless-detection)
    2. Эмулируем реального пользователя: user-agent, viewport, locale
    3. Скроллим страницу — имитируем поведение человека
    4. Ждём загрузки каждой порции отзывов
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',  # скрываем что это бот
            ]
        )

        context = await browser.new_context(
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            ),
            viewport={'width': 1280, 'height': 800},
            locale='ru-RU',
        )

        page = await context.new_page()

        # Шаг 1. Переходим по исходной ссылке (полной ИЛИ короткой «Поделиться»).
        # Короткая сама редиректит на полный /org/.../id — поэтому сначала открываем как есть.
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)  # даём отработать редиректу короткой ссылки

        final_url = page.url

        # Детект антибота: Яндекс с IP дата-центра часто отдаёт капчу
        if 'showcaptcha' in final_url or 'captcha' in final_url.lower():
            raise ValueError(
                "Яндекс показал капчу (защита от ботов). Скорее всего заблокирован IP "
                "сервера-дата-центра. Нужен резидентный прокси или запуск парсера с другого IP."
            )

        # Шаг 2. Из итогового адреса достаём ID и идём на вкладку отзывов
        org_id = extract_org_id(final_url)
        if not org_id:
            # Не нашли /org/.../id — значит это не карточка организации
            page_title = await page.title()
            raise ValueError(
                f"Не удалось определить организацию по ссылке. Итоговый адрес: {final_url}. "
                f"Заголовок страницы: «{page_title}». Возможно, капча или неверная ссылка."
            )

        # Базовый адрес карточки + вкладка отзывов
        base = re.match(r'(https?://[^/]+/maps/org/[^/]+/\d+)', final_url)
        reviews_url = (base.group(1) if base else final_url.rstrip('/')) + '/reviews/'
        await page.goto(reviews_url, wait_until='domcontentloaded', timeout=30000)

        # Ждём появления карточки организации
        try:
            await page.wait_for_selector('[class*="card-title"]', timeout=15000)
        except PlaywrightTimeout:
            page_title = await page.title()
            raise ValueError(
                f"Карточка отзывов не загрузилась за 15с. Заголовок страницы: «{page_title}». "
                "Вероятно, капча/антибот или сменилась разметка Яндекса."
            )

        # Читаем название и статистику
        org_name = await _get_text(page, '[class*="card-title__header"]')
        avg_rating = await _get_rating(page)
        ratings_count, reviews_count = await _get_counts(page)

        # Прокручиваем список отзывов до конца (загружаем все ~600)
        reviews = await _scroll_and_collect_reviews(page)

        await browser.close()

        return ParseResult(
            organization_name=org_name,
            average_rating=avg_rating,
            ratings_count=ratings_count,
            reviews_count=reviews_count,
            reviews=reviews,
        )


async def _get_text(page, selector: str, default: str = '') -> str:
    """Безопасно читает текст элемента."""
    try:
        el = await page.query_selector(selector)
        return (await el.inner_text()).strip() if el else default
    except Exception:
        return default


async def _get_rating(page) -> float:
    """Читает средний рейтинг организации."""
    text = await _get_text(page, '[class*="rating__value"]')
    try:
        return float(text.replace(',', '.'))
    except (ValueError, AttributeError):
        return 0.0


async def _get_counts(page) -> tuple[int, int]:
    """
    Читает количество оценок и отзывов.
    На странице они выглядят так: '1 234 оценки · 567 отзывов'
    """
    text = await _get_text(page, '[class*="rating__count"]', '0 оценок · 0 отзывов')

    ratings = 0
    reviews = 0

    # Ищем числа перед словами "оценк" и "отзыв"
    ratings_match = re.search(r'([\d\s]+)\s+оценк', text)
    reviews_match = re.search(r'([\d\s]+)\s+отзыв', text)

    if ratings_match:
        ratings = int(ratings_match.group(1).replace(' ', '').replace('\xa0', ''))
    if reviews_match:
        reviews = int(reviews_match.group(1).replace(' ', '').replace('\xa0', ''))

    return ratings, reviews


async def _scroll_and_collect_reviews(page) -> list[Review]:
    """
    Прокручивает список отзывов и собирает все данные.

    Яндекс подгружает отзывы порциями (~20 штук) при скролле.
    Мы прокручиваем контейнер вниз, ждём новых отзывов, повторяем.
    Останавливаемся когда новых отзывов больше не появляется.
    """
    reviews = []
    seen_authors = set()  # для дедупликации
    no_new_count = 0      # счётчик попыток без новых отзывов

    # Контейнер со списком отзывов
    reviews_container = '[class*="business-reviews-card-view"]'

    for _ in range(40):  # максимум 40 прокруток = ~600-800 отзывов
        # Собираем текущие отзывы на странице
        review_elements = await page.query_selector_all('[class*="review"]')

        new_found = False
        for el in review_elements:
            author = await _get_text(el, '[class*="user-icon__name"]')
            if not author or author in seen_authors:
                continue

            date = await _get_text(el, '[class*="review-header__date"]')
            text = await _get_text(el, '[class*="review-text"]')
            rating_el = await el.query_selector('[class*="stars__star_full"]')
            rating = await _count_stars(el)

            reviews.append(Review(
                author=author,
                date=date,
                text=text,
                rating=rating,
            ))
            seen_authors.add(author)
            new_found = True

        if not new_found:
            no_new_count += 1
            if no_new_count >= 3:
                break  # три попытки без новых — значит все загружены
        else:
            no_new_count = 0

        # Скроллим контейнер вниз
        await page.evaluate(
            f"""
            const el = document.querySelector('{reviews_container}');
            if (el) el.scrollTop += 3000;
            """
        )
        await asyncio.sleep(1.5)  # ждём подгрузки

    return reviews


async def _count_stars(review_el) -> int:
    """Считает количество закрашенных звёзд в отзыве."""
    stars = await review_el.query_selector_all('[class*="stars__star_full"]')
    return len(stars)


@app.get("/health")
async def health():
    """Laravel проверяет этим эндпоинтом что парсер живой."""
    return {"status": "ok"}
