<template>
  <div class="cluster-topology">
    <div class="topology-header">
      <h3>集群拓扑图</h3>
      <div class="topology-controls">
        <el-button 
          :icon="Refresh" 
          @click="refreshTopology" 
          :loading="loading"
          size="small"
        >
          刷新拓扑
        </el-button>
        <el-button 
          :icon="Download" 
          @click="exportTopology" 
          size="small"
        >
          导出图片
        </el-button>
      </div>
    </div>
    
    <!-- 拓扑图容器 -->
    <div ref="topologyContainer" class="topology-container">
      <svg ref="topologySvg" width="100%" height="600">
        <!-- 数据流箭头定义 -->
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon
              points="0 0, 10 3.5, 0 7"
              fill="#409EFF"
            />
          </marker>
          
          <!-- 渐变定义 -->
          <linearGradient id="streamGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#67C23A;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#409EFF;stop-opacity:1" />
          </linearGradient>
          
          <linearGradient id="bridgeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" style="stop-color:#E6A23C;stop-opacity:1" />
            <stop offset="100%" style="stop-color:#F56C6C;stop-opacity:1" />
          </linearGradient>
        </defs>
        
        <!-- Redis节点 -->
        <g class="redis-node">
          <rect
            x="50"
            y="250"
            width="120"
            height="80"
            rx="8"
            fill="#E74C3C"
            stroke="#C0392B"
            stroke-width="2"
          />
          <text x="110" y="280" text-anchor="middle" fill="white" font-weight="bold">Redis</text>
          <text x="110" y="300" text-anchor="middle" fill="white" font-size="12">Message Queue</text>
        </g>
        
        <!-- Stream节点 -->
        <g v-for="(stream, index) in streams" :key="stream.name" class="stream-node">
          <rect
            :x="300"
            :y="150 + index * 150"
            width="200"
            height="60"
            rx="6"
            fill="url(#streamGradient)"
            stroke="#409EFF"
            stroke-width="2"
          />
          <text 
            :x="400" 
            :y="175 + index * 150" 
            text-anchor="middle" 
            fill="white" 
            font-weight="bold"
          >
            {{ stream.displayName }}
          </text>
          <text 
            :x="400" 
            :y="195 + index * 150" 
            text-anchor="middle" 
            fill="white" 
            font-size="12"
          >
            {{ stream.name }}
          </text>
        </g>
        
        <!-- 桥接器节点 -->
        <g v-for="(bridge, index) in bridges" :key="bridge.name" class="bridge-node">
          <rect
            :x="600"
            :y="150 + index * 150"
            width="180"
            height="60"
            rx="6"
            fill="url(#bridgeGradient)"
            :stroke="bridge.status === 'healthy' ? '#67C23A' : '#F56C6C'"
            stroke-width="2"
          />
          <text 
            :x="690" 
            :y="175 + index * 150" 
            text-anchor="middle" 
            fill="white" 
            font-weight="bold"
          >
            {{ bridge.displayName }}
          </text>
          <text 
            :x="690" 
            :y="195 + index * 150" 
            text-anchor="middle" 
            fill="white" 
            font-size="12"
          >
            状态: {{ bridge.status === 'healthy' ? '健康' : '警告' }}
          </text>
          
          <!-- 状态指示器 -->
          <circle
            :cx="760"
            :cy="165 + index * 150"
            r="6"
            :fill="bridge.status === 'healthy' ? '#67C23A' : '#F56C6C'"
          />
        </g>
        
        <!-- 前端WebSocket节点 -->
        <g class="frontend-node">
          <rect
            x="850"
            y="200"
            width="150"
            height="100"
            rx="8"
            fill="#9C27B0"
            stroke="#7B1FA2"
            stroke-width="2"
          />
          <text x="925" y="230" text-anchor="middle" fill="white" font-weight="bold">前端界面</text>
          <text x="925" y="250" text-anchor="middle" fill="white" font-size="12">WebSocket</text>
          <text x="925" y="270" text-anchor="middle" fill="white" font-size="12">实时更新</text>
        </g>
        
        <!-- 数据流箭头 -->
        <!-- Redis到Stream -->
        <g v-for="(stream, index) in streams" :key="`redis-to-${stream.name}`">
          <line
            x1="170"
            y1="290"
            :x2="300"
            :y2="180 + index * 150"
            stroke="#409EFF"
            stroke-width="3"
            marker-end="url(#arrowhead)"
          />
          <text
            :x="235"
            :y="235 + index * 75"
            text-anchor="middle"
            fill="#409EFF"
            font-size="12"
            font-weight="bold"
          >
            {{ stream.messageCount }}条消息
          </text>
        </g>
        
        <!-- Stream到Bridge -->
        <g v-for="(bridge, index) in bridges" :key="`stream-to-${bridge.name}`">
          <line
            :x1="500"
            :y1="180 + index * 150"
            :x2="600"
            :y2="180 + index * 150"
            stroke="#E6A23C"
            stroke-width="3"
            marker-end="url(#arrowhead)"
          />
          <text
            :x="550"
            :y="175 + index * 150"
            text-anchor="middle"
            fill="#E6A23C"
            font-size="12"
            font-weight="bold"
          >
            {{ bridge.pending }}待处理
          </text>
        </g>
        
        <!-- Bridge到Frontend -->
        <g v-for="(bridge, index) in bridges" :key="`bridge-to-frontend-${bridge.name}`">
          <line
            :x1="780"
            :y1="180 + index * 150"
            :x2="850"
            :y2="225 + index * 25"
            stroke="#9C27B0"
            stroke-width="3"
            marker-end="url(#arrowhead)"
          />
        </g>
      </svg>
    </div>
    
    <!-- 图例 -->
    <div class="topology-legend">
      <div class="legend-title">图例说明</div>
      <div class="legend-items">
        <div class="legend-item">
          <div class="legend-color" style="background: #E74C3C;"></div>
          <span>Redis消息队列</span>
        </div>
        <div class="legend-item">
          <div class="legend-color" style="background: linear-gradient(to right, #67C23A, #409EFF);"></div>
          <span>Stream数据流</span>
        </div>
        <div class="legend-item">
          <div class="legend-color" style="background: linear-gradient(to right, #E6A23C, #F56C6C);"></div>
          <span>桥接器组件</span>
        </div>
        <div class="legend-item">
          <div class="legend-color" style="background: #9C27B0;"></div>
          <span>前端WebSocket</span>
        </div>
        <div class="legend-item">
          <div class="legend-indicator healthy"></div>
          <span>健康状态</span>
        </div>
        <div class="legend-item">
          <div class="legend-indicator warning"></div>
          <span>警告状态</span>
        </div>
      </div>
    </div>
    
    <!-- 统计信息 -->
    <div class="topology-stats">
      <el-row :gutter="20">
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-value">{{ totalStreams }}</div>
              <div class="stat-label">数据流</div>
            </div>
            <el-icon class="stat-icon" color="#409EFF">
              <DataLine />
            </el-icon>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-value">{{ totalBridges }}</div>
              <div class="stat-label">桥接器</div>
            </div>
            <el-icon class="stat-icon" color="#E6A23C">
              <Connection />
            </el-icon>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-value">{{ totalPendingMessages }}</div>
              <div class="stat-label">待处理消息</div>
            </div>
            <el-icon class="stat-icon" color="#F56C6C">
              <Message />
            </el-icon>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card class="stat-card">
            <div class="stat-content">
              <div class="stat-value">{{ healthyBridges }}/{{ totalBridges }}</div>
              <div class="stat-label">健康桥接器</div>
            </div>
            <el-icon class="stat-icon" color="#67C23A">
              <SuccessFilled />
            </el-icon>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Download, DataLine, Connection, Message, SuccessFilled } from '@element-plus/icons-vue'

// 响应式数据
const loading = ref(false)
const topologyContainer = ref(null)
const topologySvg = ref(null)

// 拓扑数据
const streams = ref([
  {
    name: 'fault_diagnosis_results',
    displayName: '故障诊断结果',
    messageCount: 48
  },
  {
    name: 'vehicle_health_assessments', 
    displayName: '健康评估数据',
    messageCount: 5
  }
])

const bridges = ref([
  {
    name: 'frontend_bridge_fault',
    displayName: '故障桥接器',
    status: 'warning',
    pending: 48,
    idleMinutes: 18.0
  },
  {
    name: 'frontend_bridge_health',
    displayName: '健康桥接器', 
    status: 'warning',
    pending: 5,
    idleMinutes: 18.0
  }
])

// 计算属性
const totalStreams = computed(() => streams.value.length)
const totalBridges = computed(() => bridges.value.length)
const totalPendingMessages = computed(() => 
  bridges.value.reduce((sum, bridge) => sum + bridge.pending, 0)
)
const healthyBridges = computed(() => 
  bridges.value.filter(bridge => bridge.status === 'healthy').length
)

// 方法
const refreshTopology = async () => {
  loading.value = true
  try {
    // 这里可以调用API获取最新的拓扑数据
    // const response = await api.get('/stream/topology')
    // streams.value = response.data.streams
    // bridges.value = response.data.bridges
    
    ElMessage.success('拓扑数据已刷新')
  } catch (error) {
    console.error('刷新拓扑数据失败:', error)
    ElMessage.error('刷新拓扑数据失败')
  } finally {
    loading.value = false
  }
}

const exportTopology = () => {
  try {
    const svg = topologySvg.value
    const svgData = new XMLSerializer().serializeToString(svg)
    const canvas = document.createElement('canvas')
    canvas.width = 1200
    canvas.height = 600
    const ctx = canvas.getContext('2d')
    
    const img = new Image()
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(svgBlob)
    
    img.onload = () => {
      ctx.drawImage(img, 0, 0)
      URL.revokeObjectURL(url)
      
      // 下载图片
      const link = document.createElement('a')
      link.download = 'cluster-topology.png'
      link.href = canvas.toDataURL('image/png')
      link.click()
    }
    
    img.src = url
    ElMessage.success('拓扑图导出成功')
  } catch (error) {
    console.error('导出拓扑图失败:', error)
    ElMessage.error('导出拓扑图失败')
  }
}

onMounted(() => {
  // 初始化拓扑图
  refreshTopology()
})
</script>

<style scoped>
.cluster-topology {
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.topology-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.topology-header h3 {
  margin: 0;
  color: #303133;
}

.topology-controls {
  display: flex;
  gap: 10px;
}

.topology-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
  overflow: hidden;
}

.topology-container svg {
  display: block;
}

.topology-legend {
  background: white;
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
}

.legend-title {
  font-weight: bold;
  margin-bottom: 10px;
  color: #303133;
}

.legend-items {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-color {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  border: 1px solid #ddd;
}

.legend-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.legend-indicator.healthy {
  background: #67C23A;
}

.legend-indicator.warning {
  background: #F56C6C;
}

.topology-stats {
  margin-top: 20px;
}

.stat-card {
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stat-card :deep(.el-card__body) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  line-height: 1;
}

.stat-label {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.stat-icon {
  font-size: 32px;
  opacity: 0.8;
}

/* SVG节点样式 */
.redis-node rect,
.stream-node rect,
.bridge-node rect,
.frontend-node rect {
  transition: all 0.3s ease;
}

.redis-node:hover rect,
.stream-node:hover rect,
.bridge-node:hover rect,
.frontend-node:hover rect {
  transform: scale(1.05);
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2));
}

.redis-node text,
.stream-node text,
.bridge-node text,
.frontend-node text {
  pointer-events: none;
  user-select: none;
}
</style>