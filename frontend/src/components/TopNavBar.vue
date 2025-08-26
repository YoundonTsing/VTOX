<template>
  <div class="top-nav">
    <div class="logo">
      <svg class="motor-icon" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
        <!-- 最外层圆圈 -->
        <circle cx="256" cy="256" r="260" fill="none" stroke="#ffffff" stroke-width="20" />
        <!-- 外部圆圈 -->
        <circle cx="256" cy="256" r="200" fill="none" stroke="#ffffff" stroke-width="20" />
        <!-- 轴承外环 -->
        <circle cx="256" cy="256" r="150" fill="none" stroke="#ffffff" stroke-width="30" />
        <!-- 轴承内环 -->
        <circle cx="256" cy="256" r="80" fill="none" stroke="#ffffff" stroke-width="25" />
        <!-- 轴承中心 -->
        <circle cx="256" cy="256" r="30" fill="#ffffff" />
        <!-- 滚动体 (滚珠) -->
        <circle cx="256" cy="106" r="40" fill="#ffffff" />
        <circle cx="365" cy="146" r="40" fill="#ffffff" />
        <circle cx="405" cy="256" r="40" fill="#ffffff" />
        <circle cx="365" cy="365" r="40" fill="#ffffff" />
        <circle cx="256" cy="405" r="40" fill="#ffffff" />
        <circle cx="146" cy="365" r="40" fill="#ffffff" />
        <circle cx="106" cy="256" r="40" fill="#ffffff" />
        <circle cx="146" cy="146" r="40" fill="#ffffff" />
      </svg>
      <h1>MCSA-AI电机诊断系统</h1>
    </div>
    <div class="right-section">
      <el-button v-if="!isLoggedIn" type="primary" size="small" @click="router.push('/login')">登录</el-button>
      <el-dropdown v-else>
        <span class="el-dropdown-link user-info">
          <el-icon><user-filled /></el-icon>
          用户: {{ username || '未登录' }}
          <el-icon class="el-icon--right"><arrow-down /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <el-dropdown class="settings-dropdown">
        <span class="el-dropdown-link">
          <el-icon><setting /></el-icon>
          系统设置
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="handleSaveSettings">保存当前配置</el-dropdown-item>
            <el-dropdown-item @click="handleLoadSettings">加载配置</el-dropdown-item>
            <el-dropdown-item divided @click="handleSystemInfo">系统信息</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Setting, UserFilled, ArrowDown } from '@element-plus/icons-vue' // 导入新图标

const router = useRouter()
const username = ref(localStorage.getItem('username') || '') // 获取当前用户名

// 检查用户是否登录
const isLoggedIn = computed(() => {
  return localStorage.getItem('access_token') !== null
})

// 监听路由变化，更新用户名（如果需要）
router.afterEach(() => {
  username.value = localStorage.getItem('username') || ''
})

// 处理保存设置
const handleSaveSettings = () => {
  ElMessage.success('设置已保存')
  // 可以触发全局事件，让相关组件保存设置
  window.dispatchEvent(new CustomEvent('save-settings'))
}

// 处理加载设置
const handleLoadSettings = () => {
  ElMessage.success('已加载最新设置')
  // 可以触发全局事件，让相关组件加载设置
  window.dispatchEvent(new CustomEvent('load-settings'))
}

// 处理系统信息
const handleSystemInfo = () => {
  ElMessage({
    dangerouslyUseHTMLString: true,
    message: `
      <div>
        <h4>MCSA-电机AI诊断系统 v1.0.0</h4>
        <p>前端: Vue 3 + Vite + Element Plus</p>
        <p>后端: Python FastAPI + Pandas + SciPy</p>
      </div>
    `
  })
}

// 处理退出登录
const handleLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('token_type')
  localStorage.removeItem('username') // 移除用户名
  username.value = '' // 清空用户名显示
  ElMessage.info('已退出登录。')
  router.push('/login') // 重定向到登录页
}
</script>

<style scoped>
.top-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 60px;
  background-color: #1a3059; /* 藏青色背景 */
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  display: flex;
  align-items: center;
}

.motor-icon {
  width: 32px;
  height: 32px;
  margin-right: 10px;
  animation: rotate 0.01s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.logo h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  color: #ffffff; /* 白色文字 */
}

.right-section {
  display: flex;
  align-items: center;
  gap: 20px; /* 增加元素间的间距 */
}

.el-dropdown-link {
  display: flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  color: #ffffff; /* 白色文字 */
}

.user-info {
  padding: 5px 10px;
  border-radius: 4px;
  background-color: rgba(255, 255, 255, 0.1);
  transition: background-color 0.3s;
}

.user-info:hover {
  background-color: rgba(255, 255, 255, 0.2);
}

.settings-dropdown {
  margin-left: 20px; /* 确保系统设置和登录/登出按钮之间有足够间距 */
}
</style> 