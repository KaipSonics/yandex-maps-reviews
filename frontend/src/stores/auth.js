import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '../api'

/*
 * Pinia store — централизованное хранилище состояния.
 * Вместо того чтобы каждый компонент сам хранил "кто залогинен",
 * это хранится в одном месте и доступно из любого компонента.
 *
 * Авторизация токен-режим: токен храним в localStorage, чтобы вход
 * переживал перезагрузку страницы. api-клиент сам подставляет его в заголовки.
 */
export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)

  async function login(email, password) {
    const { data } = await authApi.login(email, password)
    localStorage.setItem('token', data.token) // сохраняем токен
    user.value = data.user
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      // Чистим локальное состояние в любом случае
      localStorage.removeItem('token')
      user.value = null
    }
  }

  async function fetchMe() {
    // Нет токена — даже не дёргаем сервер
    if (!localStorage.getItem('token')) {
      user.value = null
      return
    }
    loading.value = true
    try {
      const { data } = await authApi.me()
      user.value = data
    } catch {
      user.value = null
    } finally {
      loading.value = false
    }
  }

  const isLoggedIn = () => !!user.value

  return { user, loading, login, logout, fetchMe, isLoggedIn }
})
