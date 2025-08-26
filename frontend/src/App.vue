<template>
  <div class="app-container">
    <top-nav-bar v-if="!isLoginPage" />
    
    <div class="main-container">
      <side-menu v-if="!isLoginPage" ref="sideMenu" />
      
      <div class="content-container" :class="{ 'menu-collapsed': menuCollapsed && !isLoginPage, 'full-width': isLoginPage }">
        <div class="content-wrapper">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </div>
        
        <footer class="app-footer" v-if="!isLoginPage">
          <p>&copy; {{ currentYear }} MCSA-电机AI诊断系统 | 版本 1.0.0</p>
        </footer>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import TopNavBar from '@/components/TopNavBar.vue'
import SideMenu from '@/components/SideMenu.vue'

const sideMenu = ref(null)
const menuCollapsed = ref(false)
const currentYear = computed(() => new Date().getFullYear())
const route = useRoute()

// 判断当前是否为登录页面
const isLoginPage = computed(() => {
  return route.path === '/login'
})

// 监听侧边栏状态变化
onMounted(() => {
  window.addEventListener('sidebar-toggle', (event) => {
    menuCollapsed.value = event.detail.collapsed
  })
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB',
  'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  background-color: #f5f7fa;
}

.app-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.main-container {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.content-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: auto;
  transition: all 0.3s;
  margin-left: 30px;
}

.content-container.menu-collapsed {
  margin-left: 60px;
}

.content-container.full-width {
  margin-left: 0;
  width: 100%;
}

.content-wrapper {
  flex: 1;
  padding: 20px 20px 20px 10px;
}

.app-footer {
  text-align: center;
  padding: 15px;
  color: #909399;
  font-size: 12px;
  border-top: 1px solid #ebeef5;
  background-color: #fff;
}

/* 路由过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media screen and (max-width: 768px) {
  .content-container {
    margin-left: 0;
  }
}
</style> 