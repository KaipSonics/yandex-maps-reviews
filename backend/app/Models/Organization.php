<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

/**
 * Модель организации. Одна строка = одна карточка Яндекс.Карт у пользователя.
 */
class Organization extends Model
{
    // Поля, которые разрешено массово заполнять (защита от подмены чужих полей)
    protected $fillable = [
        'user_id',
        'url',
        'yandex_id',
        'name',
        'average_rating',
        'ratings_count',
        'reviews_count',
        'parse_status',
        'parse_error',
        'parsed_at',
    ];

    protected $casts = [
        'average_rating' => 'float',
        'parsed_at' => 'datetime',
    ];

    // Связь: организация принадлежит пользователю
    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    // Связь: у организации много отзывов
    public function reviews(): HasMany
    {
        return $this->hasMany(Review::class);
    }
}
