<template>
  <div class="login-wrap">
    <div class="card login-card">
      <h1>Войти</h1>

      <form @submit.prevent="handleLogin">
        <div class="field">
          <label>Email</label>
          <input v-model="email" type="email" placeholder="test@example.com" required />
        </div>

        <div class="field">
          <label>Пароль</label>
          <input v-model="password" type="password" placeholder="••••••••" required />
        </div>

        <!-- Показываем ошибку если она есть -->
        <p v-if="error" class="error-msg">{{ error }}</p>

        <button type="submit" class="btn btn-primary" :disabled="loading" style="width:100%">
          {{ loading ? 'Вход...' : 'Войти' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
/*
 * Composition API — современный способ писать логику компонента в Vue 3.
 * ref() создаёт реактивную переменную — когда она меняется, Vue перерисовывает шаблон.
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    router.push('/')
  } catch (e) {
    // Laravel возвращает ошибки валидации в errors или общее сообщение в message
    error.value = e.response?.data?.errors?.email?.[0]
      ?? e.response?.data?.message
      ?? 'Ошибка входа'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.login-card { width: 100%; max-width: 400px; }
h1 { margin: 0 0 24px; font-size: 24px; }
.field { margin-bottom: 16px; }
label { display: block; font-size: 13px; color: #666; margin-bottom: 6px; }
</style>
