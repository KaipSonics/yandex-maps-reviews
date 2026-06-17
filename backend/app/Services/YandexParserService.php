<?php

namespace App\Services;

use App\Models\Organization;
use App\Models\Review;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use RuntimeException;

/**
 * Сервис-обёртка над парсером Яндекс.Карт.
 *
 * Зачем отдельный класс (требование ТЗ):
 *   Контроллер не должен знать КАК мы добываем данные. Он просто говорит
 *   "спарси эту организацию". Если завтра поменяем парсер (другой движок,
 *   официальный API) — правим только этот класс, контроллеры не трогаем.
 *
 * Архитектура:
 *   Laravel (этот сервис)  ->  HTTP  ->  Python+Playwright (отдельный контейнер)
 *   Python ходит на Яндекс, скроллит, отдаёт JSON. Laravel сохраняет в БД.
 */
class YandexParserService
{
    /**
     * Спарсить организацию и сохранить результат в БД.
     *
     * @throws RuntimeException если парсер недоступен или вернул ошибку
     */
    public function parseAndStore(Organization $organization): Organization
    {
        $parserUrl = config('services.parser.url'); // напр. http://parser:8001

        try {
            // Запрос к Python-парсеру. Таймаут большой — прокрутка ~600 отзывов небыстрая.
            $response = Http::timeout(300)->post("{$parserUrl}/parse", [
                'url' => $organization->url,
            ]);
        } catch (\Throwable $e) {
            // Парсер не отвечает (контейнер упал, сеть) — фиксируем ошибку
            $this->markFailed($organization, 'Парсер недоступен: ' . $e->getMessage());
            throw new RuntimeException('Сервис парсинга недоступен', previous: $e);
        }

        // Парсер вернул ошибку (неверный URL, изменилась разметка, пустой ответ)
        if ($response->failed()) {
            $message = $response->json('detail') ?? 'Неизвестная ошибка парсера';
            $this->markFailed($organization, $message);
            throw new RuntimeException($message);
        }

        $data = $response->json();

        // Защита от "пустого ответа" — крайний случай из ТЗ
        if (empty($data) || !isset($data['reviews'])) {
            $this->markFailed($organization, 'Парсер вернул пустой ответ');
            throw new RuntimeException('Парсер вернул пустой ответ');
        }

        // Сохраняем всё одной транзакцией: либо всё, либо ничего
        return DB::transaction(function () use ($organization, $data) {
            // Обновляем статистику организации
            $organization->update([
                'name' => $data['organization_name'] ?? $organization->name,
                'average_rating' => $data['average_rating'] ?? 0,
                'ratings_count' => $data['ratings_count'] ?? 0,
                'reviews_count' => $data['reviews_count'] ?? 0,
                'parse_status' => 'success',
                'parse_error' => null,
                'parsed_at' => now(),
            ]);

            // Перезаписываем отзывы: удаляем старые, вставляем свежие
            $organization->reviews()->delete();

            $rows = collect($data['reviews'])->map(fn ($r) => [
                'organization_id' => $organization->id,
                'author' => $r['author'] ?? null,
                'review_date' => $r['date'] ?? null,
                'text' => $r['text'] ?? null,
                'rating' => $r['rating'] ?? 0,
                'created_at' => now(),
                'updated_at' => now(),
            ])->all();

            // Вставляем пачками по 500 — быстрее чем по одному
            foreach (array_chunk($rows, 500) as $chunk) {
                Review::insert($chunk);
            }

            Log::info("Спарсено {$organization->reviews_count} отзывов для org #{$organization->id}");

            return $organization->fresh();
        });
    }

    /**
     * Пометить организацию как неуспешно спарсенную (для показа ошибки в UI).
     */
    private function markFailed(Organization $organization, string $message): void
    {
        $organization->update([
            'parse_status' => 'error',
            'parse_error' => $message,
            'parsed_at' => now(),
        ]);
        Log::warning("Ошибка парсинга org #{$organization->id}: {$message}");
    }
}
