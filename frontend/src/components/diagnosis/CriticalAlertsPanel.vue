<template>
  <div class="card critical-alerts-panel">
    <div class="section-header">
      <h3>🚨 关键警报</h3>
      <el-badge :value="alerts.length" :max="99" class="alerts-badge">
        <el-button @click="$emit('clear-alerts')" size="small" link>
          清空警报
        </el-button>
      </el-badge>
    </div>
    
    <div class="alerts-container">
      <div v-if="alerts.length === 0" class="no-alerts">
        <el-tag type="success">暂无关键警报</el-tag>
      </div>
      <div v-else class="alerts-list">
        <el-alert
          v-for="alert in alerts"
          :key="alert.alert_id"
          :title="`车辆${alert.vehicle_id} - ${alert.alert_type} (健康评分: ${Number(alert.health_score).toFixed(1)}%)`"
          :type="getAlertType(alert.severity)"
          size="small"
          show-icon
          class="alert-item"
          closable
          @close="$emit('dismiss-alert', alert.alert_id)"
        >
          <template #default>
            <div class="alert-content">
              <div class="alert-main-info">
                <span class="fault-info">
                  <strong>故障类型:</strong> 
                  <el-tag :type="getFaultTagType(alert.fault_type)" size="mini">
                    {{ getFaultDisplayName(alert.fault_type) }}
                  </el-tag>
                </span>
                <span class="location-info">
                  <i class="el-icon-location"></i>
                  {{ alert.location || '未知位置' }}
                </span>
              </div>
              <div class="alert-meta">
                <span class="timestamp">
                  <i class="el-icon-time"></i>
                  {{ formatTime(alert.timestamp) }}
                </span>
                <span class="severity-info">
                  {{ getSeverityText(alert.severity) }}
                </span>
              </div>
            </div>
          </template>
        </el-alert>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

// 📡 Props
const props = defineProps({
  alerts: {
    type: Array,
    default: () => []
  }
});

// 📤 Events  
const emit = defineEmits([
  'clear-alerts',
  'dismiss-alert'
]);

// 🎨 样式和显示方法
const getAlertType = (severity) => {
  const severityMap = {
    'critical': 'error',
    'warning': 'warning', 
    'info': 'info',
    'normal': 'success'
  };
  return severityMap[severity] || 'warning';
};

const getFaultTagType = (faultType) => {
  const faultTagMap = {
    'turn_fault': 'danger',
    'broken_bar': 'warning',
    'bearing': 'info',
    'eccentricity': 'warning',
    'insulation': 'danger'
  };
  return faultTagMap[faultType] || 'info';
};

const getFaultDisplayName = (faultType) => {
  const displayNameMap = {
    'turn_fault': '匝间短路',
    'broken_bar': '断条故障',
    'bearing': '轴承故障',
    'eccentricity': '偏心故障', 
    'insulation': '绝缘故障'
  };
  return displayNameMap[faultType] || faultType;
};

const getSeverityText = (severity) => {
  const textMap = {
    'critical': '需要立即处理',
    'warning': '需要关注',
    'info': '信息提示',
    'normal': '正常状态'
  };
  return textMap[severity] || '未知等级';
};

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  
  try {
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return timestamp;
    
    const now = new Date();
    const diff = now - date;
    
    // 如果是今天，只显示时间
    if (diff < 24 * 60 * 60 * 1000) {
      return date.toLocaleTimeString('zh-CN', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } else {
      // 否则显示日期和时间
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit', 
        hour: '2-digit',
        minute: '2-digit'
      });
    }
  } catch (error) {
    return timestamp;
  }
};
</script>

<style scoped>
.critical-alerts-panel {
  margin-bottom: 20px;
}

.critical-alerts-panel .card {
  background: linear-gradient(135deg, #e3e7e3 0%, #764ba2 100%);
  color: rgba(0, 0, 0, 0.8);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.2);
}

.section-header h3 {
  margin: 0;
  color: rgba(0, 0, 0, 0.9);
  font-size: 16px;
  font-weight: 600;
}

.alerts-badge {
  display: flex;
  align-items: center;
}

.alerts-container {
  max-height: 400px;
  overflow-y: auto;
}

.no-alerts {
  text-align: center;
  padding: 20px;
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert-item {
  margin-bottom: 0;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.alert-item:hover {
  transform: translateX(2px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.alert-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
}

.alert-main-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.fault-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.fault-info strong {
  color: #303133;
}

.location-info {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #606266;
  font-size: 12px;
}

.location-info i {
  color: #909399;
}

.alert-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #909399;
  font-size: 11px;
}

.timestamp {
  display: flex;
  align-items: center;
  gap: 4px;
}

.severity-info {
  font-weight: 500;
  padding: 2px 6px;
  border-radius: 3px;
  background-color: rgba(240, 249, 235, 0.8);
  color: #67C23A;
}

.alert-item.el-alert--error .severity-info {
  background-color: rgba(254, 240, 240, 0.8);
  color: #F56C6C;
}

.alert-item.el-alert--warning .severity-info {
  background-color: rgba(253, 246, 236, 0.8);
  color: #E6A23C;
}

/* 滚动条样式 */
.alerts-container::-webkit-scrollbar {
  width: 6px;
}

.alerts-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.alerts-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.alerts-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .alert-main-info {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .alert-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 5px;
  }
  
  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style> 