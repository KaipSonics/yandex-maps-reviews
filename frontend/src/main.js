import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

/*
 * Точка входа Vue приложения.
 * createApp — создаёт экземпляр приложения
 * Pinia — хранилище состояния (как Redux, но проще)
 * Router — управление URL (какой компонент показывать для какого пути)
 */
const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
