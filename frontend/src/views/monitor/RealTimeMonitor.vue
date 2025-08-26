<template>
  <div class="real-time-monitor-container">
    <h2 class="page-title">实时监测</h2>
    
    <div class="monitor-selector">
      <el-radio-group v-model="selectedFaultType">
        <el-radio-button value="combined">综合监控</el-radio-button>
        <el-radio-button value="turn_fault">匝间短路</el-radio-button>
        <el-radio-button value="broken_bar">断条故障</el-radio-button>
        <el-radio-button value="insulation">绝缘失效</el-radio-button>
        <el-radio-button value="bearing">轴承故障</el-radio-button>
        <el-radio-button value="eccentricity">偏心故障</el-radio-button>
        <!-- 更多故障类型 -->
      </el-radio-group>
    </div>

    <component 
      :is="currentMonitorComponent" 
      :fault-type="selectedFaultType" 
      :key="selectedFaultType"
      :auto-start="isCombinedMonitoringActive" 
      @view-details="handleViewDetails"
      @combined-started="onCombinedStarted"
      @combined-stopped="onCombinedStopped" 
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, defineAsyncComponent, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// 根据路由参数或默认值设置选中的故障类型
const selectedFaultType = ref(route.query.faultType || 'combined')

// 添加综合监控状态
const isCombinedMonitoringActive = ref(false)

// 添加一个标志，用于跟踪是否正在通过查看详情按钮切换组件
const isViewingDetails = ref(false)

// 在组件挂载时输出初始状态
onMounted(() => {
  console.log('[RealTimeMonitor] 组件已挂载，初始状态:', {
    selectedFaultType: selectedFaultType.value,
    isCombinedMonitoringActive: isCombinedMonitoringActive.value,
    routeQuery: route.query
  })
})

// 动态导入组件映射
const monitorComponents = {
  combined: defineAsyncComponent(() => import('@/views/diagnosis/CombinedRealTimeDiagnosis.vue')),
  turn_fault: defineAsyncComponent(() => import('@/views/diagnosis/TurnFaultDiagnosis.vue')),
  broken_bar: defineAsyncComponent(() => import('@/views/diagnosis/BrokenBarRealTimeDiagnosis.vue')),
  insulation: defineAsyncComponent(() => import('@/views/diagnosis/InsulationRealTimeDiagnosis.vue')),
  bearing: defineAsyncComponent(() => import('@/views/diagnosis/BearingRealTimeDiagnosis.vue')),
  eccentricity: defineAsyncComponent(() => import('@/views/diagnosis/EccentricityRealTimeDiagnosis.vue'))
  // 更多故障类型组件
}

// 计算当前要渲染的组件
const currentMonitorComponent = computed(() => {
  const component = monitorComponents[selectedFaultType.value];
  console.log(`[RealTimeMonitor] 计算 currentMonitorComponent, selectedFaultType = ${selectedFaultType.value}, 组件存在: ${!!component}`);
  return component;
})

// 监听 selectedFaultType 变化，更新路由查询参数
watch(selectedFaultType, (newVal, oldVal) => {
  console.log(`[RealTimeMonitor] selectedFaultType 变化: ${oldVal} -> ${newVal}, isCombinedMonitoringActive = ${isCombinedMonitoringActive.value}`)
  router.push({ query: { faultType: newVal } })
})

// 监听路由查询参数变化，更新 selectedFaultType
watch(() => route.query.faultType, (newFaultType) => {
  console.log(`[RealTimeMonitor] 路由参数 faultType 变化为: ${newFaultType}, 当前 selectedFaultType = ${selectedFaultType.value}`)
  if (newFaultType && newFaultType !== selectedFaultType.value) {
    selectedFaultType.value = newFaultType
    console.log(`[RealTimeMonitor] 已更新 selectedFaultType = ${selectedFaultType.value}`)
  }
}, { immediate: true })

// 监听 isCombinedMonitoringActive 变化
watch(isCombinedMonitoringActive, (newVal, oldVal) => {
  console.log(`[RealTimeMonitor] isCombinedMonitoringActive 变化: ${oldVal} -> ${newVal}, 当前 selectedFaultType = ${selectedFaultType.value}`)
})

// 处理综合监控启动事件
const onCombinedStarted = () => {
  console.log('[RealTimeMonitor] 综合监控已启动，设置 isCombinedMonitoringActive = true')
  isCombinedMonitoringActive.value = true
}

// 处理综合监控停止事件
const onCombinedStopped = () => {
  console.log('[RealTimeMonitor] 综合监控已停止，设置 isCombinedMonitoringActive = false')
  
  // 如果是通过查看详情按钮切换组件，则不重置 isCombinedMonitoringActive
  if (isViewingDetails.value) {
    console.log('[RealTimeMonitor] 通过查看详情按钮切换组件，保持 isCombinedMonitoringActive = true')
    // 重置标志
    isViewingDetails.value = false
    return
  }
  
  isCombinedMonitoringActive.value = false
}

// 处理查看详情事件
const handleViewDetails = (faultType) => {
  if (faultType && monitorComponents[faultType]) {
    console.log(`[RealTimeMonitor] 接收到查看详情事件: ${faultType}，当前 isCombinedMonitoringActive = ${isCombinedMonitoringActive.value}`)
    
    // 设置标志，表示正在通过查看详情按钮切换组件
    isViewingDetails.value = true
    
    selectedFaultType.value = faultType
    // 路由更新会由 watch 自动处理
    console.log(`[RealTimeMonitor] 已切换到详情视图: ${faultType}，将传递 autoStart = ${isCombinedMonitoringActive.value} 给子组件`)
  }
}
</script>

<style scoped>
.real-time-monitor-container {
  padding: 20px;
}

.page-title {
  font-size: 24px;
  color: #303133;
  margin-bottom: 20px;
}

.monitor-selector {
  margin-bottom: 20px;
}
</style> 