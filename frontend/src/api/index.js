import axios from 'axios'

/*
 * Настройка axios — HTTP клиент для запросов к Laravel API.
 *
 * Авторизация — токен-режим Sanctum: после логина бэкенд отдаёт токен,
 * мы храним его в localStorage и подставляем в заголовок Authorization
 * к каждому запросу. Это проще cookie/CSRF-режима и удобно для SPA на
 * отдельном порту.
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Accept': 'application/json',
  },
})

// Перехватчик запросов — подставляем токен, если он есть
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Перехватчик ответов — если 401 (токен протух), чистим и уводим на логин
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  login: (email, password) => api.post('/login', { email, password }),
  logout: () => api.post('/logout'),
  me: () => api.get('/me'),
}

export const organizationApi = {
  // Сохранить ссылку и спарсить
  save: (url) => api.post('/organization', { url }),
  // Текущая организация пользователя (статистика)
  current: () => api.get('/organization'),
  // Отзывы с пагинацией (orgId не нужен — берём организацию пользователя на бэке)
  reviews: (orgId, page = 1) => api.get('/organization/reviews', { params: { page } }),
}

export default api
