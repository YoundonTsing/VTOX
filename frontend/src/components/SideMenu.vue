<template>
  <div class="side-menu">
    <el-menu
      :default-active="activeMenu"
      class="menu"
      :collapse="isCollapse"
      @select="handleSelect"
      :router="true"
      :collapse-transition="false"
    >
      <el-sub-menu index="dashboard">
        <template #title>
          <el-icon><data-analysis /></el-icon>
          <span>仪表盘</span>
        </template>
        <el-menu-item index="/dashboard">系统概览</el-menu-item>
      </el-sub-menu>
      
      <el-sub-menu index="statistics">
        <template #title>
          <el-icon><pie-chart /></el-icon>
          <span>统计分析</span>
        </template>
        <el-menu-item index="/statistics/fault-history">故障历史记录</el-menu-item>
      </el-sub-menu>
      
      <el-sub-menu index="fault-diagnosis">
        <template #title>
          <el-icon><warning /></el-icon>
          <span>故障诊断</span>
        </template>
        <el-menu-item index="/diagnosis/turn-to-turn">匝间短路诊断</el-menu-item>
        <el-menu-item index="/diagnosis/insulation">绝缘失效检测</el-menu-item>
        <el-menu-item index="/diagnosis/bearing">轴承故障诊断</el-menu-item>
        <el-menu-item index="/diagnosis/eccentricity">偏心故障诊断</el-menu-item>
        <el-menu-item index="/diagnosis/broken-bar">断条故障诊断</el-menu-item>
      </el-sub-menu>
      
      <el-sub-menu index="monitor">
        <template #title>
          <el-icon><monitor /></el-icon>
          <span>在线监测</span>
        </template>
        <el-menu-item index="/monitor/realtime">实时监测</el-menu-item>
        <el-menu-item index="/monitor/trend">趋势分析</el-menu-item>
        <el-menu-item index="/monitor/alarm">告警管理</el-menu-item>
        <el-menu-item index="/monitor/fleet-distributed">中央监测 </el-menu-item>
        <el-menu-item index="/monitor/cache-status">缓存状态监控</el-menu-item>
        <el-menu-item index="/monitor/cluster-status"> 集群状态监控</el-menu-item>
      </el-sub-menu>
      
      <el-sub-menu index="agent">
        <template #title>
          <el-icon><connection /></el-icon>
          <span>智能Agent</span>
        </template>
        <el-menu-item index="/agent">AI智能助手</el-menu-item>
        <el-menu-item index="/agent/management">Agent管理</el-menu-item>
        <el-menu-item index="/agent/tasks">任务分配</el-menu-item>
      </el-sub-menu>
      
      <el-sub-menu index="settings">
        <template #title>
          <el-icon><setting /></el-icon>
          <span>系统设置</span>
        </template>
        <el-menu-item index="/settings/threshold">阈值设置</el-menu-item>
        <el-menu-item index="/settings/parameters">参数配置</el-menu-item>
        <el-menu-item index="/config/throughput">吞吐量配置</el-menu-item>
        <el-menu-item index="/settings/user">用户管理</el-menu-item>
      </el-sub-menu>
    </el-menu>
    
    <div class="collapse-btn" @click="toggleCollapse">
      <el-icon v-if="isCollapse"><arrow-right /></el-icon>
      <el-icon v-else><arrow-left /></el-icon>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { 
  DataAnalysis, 
  Warning, 
  Monitor, 
  Setting,
  ArrowRight,
  ArrowLeft,
  PieChart,
  Connection
} from '@element-plus/icons-vue'

const route = useRoute()
const isCollapse = ref(false)

// 根据当前路由计算激活菜单项
const activeMenu = computed(() => {
  const path = route.path
  if (path === '/dashboard') return '/dashboard'
  if (path.startsWith('/diagnosis/turn-to-turn')) return '/diagnosis/turn-to-turn'
  if (path.startsWith('/diagnosis/turn-fault')) return '/diagnosis/turn-fault'
  if (path.startsWith('/diagnosis')) return path
  if (path.startsWith('/monitor')) return path
  if (path.startsWith('/settings')) return path
  if (path.startsWith('/config/throughput')) return '/config/throughput'
  if (path.startsWith('/statistics/fault-history')) return '/statistics/fault-history'
  if (path.startsWith('/agent')) return path
  return '/'
})

// 切换侧边栏折叠状态
const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
  // 触发侧边栏状态变化事件
  window.dispatchEvent(new CustomEvent('sidebar-toggle', { 
    detail: { collapsed: isCollapse.value } 
  }))
}

// 菜单项选择处理
const handleSelect = (index) => {
  console.log('Menu selected:', index)
  // 在小屏幕上自动折叠侧边栏
  if (window.innerWidth < 768) {
    isCollapse.value = true
  }
}

// 导出侧边栏状态
defineExpose({
  isCollapse
})
</script>

<style scoped>
.side-menu {
  position: relative;
  height: 100%;
  background-color: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
}

.menu {
  height: 100%;
  border-right: none;
}

.menu:not(.el-menu--collapse) {
  width: 220px;
}

/* 添加导航菜单项文字居中样式 */
:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  text-align: center;
  justify-content: center;
  font-size: 16px; /* 放大字体 */
}

:deep(.el-menu-item span),
:deep(.el-sub-menu__title span) {
  font-size: 16px; /* 放大字体 */
}

/* 确保子菜单项也居中 */
:deep(.el-menu--inline) .el-menu-item {
  text-align: center;
  justify-content: center;
  padding-left: 0 !important; /* 覆盖默认的左内边距 */
}

/* 折叠状态下图标居中 */
.el-menu--collapse :deep(.el-sub-menu__title),
.el-menu--collapse :deep(.el-menu-item) {
  display: flex;
  justify-content: center;
  padding: 0;
}

/* 弹出的子菜单居中 */
:deep(.el-menu--popup) {
  min-width: 160px;
}

:deep(.el-menu--popup) .el-menu-item {
  display: flex;
  justify-content: center;
  text-align: center;
  padding-left: 0 !important;
  padding-right: 0 !important;
}

/* 放大图标尺寸 */
:deep(.el-icon) {
  font-size: 18px;
  margin-right: 5px;
}

.collapse-btn {
  position: absolute;
  bottom: 20px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 30px;
  cursor: pointer;
  color: #909399;
  transition: all 0.3s;
}

.collapse-btn:hover {
  color: #409EFF;
}
</style> 