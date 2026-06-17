<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\ValidationException;

/**
 * Авторизация через Laravel Sanctum (токен-режим).
 *
 * Почему токен, а не cookie-сессии: фронтенд — отдельное SPA на другом порту.
 * Токен в заголовке Authorization: Bearer ... проще и нагляднее для тестового,
 * без возни с CSRF-cookie и общим доменом. Токен фронт хранит в localStorage.
 */
class AuthController extends Controller
{
    /**
     * Вход: проверяем email+пароль, выдаём токен.
     */
    public function login(Request $request): JsonResponse
    {
        $credentials = $request->validate([
            'email' => ['required', 'email'],
            'password' => ['required'],
        ]);

        $user = User::where('email', $credentials['email'])->first();

        // Проверяем что пользователь есть и пароль совпадает (Hash::check сравнивает с хэшем)
        if (! $user || ! Hash::check($credentials['password'], $user->password)) {
            // Единое сообщение — не подсказываем, что именно неверно (логин или пароль)
            throw ValidationException::withMessages([
                'email' => ['Неверный email или пароль.'],
            ]);
        }

        // Создаём персональный токен доступа
        $token = $user->createToken('spa-token')->plainTextToken;

        return response()->json([
            'user' => $user->only('id', 'name', 'email'),
            'token' => $token,
        ]);
    }

    /**
     * Выход: удаляем текущий токен.
     */
    public function logout(Request $request): JsonResponse
    {
        $request->user()->currentAccessToken()->delete();

        return response()->json(['message' => 'Вы вышли из системы.']);
    }

    /**
     * Данные текущего пользователя (для проверки авторизации на фронте).
     */
    public function me(Request $request): JsonResponse
    {
        return response()->json($request->user()->only('id', 'name', 'email'));
    }
}
