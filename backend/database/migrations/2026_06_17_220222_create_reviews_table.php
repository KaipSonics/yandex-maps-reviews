<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Таблица reviews — отдельные отзывы, привязанные к организации.
 *
 * Храним результат парсинга в БД, а не тянем ~600 отзывов с Яндекса при каждом
 * открытии страницы. Это и есть "кэширование на стороне бэка" из ТЗ: спарсили
 * один раз — отдаём из БД с пагинацией мгновенно.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('reviews', function (Blueprint $table) {
            $table->id();

            // К какой организации относится отзыв
            $table->foreignId('organization_id')->constrained()->cascadeOnDelete();

            $table->string('author')->nullable();   // автор отзыва
            $table->string('review_date')->nullable(); // дата (как её отдаёт Яндекс)
            $table->text('text')->nullable();        // текст отзыва
            $table->unsignedTinyInteger('rating')->default(0); // оценка 1–5

            $table->timestamps();

            // Индекс для быстрой пагинации по организации
            $table->index('organization_id');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('reviews');
    }
};
