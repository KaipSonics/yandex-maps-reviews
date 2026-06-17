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
from urllib.parse import unquote
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
    Достаёт ID организации из URL Яндекс.Карт. Поддерживает разные форматы ссылок:
      • карточка:        /maps/org/название/12345678
      • поисковая выдача: ...poi[uri]=ymapsbm1://org?oid=12345678  (ссылка «Поделиться»)
      • просто параметр:  ...&oid=12345678
    Возвращает None, если ID не найден (напр. ещё не отработал редирект короткой ссылки).
    """
    # url может быть URL-кодированным (oid%3D...), раскодируем для поиска oid
    decoded = unquote(url)
    patterns = [
        r'/org/[^/]+/(\d+)',     # /maps/org/name/12345
        r'/org/(\d+)',           # /maps/org/12345 (без slug)
        r'[?&]oid=(\d+)',        # &oid=12345
        r'org\?oid=(\d+)',       # ymapsbm1://org?oid=12345
    ]
    for pat in patterns:
        m = re.search(pat, decoded)
        if m:
            return m.group(1)
    return None


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

        # Шаг 2. Достаём ID организации — из итогового адреса ИЛИ из исходной ссылки
        # (ID может быть в параметре oid у ссылок «Поделиться» из поиска).
        org_id = extract_org_id(final_url) or extract_org_id(url)
        if not org_id:
            page_title = await page.title()
            raise ValueError(
                f"Не удалось определить организацию по ссылке. Итоговый адрес: {final_url}. "
                f"Заголовок страницы: «{page_title}». Возможно, капча или неверная ссылка."
            )

        # Строим канонический адрес карточки по ID и идём на вкладку отзывов.
        # Яндекс сам подставит slug — /maps/org/<id>/reviews/ работает без названия.
        reviews_url = f'https://yandex.ru/maps/org/{org_id}/reviews/'
        await page.goto(reviews_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(2)

        # Ждём появления хотя бы одного блока отзыва. Пробуем несколько селекторов:
        # классы Яндекса меняются, поэтому берём широкие подстроки, а не точные имена.
        review_selectors = [
            '[itemprop="review"]',                  # микроразметка schema.org (самое стабильное)
            '[class*="business-review-view"]',      # BEM-блок отзыва
            '[class*="review-view"]',
        ]
        review_selector = None
        for sel in review_selectors:
            try:
                await page.wait_for_selector(sel, timeout=8000)
                review_selector = sel
                break
            except PlaywrightTimeout:
                continue

        if review_selector is None:
            # Диагностика: считаем, сколько элементов даёт каждый селектор-кандидат,
            # чтобы понять реальную разметку Яндекса (парсим вслепую).
            probes = [
                '[itemprop="review"]', '[itemscope]', '[class*="review"]',
                '[class*="business-review"]', '[class*="review-view"]', 'article',
            ]
            counts = {}
            for sel in probes:
                try:
                    counts[sel] = len(await page.query_selector_all(sel))
                except Exception:
                    counts[sel] = -1
            page_title = await page.title()
            diag = ', '.join(f'{s}={c}' for s, c in counts.items())
            raise ValueError(
                f"Не нашёл блоки отзывов. Заголовок: «{page_title}». Диагностика селекторов: {diag}"
            )

        # Название организации — из заголовка вкладки (самый надёжный источник)
        org_name = await _get_org_name(page)

        # Рейтинг и счётчики берём регулярками из текста страницы — устойчиво к смене классов
        page_text = await page.inner_text('body')
        avg_rating = _parse_rating(page_text)
        ratings_count, reviews_count = _parse_counts(page_text)

        # Прокручиваем список отзывов до конца (загружаем все ~600)
        reviews = await _scroll_and_collect_reviews(page, review_selector)

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


async def _get_org_name(page) -> str:
    """Название организации. Пробуем h1/заголовок, затем title вкладки."""
    for sel in ['h1[class*="title"]', '[class*="card-title-view__title"]', 'h1']:
        name = await _get_text(page, sel)
        if name:
            return name
    # Фолбэк: из title вида «Отзывы о „Привет", Санкт-Петербург… — Яндекс Карты»
    title = await page.title()
    m = re.search(r'Отзывы о\s+[«"]?(.+?)[»"]?,', title)
    return m.group(1) if m else title


def _parse_rating(text: str) -> float:
    """
    Средний рейтинг из текста страницы. Ищем число рядом со словом «оцен»,
    напр. «4,5 · 1 234 оценки». Это устойчивее, чем привязка к CSS-классу.
    """
    m = re.search(r'([1-5][.,]\d)\s*(?:·|\n|\s)*\s*[\d\s ]+\s*оцен', text)
    if not m:
        m = re.search(r'\b([1-5][.,]\d)\b', text)  # запасной вариант — первое «X,Y»
    return float(m.group(1).replace(',', '.')) if m else 0.0


def _parse_counts(text: str) -> tuple[int, int]:
    """Количество оценок и отзывов из текста: «… 1 234 оценки · 567 отзывов»."""
    def num(pattern: str) -> int:
        m = re.search(pattern, text)
        return int(re.sub(r'[\s ]', '', m.group(1))) if m else 0

    ratings = num(r'([\d\s ]+)\s*оцен')
    reviews = num(r'([\d\s ]+)\s*отзыв')
    return ratings, reviews


async def _scroll_and_collect_reviews(page, review_selector: str) -> list[Review]:
    """
    Прокручивает список отзывов и собирает все данные.

    Яндекс подгружает отзывы порциями (~20 штук) при скролле.
    Мы прокручиваем контейнер вниз, ждём новых отзывов, повторяем.
    Останавливаемся, когда новых отзывов больше не появляется (3 пустые попытки).
    """
    reviews: list[Review] = []
    seen = set()       # дедупликация по (автор, начало текста)
    no_new_count = 0

    for _ in range(50):  # максимум 50 прокруток (~600-1000 отзывов)
        review_elements = await page.query_selector_all(review_selector)

        new_found = False
        for el in review_elements:
            data = await _extract_review(el)
            if not data:
                continue
            key = (data['author'], (data['text'] or '')[:40])
            if key in seen:
                continue
            seen.add(key)
            reviews.append(Review(**data))
            new_found = True

        no_new_count = 0 if new_found else no_new_count + 1
        if no_new_count >= 3:
            break

        # Прокручиваем последний отзыв в зону видимости ЧЕРЕЗ JS: элемент ищется
        # заново в контексте страницы, поэтому нет «оторванных от DOM» ссылок,
        # которые ломаются при перерисовке списка Яндексом.
        try:
            await page.evaluate(
                """(sel) => {
                    const els = document.querySelectorAll(sel);
                    if (els.length) els[els.length - 1].scrollIntoView({block: 'end'});
                }""",
                review_selector,
            )
        except Exception:
            pass  # прокрутка не критична — на следующей итерации попробуем снова
        await asyncio.sleep(1.2)

    return reviews


async def _extract_review(el) -> dict | None:
    """Извлекает поля одного отзыва с фолбэками (микроразметка → BEM-классы)."""
    # Автор
    author = (await _get_text(el, '[itemprop="name"]')
              or await _get_text(el, '[class*="author-name"]')
              or await _get_text(el, '[class*="_author"]'))

    # Текст отзыва
    text = (await _get_text(el, '[itemprop="reviewBody"]')
            or await _get_text(el, '[class*="__body"]')
            or await _get_text(el, '[class*="review-text"]'))

    # Дата: сначала микроразметка (атрибут content), потом видимый текст
    date = await _get_attr(el, 'meta[itemprop="datePublished"]', 'content')
    if not date:
        date = (await _get_text(el, '[class*="__date"]')
                or await _get_text(el, '[class*="date"]'))

    # Оценка: микроразметка ratingValue, иначе считаем закрашенные звёзды
    rating = 0
    rating_meta = await _get_attr(el, 'meta[itemprop="ratingValue"]', 'content')
    if rating_meta:
        try:
            rating = int(float(rating_meta))
        except ValueError:
            rating = 0
    if not rating:
        try:
            full_stars = await el.query_selector_all('[class*="_full"]')
            rating = len(full_stars)
        except Exception:
            rating = 0

    if not author and not text:
        return None  # пустой/служебный блок — пропускаем

    return {'author': author or 'Аноним', 'date': date or '', 'text': text or '', 'rating': rating}


async def _get_attr(el, selector: str, attr: str) -> str:
    """Безопасно читает атрибут вложенного элемента."""
    try:
        node = await el.query_selector(selector)
        return (await node.get_attribute(attr)) or '' if node else ''
    except Exception:
        return ''


@app.get("/health")
async def health():
    """Laravel проверяет этим эндпоинтом что парсер живой."""
    return {"status": "ok"}
