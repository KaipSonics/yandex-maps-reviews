<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Таблица organizations — хранит карточки организаций, которые добавил пользователь.
 *
 * Здесь же кэшируем результат парсинга (рейтинг, счётчики), чтобы не дёргать
 * Яндекс при каждом открытии страницы. Сами отзывы — в отдельной таблице reviews.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('organizations', function (Blueprint $table) {
            $table->id();

            // К какому пользователю относится организация
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();

            // Исходная ссылка, которую вставил пользователь
            $table->string('url');

            // ID организации, извлечённый из ссылки (для дедупликации/обновлений)
            $table->string('yandex_id')->nullable();

            // Название организации (получаем при парсинге)
            $table->string('name')->nullable();

            // Кэш статистики — заполняется после парсинга
            $table->decimal('average_rating', 3, 1)->nullable(); // напр. 4.5
            $table->unsignedInteger('ratings_count')->default(0); // число оценок
            $table->unsignedInteger('reviews_count')->default(0); // число отзывов

            // Статус последнего парсинга: pending | success | error
            $table->string('parse_status')->default('pending');
            $table->text('parse_error')->nullable();      // текст ошибки, если была
            $table->timestamp('parsed_at')->nullable();   // когда последний раз парсили

            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('organizations');
    }
};
