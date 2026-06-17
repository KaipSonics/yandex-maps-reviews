<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/**
 * Модель отзыва. Одна строка = один отзыв об организации.
 */
class Review extends Model
{
    protected $fillable = [
        'organization_id',
        'author',
        'review_date',
        'text',
        'rating',
    ];

    protected $casts = [
        'rating' => 'integer',
    ];

    // Связь: отзыв принадлежит организации
    public function organization(): BelongsTo
    {
        return $this->belongsTo(Organization::class);
    }
}
