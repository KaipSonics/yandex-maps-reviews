<?php

use Illuminate\Support\Facades\Route;

/*
 | На проде Laravel отдаёт собранный Vue-SPA. Любой не-API маршрут возвращает
 | index.html, а дальше vue-router сам показывает нужный экран. Так фронт и бэк
 | живут на одном домене — не нужен CORS, токен-авторизация работает same-origin.
 */
Route::get('/{any}', function () {
    $index = public_path('index.html');

    // Если фронт ещё не собран (чистый локальный бэкенд) — отдаём заглушку Laravel
    return file_exists($index)
        ? response()->file($index)
        : view('welcome');
})->where('any', '^(?!api).*$');
