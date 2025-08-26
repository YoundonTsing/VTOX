import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import './styles/main.css'

// 应用启动时清空聊天记录缓存
const CHAT_CACHE_KEY = 'mcsa_agent_chat_history'
try {
  sessionStorage.removeItem(CHAT_CACHE_KEY)
  console.log('[App] 应用启动，已清空聊天记录缓存')
} catch (error) {
  console.warn('[App] 清空聊天记录缓存失败:', error)
}

const app = createApp(App)
app.use(ElementPlus)
app.use(router)
app.mount('#app') 