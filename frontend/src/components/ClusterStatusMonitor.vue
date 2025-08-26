<template>
  <el-card class="cluster-status-card" shadow="hover">
    <template #header>
      <div class="card-header">
        <span>🏗️ 微服务集群状态</span>
        <el-tag :type="clusterHealthType" size="small">
          {{ clusterStatus }}
        </el-tag>
      </div>
    </template>
    
    <div class="cluster-metrics">
      <!-- 整体集群健康度 -->
      <div class="metric-item">
        <div class="metric-label">集群健康度</div>
        <el-progress 
          :percentage="clusterHealth" 
          :color="healthColors"
          :stroke-width="8"
        />
      </div>
      
      <!-- Worker节点状态 -->
      <div class="metric-item">
        <div class="metric-label">Worker节点</div>
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
          <el-select v-model="selectedWorkerType" placeholder="全部类型" size="small" style="width: 220px;">
            <el-option :label="`全部类型 (${workerNodes.length})`" value="all" />
            <el-option 
              v-for="opt in workerTypeOptions" 
              :key="opt.value" 
              :label="`${opt.label} (${opt.count})`" 
              :value="opt.value" 
            />
          </el-select>
        </div>
        <div class="worker-grid">
          <div 
            v-for="worker in filteredWorkerNodes" 
            :key="worker.id"
            class="worker-node"
            :class="getWorkerStatusClass(worker.status)"
          >
            <div class="worker-name">{{ mapTypeText(worker.type) }}</div>
            <div class="worker-status">{{ worker.status }}</div>
          </div>
        </div>
      </div>
      
      <!-- 性能指标 -->
      <div class="metric-item">
        <div class="metric-label">性能指标</div>
        <div class="performance-grid">
          <div class="perf-item">
            <span class="perf-label">吞吐量</span>
            <span class="perf-value">{{ throughput }} msg/s</span>
          </div>
          <div class="perf-item">
            <span class="perf-label">响应时延</span>
            <span class="perf-value">{{ latency }}ms</span>
          </div>
          <div class="perf-item">
            <span class="perf-label">任务积压</span>
            <span class="perf-value">{{ queueLength }}</span>
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '@/api/index.js'
import { ensureConnected, getState, subscribe } from '@/stores/realtimeStore.js'

// 响应式数据
const clusterHealth = ref(95)
const workerNodes = ref([
  { id: 'worker_1', type: '匝间短路', status: 'healthy' },
  { id: 'worker_2', type: '绝缘失效', status: 'healthy' },
  { id: 'worker_3', type: '轴承故障', status: 'healthy' },
  { id: 'worker_4', type: '偏心故障', status: 'healthy' },
  { id: 'worker_5', type: '断条故障', status: 'healthy' }
])
const throughput = ref(285)
const latency = ref(18)
const queueLength = ref(12)

// 计算属性
const clusterStatus = computed(() => {
  if (clusterHealth.value > 90) return '优秀'
  if (clusterHealth.value > 70) return '良好'
  if (clusterHealth.value > 50) return '警告'
  return '故障'
})

const clusterHealthType = computed(() => {
  if (clusterHealth.value > 90) return 'success'
  if (clusterHealth.value > 70) return 'warning'
  return 'danger'
})

const healthColors = [
  { color: '#f56c6c', percentage: 20 },
  { color: '#e6a23c', percentage: 40 },
  { color: '#5cb87a', percentage: 60 },
  { color: '#1989fa', percentage: 80 },
  { color: '#6f7ad3', percentage: 100 }
]

// 方法
const getWorkerStatusClass = (status) => {
  return {
    'worker-healthy': status === 'healthy',
    'worker-warning': status === 'warning',
    'worker-error': status === 'error'
  }
}

// 🔧 Worker 类型分组与过滤
const selectedWorkerType = ref('all')
const workerTypeOptions = computed(() => {
  const map = new Map()
  for (const w of workerNodes.value) {
    const key = w.type || 'unknown'
    map.set(key, (map.get(key) || 0) + 1)
  }
  return Array.from(map.entries()).map(([value, count]) => ({ label: mapTypeText(value), value, count }))
})
const filteredWorkerNodes = computed(() => {
  if (selectedWorkerType.value === 'all') return workerNodes.value
  return workerNodes.value.filter(w => (w.type || 'unknown') === selectedWorkerType.value)
})
const mapTypeText = (type) => {
  const map = {
    'turn_fault': '匝间短路',
    'insulation': '绝缘失效',
    'bearing': '轴承故障',
    'eccentricity': '偏心故障',
    'broken_bar': '断条故障',
    'fault_results': '故障结果',
    'health': '健康评估',
    'result_aggregation': '结果聚合'
  }
  return map[type] || type || '未知'
}

const fetchClusterStatus = async () => {
  try {
    // 🚀 调用统一API封装（axios baseURL指向后端8000）
    const result = await api.getClusterStatus()
    const data = result.data
    
    // 更新真实集群数据
    clusterHealth.value = data.cluster_health || 95
    // 吞吐量改为每秒API请求次数（RPS）
    if (!window.__vtox_lastReqTs) window.__vtox_lastReqTs = null
    if (!window.__vtox_lastReqTotal) window.__vtox_lastReqTotal = null
    const nowTs = Date.now()
    const totalRequests = data.load_balancer?.total_requests || 0
    if (window.__vtox_lastReqTs !== null && window.__vtox_lastReqTotal !== null && totalRequests >= window.__vtox_lastReqTotal) {
      const deltaReq = totalRequests - window.__vtox_lastReqTotal
      const deltaSec = (nowTs - window.__vtox_lastReqTs) / 1000
      const rps = deltaSec > 0 ? deltaReq / deltaSec : 0
      throughput.value = Math.max(0, Math.round(rps))
    } else {
      throughput.value = 0
    }
    window.__vtox_lastReqTotal = totalRequests
    window.__vtox_lastReqTs = nowTs
    latency.value = Math.round(data.performance_metrics?.latency || 18)
    queueLength.value = data.performance_metrics?.queue_length || 0
    
    // 更新Worker节点数据
    if (data.worker_nodes && data.worker_nodes.length > 0) {
      workerNodes.value = data.worker_nodes.map(worker => ({
        id: worker.id,
        type: worker.type || '未知',
        status: worker.status || 'healthy'
      }))
    }
    
  } catch (error) {
    console.log('获取集群状态失败，使用模拟数据', error)
    
    // 备用模拟数据
    throughput.value = Math.round(Math.random() * 100 + 200)
    latency.value = Math.round(Math.random() * 20 + 10)
    queueLength.value = Math.round(Math.random() * 30 + 5)
    
    // 更新Worker状态 (模拟数据)
    workerNodes.value.forEach(worker => {
      worker.status = Math.random() > 0.1 ? 'healthy' : 'warning'
    })
  }
}

let statusTimer = null

onMounted(() => {
  fetchClusterStatus()
  // 每5秒更新一次状态
  statusTimer = setInterval(fetchClusterStatus, 5000)
  // 确保全局WS已连接
  ensureConnected().catch(() => {})
})

onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer)
  }
})
</script>

<style scoped>
.cluster-status-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
}

.cluster-metrics {
  display: flex;
  flex-direction: column;
  gap: 16px; /* 替代 space-y */
}

.metric-item {
  margin-bottom: 16px;
}

.metric-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.worker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 8px;
}

.worker-node {
  padding: 8px;
  border-radius: 6px;
  text-align: center;
  font-size: 12px;
  border: 1px solid #e4e7ed;
}

.worker-healthy {
  background-color: #f0f9ff;
  border-color: #67c23a;
}

.worker-warning {
  background-color: #fdf6ec;
  border-color: #e6a23c;
}

.worker-error {
  background-color: #fef0f0;
  border-color: #f56c6c;
}

.worker-name {
  font-weight: bold;
  margin-bottom: 4px;
}

.worker-status {
  color: #666;
}

.performance-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.perf-item {
  text-align: center;
  padding: 8px;
  background-color: #fafafa;
  border-radius: 4px;
}

.perf-label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.perf-value {
  display: block;
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}
</style>