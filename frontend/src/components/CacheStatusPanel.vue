<template>
  <div class="cache-status-panel">
    <div class="panel-header">
      <h3>🗄️ 缓存状态监控</h3>
      <div class="panel-controls">
        <button 
          class="refresh-btn" 
          @click="refreshCacheStatus"
          :disabled="isRefreshing"
          title="刷新缓存状态"
        >
          <i :class="['fas', 'fa-sync-alt', { 'fa-spin': isRefreshing }]"></i>
          <span>刷新</span>
        </button>
        <button 
          class="clear-cache-btn" 
          @click="clearCache"
          :disabled="isClearing"
          title="清空缓存"
        >
          <i :class="['fas', 'fa-trash-alt', { 'fa-spin': isClearing }]"></i>
          <span>清空缓存</span>
        </button>
      </div>
    </div>

    <div class="cache-metrics">
      <!-- 缓存概览 -->
      <div class="metric-group">
        <h4>📊 缓存概览</h4>
        <div class="metrics-grid">
          <div class="metric-item">
            <span class="metric-label">缓存大小</span>
            <span class="metric-value">{{ formatSize(cacheStatus.totalSize) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">缓存项目</span>
            <span class="metric-value">{{ cacheStatus.itemCount }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">命中率</span>
            <span class="metric-value">{{ cacheStatus.hitRate }}%</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">最后更新</span>
            <span class="metric-value">{{ formatTime(cacheStatus.lastUpdate) }}</span>
          </div>
        </div>
      </div>

      <!-- WebSocket缓存 -->
      <div class="metric-group">
        <h4>🔌 WebSocket缓存</h4>
        <div class="metrics-grid">
          <div class="metric-item">
            <span class="metric-label">消息缓冲区</span>
            <span class="metric-value">{{ wsCache.bufferSize }}/{{ wsCache.bufferCapacity }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">缓冲区利用率</span>
            <span class="metric-value">{{ Math.round(wsCache.bufferUtilization) }}%</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">消息队列</span>
            <span class="metric-value">{{ wsCache.queueLength }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">处理延迟</span>
            <span class="metric-value">{{ wsCache.latency }}ms</span>
          </div>
        </div>
      </div>

      <!-- 诊断数据缓存 -->
      <div class="metric-group">
        <h4>🔬 诊断数据缓存</h4>
        <div class="metrics-grid">
          <div class="metric-item">
            <span class="metric-label">历史数据</span>
            <span class="metric-value">{{ formatSize(diagnosisCache.historySize) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">图表缓存</span>
            <span class="metric-value">{{ diagnosisCache.chartCacheCount }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">特征缓存</span>
            <span class="metric-value">{{ diagnosisCache.featureCacheCount }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">缓存有效期</span>
            <span class="metric-value">{{ diagnosisCache.ttl }}s</span>
          </div>
        </div>
      </div>

      <!-- 浏览器存储 -->
      <div class="metric-group">
        <h4>💾 浏览器存储</h4>
        <div class="metrics-grid">
          <div class="metric-item">
            <span class="metric-label">localStorage</span>
            <span class="metric-value">{{ formatSize(browserCache.localStorage) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">sessionStorage</span>
            <span class="metric-value">{{ formatSize(browserCache.sessionStorage) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">IndexedDB</span>
            <span class="metric-value">{{ formatSize(browserCache.indexedDB) }}</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">配额使用</span>
            <span class="metric-value">{{ browserCache.quotaUsage }}%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 缓存健康状态 -->
    <div class="cache-health">
      <div class="health-indicator">
        <div :class="['health-status', getHealthStatusClass()]">
          <i :class="getHealthIcon()"></i>
          <span>{{ getHealthText() }}</span>
        </div>
        <div class="health-details">
          <div v-for="issue in healthIssues" :key="issue.type" class="health-issue">
            <i :class="['fas', issue.severity === 'warning' ? 'fa-exclamation-triangle' : 'fa-times-circle']"></i>
            <span>{{ issue.message }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue';
import globalWebSocketManager from '@/utils/webSocketManager.js';

export default {
  name: 'CacheStatusPanel',
  
  setup() {
    // 响应式数据
    const isRefreshing = ref(false);
    const isClearing = ref(false);
    
    const cacheStatus = reactive({
      totalSize: 0,
      itemCount: 0,
      hitRate: 85,
      lastUpdate: Date.now()
    });
    
    const wsCache = reactive({
      bufferSize: 0,
      bufferCapacity: 500,
      bufferUtilization: 0,
      queueLength: 0,
      latency: 0
    });
    
    const diagnosisCache = reactive({
      historySize: 0,
      chartCacheCount: 0,
      featureCacheCount: 0,
      ttl: 300
    });
    
    const browserCache = reactive({
      localStorage: 0,
      sessionStorage: 0,
      indexedDB: 0,
      quotaUsage: 0
    });
    
    const healthIssues = ref([]);
    
    // 定时器
    let refreshInterval = null;
    
    // 计算属性
    const overallHealth = computed(() => {
      if (healthIssues.value.length === 0) return 'good';
      if (healthIssues.value.some(issue => issue.severity === 'error')) return 'poor';
      return 'warning';
    });
    
    // 方法
    const formatSize = (bytes) => {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
    };
    
    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString();
    };
    
    const getHealthStatusClass = () => {
      return `health-${overallHealth.value}`;
    };
    
    const getHealthIcon = () => {
      switch (overallHealth.value) {
        case 'good': return 'fas fa-check-circle';
        case 'warning': return 'fas fa-exclamation-triangle';
        case 'poor': return 'fas fa-times-circle';
        default: return 'fas fa-question-circle';
      }
    };
    
    const getHealthText = () => {
      switch (overallHealth.value) {
        case 'good': return '缓存状态良好';
        case 'warning': return '缓存状态警告';
        case 'poor': return '缓存状态异常';
        default: return '未知状态';
      }
    };
    
    const refreshCacheStatus = async () => {
      isRefreshing.value = true;
      
      try {
        // 更新WebSocket缓存状态
        const wsStats = globalWebSocketManager.getDetailedStats();
        wsCache.bufferSize = wsStats.bufferSize || 0;
        wsCache.bufferUtilization = wsStats.bufferUtilization || 0;
        wsCache.queueLength = wsStats.queuedBatches || 0;
        wsCache.latency = wsStats.latencyMs || 0;
        
        // 更新浏览器存储状态
        browserCache.localStorage = calculateLocalStorageSize();
        browserCache.sessionStorage = calculateSessionStorageSize();
        
        // 计算配额使用情况
        if ('storage' in navigator && 'estimate' in navigator.storage) {
          const estimate = await navigator.storage.estimate();
          browserCache.quotaUsage = Math.round((estimate.usage / estimate.quota) * 100);
        }
        
        // 更新整体缓存状态
        cacheStatus.totalSize = browserCache.localStorage + browserCache.sessionStorage;
        cacheStatus.itemCount = localStorage.length + sessionStorage.length;
        cacheStatus.lastUpdate = Date.now();
        
        // 检查健康状态
        checkCacheHealth();
        
      } catch (error) {
        console.error('刷新缓存状态失败:', error);
      } finally {
        isRefreshing.value = false;
      }
    };
    
    const clearCache = async () => {
      if (!confirm('确定要清空所有缓存吗？这将清除所有本地存储的数据。')) {
        return;
      }
      
      isClearing.value = true;
      
      try {
        // 清空localStorage（保留重要配置）
        const importantKeys = ['access_token', 'user_settings'];
        const backup = {};
        importantKeys.forEach(key => {
          if (localStorage.getItem(key)) {
            backup[key] = localStorage.getItem(key);
          }
        });
        
        localStorage.clear();
        
        // 恢复重要配置
        Object.entries(backup).forEach(([key, value]) => {
          localStorage.setItem(key, value);
        });
        
        // 清空sessionStorage
        sessionStorage.clear();
        
        // 重置WebSocket缓存
        if (globalWebSocketManager.resetStats) {
          globalWebSocketManager.resetStats();
        }
        
        // 刷新状态
        await refreshCacheStatus();
        
        console.log('缓存清理完成');
        
      } catch (error) {
        console.error('清空缓存失败:', error);
      } finally {
        isClearing.value = false;
      }
    };
    
    const calculateLocalStorageSize = () => {
      let total = 0;
      for (let key in localStorage) {
        if (localStorage.hasOwnProperty(key)) {
          total += localStorage[key].length + key.length;
        }
      }
      return total;
    };
    
    const calculateSessionStorageSize = () => {
      let total = 0;
      for (let key in sessionStorage) {
        if (sessionStorage.hasOwnProperty(key)) {
          total += sessionStorage[key].length + key.length;
        }
      }
      return total;
    };
    
    const checkCacheHealth = () => {
      const issues = [];
      
      // 检查缓冲区使用率
      if (wsCache.bufferUtilization > 90) {
        issues.push({
          type: 'buffer_high',
          severity: 'error',
          message: 'WebSocket缓冲区使用率过高'
        });
      } else if (wsCache.bufferUtilization > 70) {
        issues.push({
          type: 'buffer_warning',
          severity: 'warning',
          message: 'WebSocket缓冲区使用率较高'
        });
      }
      
      // 检查延迟
      if (wsCache.latency > 1000) {
        issues.push({
          type: 'latency_high',
          severity: 'error',
          message: '消息处理延迟过高'
        });
      } else if (wsCache.latency > 500) {
        issues.push({
          type: 'latency_warning',
          severity: 'warning',
          message: '消息处理延迟较高'
        });
      }
      
      // 检查浏览器存储配额
      if (browserCache.quotaUsage > 90) {
        issues.push({
          type: 'quota_high',
          severity: 'error',
          message: '浏览器存储配额即将用完'
        });
      } else if (browserCache.quotaUsage > 70) {
        issues.push({
          type: 'quota_warning',
          severity: 'warning',
          message: '浏览器存储配额使用较高'
        });
      }
      
      healthIssues.value = issues;
    };
    
    // 生命周期
    onMounted(() => {
      refreshCacheStatus();
      
      // 定时刷新
      refreshInterval = setInterval(refreshCacheStatus, 5000);
    });
    
    onUnmounted(() => {
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    });
    
    return {
      isRefreshing,
      isClearing,
      cacheStatus,
      wsCache,
      diagnosisCache,
      browserCache,
      healthIssues,
      formatSize,
      formatTime,
      getHealthStatusClass,
      getHealthIcon,
      getHealthText,
      refreshCacheStatus,
      clearCache
    };
  }
};
</script>

<style scoped>
.cache-status-panel {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 20px;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.panel-header h3 {
  margin: 0;
  color: #e2e8f0;
  font-size: 1.1rem;
  font-weight: 600;
}

.panel-controls {
  display: flex;
  gap: 10px;
}

.refresh-btn,
.clear-cache-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.refresh-btn {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  color: white;
}

.refresh-btn:hover {
  background: linear-gradient(135deg, #2563eb, #1e40af);
  transform: translateY(-1px);
}

.clear-cache-btn {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: white;
}

.clear-cache-btn:hover {
  background: linear-gradient(135deg, #dc2626, #b91c1c);
  transform: translateY(-1px);
}

.refresh-btn:disabled,
.clear-cache-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.cache-metrics {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.metric-group {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  padding: 16px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.metric-group h4 {
  margin: 0 0 12px 0;
  color: #94a3b8;
  font-size: 0.95rem;
  font-weight: 600;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.metric-label {
  color: #cbd5e1;
  font-size: 0.85rem;
  font-weight: 500;
}

.metric-value {
  color: #e2e8f0;
  font-size: 0.85rem;
  font-weight: 600;
  font-family: 'Consolas', 'Monaco', monospace;
}

.cache-health {
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.03);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.health-indicator {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.health-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 0.9rem;
}

.health-good {
  color: #10b981;
}

.health-warning {
  color: #f59e0b;
}

.health-poor {
  color: #ef4444;
}

.health-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-left: 24px;
}

.health-issue {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #94a3b8;
  font-size: 0.8rem;
}

.health-issue i.fa-exclamation-triangle {
  color: #f59e0b;
}

.health-issue i.fa-times-circle {
  color: #ef4444;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .panel-header {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }
  
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  
  .metric-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
}
</style> 