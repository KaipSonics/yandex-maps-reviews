<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;

/**
 * Валидация ссылки на карточку Яндекс.Карт.
 *
 * Выносим правила сюда, чтобы контроллер оставался чистым. Laravel сам
 * проверит данные ДО входа в метод контроллера и вернёт 422 с ошибками,
 * если ссылка невалидна.
 */
class StoreOrganizationRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true; // доступ уже проверен middleware auth:sanctum
    }

    public function rules(): array
    {
        return [
            'url' => [
                'required',
                'url',
                // Ссылка должна быть именно на организацию Яндекс.Карт вида /org/.../12345
                'regex:#^https?://yandex\.[a-z]+/maps/org/[^/]+/\d+#',
            ],
        ];
    }

    public function messages(): array
    {
        return [
            'url.required' => 'Вставьте ссылку на организацию.',
            'url.url' => 'Это не похоже на ссылку.',
            'url.regex' => 'Ссылка должна быть на карточку организации в Яндекс.Картах (например, https://yandex.ru/maps/org/.../123456).',
        ];
    }
}
