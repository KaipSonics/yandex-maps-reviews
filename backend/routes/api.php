<?php

use App\Http\Controllers\AuthController;
use App\Http\Controllers\OrganizationController;
use Illuminate\Support\Facades\Route;

/*
 | Маршруты API. Префикс /api добавляется автоматически.
 | Публичный — только логин. Всё остальное защищено auth:sanctum
 | (требует валидный токен в заголовке Authorization: Bearer ...).
 */

// --- Публичные маршруты ---
Route::post('/login', [AuthController::class, 'login']);

// --- Защищённые маршруты (нужен токен) ---
Route::middleware('auth:sanctum')->group(function () {
    Route::post('/logout', [AuthController::class, 'logout']);
    Route::get('/me', [AuthController::class, 'me']);

    // Организация пользователя
    Route::get('/organization', [OrganizationController::class, 'show']);
    Route::post('/organization', [OrganizationController::class, 'store']);
    Route::get('/organization/reviews', [OrganizationController::class, 'reviews']);
});
