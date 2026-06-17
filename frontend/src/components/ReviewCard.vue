<template>
  <div class="card review">
    <div class="review-header">
      <strong>{{ review.author }}</strong>
      <span class="stars">{{ '★'.repeat(review.rating) }}{{ '☆'.repeat(5 - review.rating) }}</span>
      <span class="date">{{ review.review_date }}</span>
    </div>
    <p v-if="review.text" class="review-text">{{ review.text }}</p>
    <p v-else class="no-text">Без текста</p>
  </div>
</template>

<script setup>
/*
 * defineProps — объявляем что этот компонент принимает снаружи.
 * Компонент не знает откуда берётся review — это делает его переиспользуемым.
 */
defineProps({
  review: {
    type: Object,
    required: true,
  },
})
</script>

<style scoped>
.review { padding: 16px 24px; }
.review-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.date { color: #aaa; font-size: 13px; margin-left: auto; }
.review-text { margin: 0; font-size: 14px; line-height: 1.6; }
.no-text { margin: 0; color: #bbb; font-size: 13px; font-style: italic; }
</style>
