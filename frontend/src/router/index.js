import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    name: 'Settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { public: false },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/*
 * Navigation guard — проверяет перед каждым переходом:
 * - если маршрут закрытый и пользователь не авторизован → на /login
 * - если пользователь уже залогинен и пытается зайти на /login → на главную
 */
router.beforeEach(async (to) => {
  const auth = useAuthStore()

  if (!auth.user) {
    await auth.fetchMe()
  }

  if (!to.meta.public && !auth.isLoggedIn()) {
    return { name: 'Login' }
  }

  if (to.name === 'Login' && auth.isLoggedIn()) {
    return { name: 'Settings' }
  }
})

export default router
