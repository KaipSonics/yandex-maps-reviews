<?php

namespace App\Http\Controllers;

use App\Http\Requests\StoreOrganizationRequest;
use App\Models\Organization;
use App\Services\YandexParserService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use RuntimeException;

/**
 * Управление организацией пользователя и выдача её отзывов.
 *
 * Обратите внимание: контроллер НЕ содержит логики парсинга — он только
 * принимает запрос, зовёт сервис и формирует ответ. Вся работа с Яндексом —
 * в YandexParserService (требование ТЗ).
 */
class OrganizationController extends Controller
{
    public function __construct(
        private YandexParserService $parser, // Laravel сам подставит сервис (DI)
    ) {}

    /**
     * Сохранить ссылку и сразу спарсить организацию.
     * POST /api/organization
     */
    public function store(StoreOrganizationRequest $request): JsonResponse
    {
        $user = $request->user();

        // Извлекаем yandex_id из ссылки (число после /org/название/)
        preg_match('#/org/[^/]+/(\d+)#', $request->url, $m);
        $yandexId = $m[1] ?? null;

        // Один пользователь — одна организация: обновляем существующую или создаём
        $organization = Organization::updateOrCreate(
            ['user_id' => $user->id],
            [
                'url' => $request->url,
                'yandex_id' => $yandexId,
                'parse_status' => 'pending',
            ],
        );

        // Запускаем парсинг. Ошибки парсера превращаем в понятный JSON-ответ.
        try {
            $organization = $this->parser->parseAndStore($organization);
        } catch (RuntimeException $e) {
            return response()->json([
                'message' => 'Не удалось получить данные организации.',
                'error' => $e->getMessage(),
                'organization' => $this->formatOrganization($organization),
            ], 502); // 502 Bad Gateway — внешний источник подвёл
        }

        return response()->json([
            'message' => 'Данные успешно получены.',
            'organization' => $this->formatOrganization($organization),
        ]);
    }

    /**
     * Текущая организация пользователя (статистика, без отзывов).
     * GET /api/organization
     */
    public function show(Request $request): JsonResponse
    {
        $organization = Organization::where('user_id', $request->user()->id)->first();

        if (! $organization) {
            return response()->json(['organization' => null]);
        }

        return response()->json([
            'organization' => $this->formatOrganization($organization),
        ]);
    }

    /**
     * Отзывы организации с пагинацией по 50 на страницу.
     * GET /api/organization/reviews?page=2
     *
     * Решение по архитектуре (из ТЗ): мы НЕ дёргаем Яндекс при каждом запросе.
     * Все ~600 отзывов один раз спарсены и лежат в БД. Здесь отдаём из БД с
     * пагинацией — мгновенно и без нагрузки на Яндекс.
     */
    public function reviews(Request $request): JsonResponse
    {
        $organization = Organization::where('user_id', $request->user()->id)->firstOrFail();

        $reviews = $organization->reviews()
            ->orderByDesc('id')
            ->paginate(50); // Laravel сам считает страницы и total

        return response()->json($reviews);
    }

    /**
     * Приводим организацию к единому виду для фронта.
     */
    private function formatOrganization(Organization $organization): array
    {
        return [
            'id' => $organization->id,
            'url' => $organization->url,
            'name' => $organization->name,
            'average_rating' => $organization->average_rating,
            'ratings_count' => $organization->ratings_count,
            'reviews_count' => $organization->reviews_count,
            'parse_status' => $organization->parse_status,
            'parse_error' => $organization->parse_error,
            'parsed_at' => $organization->parsed_at,
        ];
    }
}
