<template>
  <div class="performance-metrics-panel">
    <!-- 📊 性能监控卡片 -->
    <div class="card">
      <div class="panel-header">
        <div class="header-left">
          <h3>📊 系统性能监控</h3>
          <el-tag :type="connectionStatus === 'connected' ? 'success' : 'info'" size="small">
            {{ getStatusText(connectionStatus) }}
          </el-tag>
        </div>
        <div class="header-actions">
          <el-button 
            size="small" 
            :type="isMonitoring ? 'danger' : 'primary'"
            @click="toggleMonitoring"
            :disabled="connectionStatus === 'connecting'"
          >
            {{ isMonitoring ? '停止监控' : '开始监控' }}
          </el-button>
        </div>
      </div>

      <!-- 性能指标展示 -->
      <div class="metrics-container">
        <div class="metrics-grid">
          <!-- 消息速率 -->
          <div class="metric-item">
            <div class="metric-icon message-rate">
              <i class="el-icon-message"></i>
            </div>
            <div class="metric-content">
              <div class="metric-value">{{ formatNumber(metrics.messageRate) }}</div>
              <div class="metric-unit">消息/秒</div>
            </div>
          </div>

          <!-- 内存使用 -->
          <div class="metric-item">
            <div class="metric-icon memory-usage">
              <i class="el-icon-cpu"></i>
            </div>
            <div class="metric-content">
              <div class="metric-value">{{ metrics.memoryUsage }}</div>
              <div class="metric-unit">内存使用</div>
            </div>
          </div>

          <!-- 更新延迟 -->
          <div class="metric-item">
            <div class="metric-icon update-time">
              <i class="el-icon-timer"></i>
            </div>
            <div class="metric-content">
              <div class="metric-value">{{ metrics.updateTime }}</div>
              <div class="metric-unit">响应时间</div>
            </div>
          </div>

          <!-- 连接状态 -->
          <div class="metric-item">
            <div class="metric-icon connection-status">
              <i class="el-icon-connection"></i>
            </div>
            <div class="metric-content">
              <div class="metric-value">{{ getUptime() }}</div>
              <div class="metric-unit">运行时间</div>
            </div>
          </div>
        </div>

        <!-- 最后更新时间 -->
        <div v-if="connectionStatus === 'connected'" class="last-update-info">
          <el-text size="small" type="info">
            <i class="el-icon-refresh"></i>
            最后更新: {{ getLastUpdateTime() }}
          </el-text>
        </div>

        <!-- 操作按钮 -->
        <div class="action-buttons">
          <el-button size="small" @click="refreshMetrics" :loading="refreshing">
            <i class="el-icon-refresh"></i>
            刷新数据
          </el-button>
          <el-button size="small" type="warning" @click="resetMetrics">
            <i class="el-icon-delete"></i>
            重置统计
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, defineProps, defineEmits } from 'vue';
import { ElMessage } from 'element-plus';

// 组件属性
const props = defineProps({
  connectionStatus: {
    type: String,
    default: 'disconnected'
  },
  isMonitoring: {
    type: Boolean,
    default: false
  },
  metrics: {
    type: Object,
    default: () => ({
      messageRate: 0,
      memoryUsage: '0 MB',
      updateTime: '0 ms'
    })
  }
});

// 组件事件
const emit = defineEmits([
  'toggle-monitoring',
  'refresh-metrics', 
  'reset-metrics'
]);

// 响应式数据
const refreshing = ref(false);
const startTime = ref(Date.now());

// 计算属性
const canToggleMonitoring = computed(() => {
  return props.connectionStatus !== 'connecting';
});

// 工具方法
const formatNumber = (num) => {
  if (typeof num !== 'number') return '0';
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
};

const getStatusText = (status) => {
  const statusMap = {
    connected: '已连接',
    connecting: '连接中',
    disconnected: '未连接',
    disconnecting: '断开中',
    error: '连接错误'
  };
  return statusMap[status] || '未知状态';
};

const getUptime = () => {
  if (props.connectionStatus !== 'connected') return '0s';
  const uptime = Math.floor((Date.now() - startTime.value) / 1000);
  const minutes = Math.floor(uptime / 60);
  const seconds = uptime % 60;
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
};

const getLastUpdateTime = () => {
  return new Date().toLocaleTimeString();
};

// 事件处理方法
const toggleMonitoring = () => {
  if (!canToggleMonitoring.value) return;
  
  if (!props.isMonitoring) {
    startTime.value = Date.now();
  }
  
  emit('toggle-monitoring', !props.isMonitoring);
  
  ElMessage({
    type: props.isMonitoring ? 'warning' : 'success',
    message: props.isMonitoring ? '性能监控已停止' : '性能监控已启动'
  });
};

const refreshMetrics = async () => {
  refreshing.value = true;
  
  try {
    emit('refresh-metrics');
    ElMessage.success('性能数据已刷新');
  } catch (error) {
    ElMessage.error('刷新失败');
  } finally {
    setTimeout(() => {
      refreshing.value = false;
    }, 500);
  }
};

const resetMetrics = () => {
  emit('reset-metrics');
  startTime.value = Date.now();
  ElMessage.info('性能统计已重置');
};
</script>

<style scoped>
.performance-metrics-panel {
  margin-bottom: 20px;
}

.card {
  background: linear-gradient(135deg, #e3e7e3 0%, #764ba2 100%);
  border-radius: var(--radius-md, 8px);
  box-shadow: var(--shadow-light, 0 2px 12px 0 rgba(0,0,0,0.1));
  padding: var(--spacing-lg, 20px);
  border: 1px solid var(--border-light, #EBEEF5);
  color: rgba(0, 0, 0, 0.8);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg, 20px);
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.2);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h3 {
  margin: 0;
  color: rgba(0, 0, 0, 0.9);
  font-size: 18px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.metrics-container {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md, 16px);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-md, 16px);
}

.metric-item {
  display: flex;
  align-items: center;
  padding: var(--spacing-md, 16px);
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-md, 8px);
  border: 1px solid rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.metric-item:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(0, 0, 0, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.metric-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: var(--spacing-sm, 12px);
  font-size: 18px;
  color: white;
}

.metric-icon.message-rate {
  background: linear-gradient(135deg, #67C23A, #85CE61);
}

.metric-icon.memory-usage {
  background: linear-gradient(135deg, #E6A23C, #EEBE77);
}

.metric-icon.update-time {
  background: linear-gradient(135deg, #409EFF, #79BBFF);
}

.metric-icon.connection-status {
  background: linear-gradient(135deg, #F56C6C, #F78989);
}

.metric-content {
  flex: 1;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: rgba(0, 0, 0, 0.9);
  line-height: 1.2;
}

.metric-unit {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.6);
  margin-top: 4px;
}

.last-update-info {
  text-align: center;
  padding: var(--spacing-sm, 12px);
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-sm, 4px);
  border: 1px solid rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(10px);
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: var(--spacing-sm, 12px);
  padding-top: var(--spacing-md, 16px);
  border-top: 1px solid rgba(0, 0, 0, 0.2);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .panel-header {
    flex-direction: column;
    gap: var(--spacing-sm, 12px);
    align-items: stretch;
  }
  
  .header-left {
    justify-content: center;
  }
  
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  
  .action-buttons {
    flex-direction: column;
  }
}

@media (max-width: 480px) {
  .metric-item {
    padding: var(--spacing-sm, 12px);
  }
  
  .metric-icon {
    width: 32px;
    height: 32px;
    font-size: 14px;
    margin-right: var(--spacing-xs, 8px);
  }
  
  .metric-value {
    font-size: 20px;
  }
}
</style> 