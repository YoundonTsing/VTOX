<template>
  <div class="card distributed-control-panel">
    <h3>🌊 分布式车联网诊断系统</h3>
    <p class="panel-description">
      基于Redis Stream的分布式故障诊断系统，支持高并发车辆数据处理、消费者组负载均衡和实时性能监控。
    </p>
    
    <div class="distributed-controls">
      <!-- 系统状态显示 -->
      <div class="system-status">
        <div class="status-item">
          <el-tag :type="getDistributedStatusType(systemStatus.system)">
            {{ getDistributedStatusText(systemStatus.system) }}
          </el-tag>
          <span class="status-label">系统状态</span>
        </div>
        
        <!-- 未授权提示 -->
        <div v-if="systemStatus.system === 'unauthorized'" class="auth-warning">
          <el-alert
            title="需要登录认证"
            description="请先登录后再使用分布式诊断功能。系统需要验证您的身份以确保数据安全。"
            type="warning"
            show-icon
            :closable="false"
          />
        </div>
        
        <div v-if="systemStatus.system === 'running'" class="performance-info">
          <span class="metric-item">
            <i class="el-icon-cpu"></i>
            处理消息: {{ metrics.processedMessages || 0 }}
          </span>
          <span class="metric-item">
            <i class="el-icon-timer"></i>
            平均延迟: {{ metrics.averageLatency || 0 }}ms
          </span>
          <span class="metric-item">
            <i class="el-icon-user"></i>
            活跃消费者: {{ metrics.activeConsumers || 0 }}
          </span>
        </div>
      </div>

      <!-- 控制按钮 -->
      <div class="control-buttons">
        <el-button 
          type="primary" 
          @click="$emit('initialize')"
          :loading="systemStatus.initializing"
          :disabled="systemStatus.system === 'unauthorized' || systemStatus.system === 'running' || systemStatus.system === 'initializing'"
        >
          初始化系统
        </el-button>
        
        <el-button 
          type="success" 
          @click="$emit('start')"
          :loading="systemStatus.starting"
          :disabled="systemStatus.system === 'unauthorized' || (systemStatus.system !== 'initialized' && systemStatus.system !== 'stopped')"
        >
          启动分布式诊断
        </el-button>
        
        <el-button 
          type="warning" 
          @click="$emit('stop')"
          :loading="systemStatus.stopping"
          :disabled="systemStatus.system === 'unauthorized' || systemStatus.system !== 'running'"
        >
          停止分布式诊断
        </el-button>
        
        <el-button 
          type="info" 
          @click="$emit('refresh-metrics')"
          :disabled="systemStatus.system === 'unauthorized' || systemStatus.system !== 'running'"
        >
          刷新指标
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineEmits, defineProps } from 'vue';

// 📡 Props
const props = defineProps({
  systemStatus: {
    type: Object,
    required: true,
    default: () => ({
      system: 'stopped',
      initializing: false,
      starting: false,
      stopping: false,
      lastError: null
    })
  },
  metrics: {
    type: Object,
    default: () => ({
      processedMessages: 0,
      averageLatency: 0,
      activeConsumers: 0,
      lastUpdated: null
    })
  }
});

// 📤 Events
const emit = defineEmits([
  'initialize',
  'start', 
  'stop',
  'refresh-metrics'
]);

// 🎨 状态样式方法
const getDistributedStatusType = (status) => {
  const statusMap = {
    'stopped': 'info',
    'initializing': 'warning',
    'initialized': 'warning', 
    'starting': 'warning',
    'running': 'success',
    'stopping': 'warning',
    'error': 'danger',
    'unauthorized': 'warning'
  };
  return statusMap[status] || 'info';
};

const getDistributedStatusText = (status) => {
  const textMap = {
    'stopped': '已停止',
    'initializing': '初始化中',
    'initialized': '已初始化',
    'starting': '启动中', 
    'running': '运行中',
    'stopping': '停止中',
    'error': '错误',
    'unauthorized': '未授权'
  };
  return textMap[status] || '未知状态';
};
</script>

<style scoped>
.distributed-control-panel {
  margin-bottom: 20px;
}

.distributed-control-panel h3 {
  color: rgba(0, 0, 0, 0.9);
  margin: 0 0 15px 0;
  font-size: 18px;
  font-weight: 600;
}

.panel-description {
  margin: 15px 0;
  color: #606266;
  font-size: 14px;
  line-height: 1.5;
}

.distributed-controls {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.system-status {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 15px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-label {
  font-size: 14px;
  color: #606266;
}

.auth-warning {
  width: 100%;
  margin-top: 10px;
}

.performance-info {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 14px;
  color: #606266;
}

.metric-item i {
  color: #409EFF;
}

.control-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.control-buttons .el-button {
  min-width: 120px;
}

@media (max-width: 768px) {
  .system-status {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .performance-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .control-buttons {
    flex-direction: column;
  }
  
  .control-buttons .el-button {
    width: 100%;
  }
}
</style> 