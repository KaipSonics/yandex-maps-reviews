<template>
  <div class="container">
    <header class="page-header">
      <h1>Отзывы с Яндекс.Карт</h1>
      <button class="btn btn-secondary" @click="handleLogout">Выйти</button>
    </header>

    <!-- Блок ввода ссылки -->
    <div class="card">
      <h2>Настройки</h2>
      <p style="color:#666; font-size:14px">
        Вставьте ссылку на карточку организации в Яндекс.Картах
      </p>

      <form @submit.prevent="handleSave" style="display:flex; gap:8px">
        <input
          v-model="url"
          type="text"
          placeholder="https://yandex.ru/maps/org/название/123456789/"
          style="flex:1"
        />
        <button type="submit" class="btn btn-primary" :disabled="saving">
          {{ saving ? 'Загрузка...' : 'Загрузить' }}
        </button>
      </form>

      <p v-if="saveError" class="error-msg">{{ saveError }}</p>
      <p v-if="saving" class="loading">⏳ Парсинг отзывов — это может занять 1-2 минуты...</p>
    </div>

    <!-- Блок статистики -->
    <div v-if="org" class="card">
      <h2>{{ org.name }}</h2>
      <div class="stats">
        <div class="stat">
          <span class="stat-val">{{ org.average_rating?.toFixed(1) }}</span>
          <span class="stat-label">Средний рейтинг</span>
        </div>
        <div class="stat">
          <span class="stat-val">{{ org.ratings_count?.toLocaleString('ru') }}</span>
          <span class="stat-label">Оценок</span>
        </div>
        <div class="stat">
          <span class="stat-val">{{ org.reviews_count?.toLocaleString('ru') }}</span>
          <span class="stat-label">Отзывов</span>
        </div>
      </div>
    </div>

    <!-- Список отзывов -->
    <div v-if="org">
      <div v-if="reviewsLoading" class="loading">Загрузка отзывов...</div>

      <div v-else-if="reviewsError" class="error-msg" style="padding:16px">
        {{ reviewsError }}
      </div>

      <template v-else>
        <ReviewCard
          v-for="review in reviews"
          :key="review.id"
          :review="review"
        />

        <!-- Пагинация -->
        <div v-if="totalPages > 1" class="pagination">
          <button
            class="btn btn-secondary"
            :disabled="currentPage === 1"
            @click="loadReviews(currentPage - 1)"
          >← Назад</button>

          <span>{{ currentPage }} / {{ totalPages }}</span>

          <button
            class="btn btn-secondary"
            :disabled="currentPage === totalPages"
            @click="loadReviews(currentPage + 1)"
          >Вперёд →</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { organizationApi } from '../api'
import ReviewCard from '../components/ReviewCard.vue'

const router = useRouter()
const auth = useAuthStore()

const url = ref('')
const org = ref(null)
const saving = ref(false)
const saveError = ref('')

const reviews = ref([])
const reviewsLoading = ref(false)
const reviewsError = ref('')
const currentPage = ref(1)
const totalPages = ref(1)

// При загрузке страницы — проверяем есть ли уже сохранённая организация
onMounted(async () => {
  try {
    const { data } = await organizationApi.current()
    if (data.organization) {
      org.value = data.organization
      url.value = data.organization.url
      await loadReviews(1)
    }
  } catch {
    // нет сохранённой организации — ок
  }
})

async function handleSave() {
  saveError.value = ''
  saving.value = true
  try {
    const { data } = await organizationApi.save(url.value)
    org.value = data.organization
    await loadReviews(1)
  } catch (e) {
    saveError.value = e.response?.data?.message ?? 'Ошибка при загрузке данных'
  } finally {
    saving.value = false
  }
}

async function loadReviews(page) {
  reviewsLoading.value = true
  reviewsError.value = ''
  try {
    const { data } = await organizationApi.reviews(org.value.id, page)
    reviews.value = data.data          // Laravel paginate() возвращает объект с полем data
    currentPage.value = data.current_page
    totalPages.value = data.last_page
  } catch {
    reviewsError.value = 'Не удалось загрузить отзывы'
  } finally {
    reviewsLoading.value = false
  }
}

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
h1 { margin: 0; font-size: 22px; }
h2 { margin: 0 0 16px; font-size: 18px; }

.stats {
  display: flex;
  gap: 32px;
}
.stat { display: flex; flex-direction: column; }
.stat-val { font-size: 28px; font-weight: 700; color: #fc3f1d; }
.stat-label { font-size: 12px; color: #888; }

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 24px 0;
  font-size: 14px;
}
</style>
