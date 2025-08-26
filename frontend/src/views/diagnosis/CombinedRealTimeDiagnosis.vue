<template>
  <div class="combined-diagnosis-container">
    <!-- 📦 分布式系统控制面板 (子组件) -->
    <DistributedSystemPanel
      :system-status="distributedStatus"
      :metrics="distributedMetrics"
      @initialize="initializeDistributedSystem"
      @start="startDistributedSystem"
      @stop="stopDistributedSystem"
      @refresh-metrics="refreshSystemMetrics"
    />
    


    


    <!-- 📦 关键警报面板 (子组件) -->
    <CriticalAlertsPanel
      v-if="distributedStatus.system === 'running'"
      :alerts="criticalAlerts"
      @clear-alerts="clearCriticalAlerts"
      @dismiss-alert="dismissAlert"
    />

    <!-- 📦 性能监控面板 (子组件) -->
    <PerformanceMetricsPanel
      v-if="distributedStatus.system === 'running'"
      :connection-status="connectionStatus"
      :is-monitoring="isMonitoring"
      :metrics="performanceMetrics"
      @toggle-monitoring="toggleMonitoring"
      @refresh-metrics="refreshPerformanceMetrics"
      @reset-metrics="resetPerformanceMetrics"
    />

    <div class="card">
      <div class="monitor-controls">
        <div class="monitor-header">
          <h3>实时监控</h3>
          <el-tag :type="getConnectionStatusType(connectionStatus)" size="small">
            {{ getConnectionStatusText(connectionStatus) }}
          </el-tag>
        </div>
        
        <div class="control-actions">
          <el-button 
            :type="connectionStatus === 'connected' ? 'danger' : 'primary'" 
            @click="connectionStatus === 'connected' ? stopMonitoring() : startMonitoring()"
            :disabled="connectionStatus === 'connecting'"
          >
            {{ connectionStatus === 'connected' ? '停止' : '开始' }}
          </el-button>
          <el-button v-if="connectionStatus === 'connected'" type="warning" size="small" @click="resetConnectionTime">
            重置
          </el-button>
        </div>
      </div>
      
      <!-- 运行时信息（仅在连接时显示） -->
      <div v-if="isMonitoring && connectionStatus === 'connected'" class="runtime-info">
        <span class="info-item">
          <i class="el-icon-time"></i>
          {{ formatConnectionDuration() }}
        </span>
        <span class="info-item">
          <i class="el-icon-cpu"></i>
          {{ performanceMetrics.memoryUsage }}
        </span>
        <span class="info-item">
          <i class="el-icon-timer"></i>
          {{ performanceMetrics.updateTime }}
        </span>
      </div>
    </div>

    <div v-if="connectionStatus === 'connected'" class="dashboard-grid">
      <div v-for="fault in faultTypes" :key="fault.type" class="summary-card" :class="getStatusClass(getStatus(latestDiagnoses[fault.type]))">
        <div class="card-header">
          <div class="header-content">
            <h3 class="fault-title">{{ fault.name }}</h3>
          </div>
          <el-button 
            type="primary" 
            link 
            @click.stop="viewDetails(fault.type);"
            class="details-button"
          >
            查看详情
          </el-button>
          <el-tag
            size="large"
            :type="getTagType(getStatus(latestDiagnoses[fault.type]))"
            class="status-tag"
          >
            {{ getStatusText(getStatus(latestDiagnoses[fault.type])) }}
          </el-tag>
        </div>
        <div class="card-body">
          <p class="fault-score">
            故障评分: <strong>{{ formatScore(latestDiagnoses[fault.type]) }}</strong>
          </p>
          <div class="feature-list">
            <div v-for="feature in fault.features" :key="feature.key" class="feature-item">
              <span class="feature-name">{{ feature.name }}</span>
              <span class="feature-value">{{ formatFeature(latestDiagnoses[fault.type].latest, feature) }}</span>
              <span class="feature-description">{{ feature.description }}</span>
            </div>
          </div>
          <p class="last-update">
            上次更新: {{ formatLastUpdate(latestDiagnoses[fault.type]) }}
          </p>
        </div>
        <div class="card-footer">
           <!-- 移除重复的查看详情链接 -->
          <el-button 
            link 
            :icon="expandedStates[fault.type] ? 'el-icon-arrow-up' : 'el-icon-arrow-down'"
            @click="toggleExpand(fault.type)"
            class="expand-toggle-button"
          >
            {{ expandedStates[fault.type] ? '收起图表' : '展开图表' }}
          </el-button>
        </div>

        <el-collapse-transition>
          <div v-show="expandedStates[fault.type]" class="charts-container">
            <h4>实时图表</h4>
            <el-tabs type="border-card">
              <el-tab-pane label="时域波形">
                <div class="chart-wrapper">
                  <high-performance-line-chart
                    v-if="latestDiagnoses[fault.type].timeSeries && latestDiagnoses[fault.type].timeSeries.labels.length > 0"
                    :chart-data="latestDiagnoses[fault.type].timeSeries"
                    :chart-id="`time-series-${fault.type}`"
                    :height="400"
                    :options="timeChartOptions(fault)"
                    :max-data-points="50"
                    :sampling-rate="3"
                    update-mode="incremental"
                  />
                  <el-empty v-else description="暂无时域波形数据" :image-size="50" />
                </div>
              </el-tab-pane>
              <el-tab-pane :label="fault.type === 'turn_fault' ? '频谱分析' : '特征趋势'">
                <div class="chart-wrapper">
                  <high-performance-line-chart
                    v-if="(fault.type === 'turn_fault' ? latestDiagnoses[fault.type].spectrum : latestDiagnoses[fault.type].featureTrend) && (fault.type === 'turn_fault' ? latestDiagnoses[fault.type].spectrum.labels.length > 0 : latestDiagnoses[fault.type].featureTrend.labels.length > 0)"
                    :chart-data="fault.type === 'turn_fault' ? latestDiagnoses[fault.type].spectrum : latestDiagnoses[fault.type].featureTrend"
                    :chart-id="`second-chart-${fault.type}`"
                    :height="400"
                    :options="fault.type === 'turn_fault' ? spectrumOptions(fault) : featureTrendOptions(fault)"
                    :max-data-points="fault.type === 'turn_fault' ? 30 : 40"
                    :sampling-rate="fault.type === 'turn_fault' ? 4 : 2"
                    update-mode="incremental"
                  />
                  <el-empty v-else :description="fault.type === 'turn_fault' ? '暂无频谱数据' : '暂无特征趋势数据'" :image-size="50" />
                </div>
              </el-tab-pane>
              <el-tab-pane label="历史趋势">
                <div class="chart-wrapper">
                  <high-performance-line-chart
                    v-if="latestDiagnoses[fault.type].historyChart && latestDiagnoses[fault.type].historyChart.labels.length > 0"
                    :chart-data="latestDiagnoses[fault.type].historyChart"
                    :chart-id="`history-chart-${fault.type}`"
                    :height="400"
                    :options="historyChartOptions(fault)"
                    :max-data-points="20"
                    :sampling-rate="1"
                    update-mode="incremental"
                  />
                  <el-empty v-else description="暂无历史趋势数据" :image-size="50" />
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-collapse-transition>
      </div>
    </div>

    <div v-else class="no-data-message">
      <el-empty description="请点击 开始监控 以查看实时状态" />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onUnmounted, onMounted, defineEmits, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useRouter } from 'vue-router';

import globalDataManager from '@/utils/dataManager.js'; // 数据管理器
import globalWebSocketManager from '@/utils/webSocketManager.js'; // WebSocket管理器
import api from '@/api/index.js'; // API接口
import Chart from 'chart.js/auto'; // Chart.js图表库

// 📦 子组件导入
import DistributedSystemPanel from '@/components/diagnosis/DistributedSystemPanel.vue';
import CriticalAlertsPanel from '@/components/diagnosis/CriticalAlertsPanel.vue';
import PerformanceMetricsPanel from '@/components/diagnosis/PerformanceMetricsPanel.vue';
import HighPerformanceLineChart from '@/components/charts/HighPerformanceLineChart.vue';

const router = useRouter();

// 使用全局数据和WebSocket管理器
const connectionStatus = ref('disconnected');
const isMonitoring = ref(false);

// 图表实例管理
let faultDistributionChartInstance = null;

// 性能监控
const performanceMetrics = ref({
  messageRate: 0,
  memoryUsage: '0 MB',
  updateTime: '0 ms'
});

// 添加一个变量来跟踪是否是通过查看详情按钮跳转的
const isNavigatingToDetails = ref(false);

// ==========================================
// 分布式诊断系统相关数据
// ==========================================

// 分布式系统状态
const distributedStatus = reactive({
  system: 'stopped', // stopped, initializing, initialized, starting, running, stopping, error
  initializing: false,
  starting: false,
  stopping: false,
  lastError: null
});

// 分布式系统性能指标
const distributedMetrics = reactive({
  processedMessages: 0,
  averageLatency: 0,
  activeConsumers: 0,
  lastUpdated: null
});

// 车辆模拟配置
const simulationConfig = reactive({
  vehicleCount: 10,  // 默认10辆车
  faultType: 'normal',
  running: false,
  interval: null,
  vehicles: []
});

// 关键警报列表
const criticalAlerts = ref([]);

// 车队管理状态
const fleetManagement = reactive({
  status: 'stopped', // stopped, initialized, starting, running, stopping, error
  initializing: false,
  starting: false,
  stopping: false,
  runtime: null,
  lastError: null
});

// 车队配置
const fleetConfig = reactive({
  fleetSize: 10,  // 默认10辆车
  durationMinutes: 0, // 0表示持续运行
  testMode: false
});

// 车队统计数据
const fleetStats = ref(null);



// 定义事件
const emit = defineEmits(['view-details', 'combined-started', 'combined-stopped']);

const faultTypes = ref([
  { 
    type: 'turn_fault', 
    name: '匝间短路故障',
    timeSeriesYAxisLabel: '电流 (A)',
    spectrumXAxisLabel: '频率 (Hz)',
    spectrumYAxisLabel: '幅值',
    historyYAxisLabel: '故障评分',
    features: [
      { key: 'current_imbalance', name: '电流不平衡度', unit: '%', description: '三相电流幅值偏差' },
      { key: 'negative_sequence_ratio', name: '负序分量比例', unit: '%', description: '负序电流分量占比' },
      { key: 'third_harmonic_ratio', name: '三次谐波比例', unit: '%', description: '三次谐波与基波幅值比' }
    ]
  },
  { 
    type: 'broken_bar', 
    name: '断条故障',
    timeSeriesYAxisLabel: '电流 (A)',
    featureTrendYAxisLabel: '指标值 (%)',
    historyYAxisLabel: '故障评分',
    features: [
      { key: 'sideband_ratio', name: '边带幅值比', unit: '%', description: '断条特征边带与基波幅值比' },
      { key: 'normalized_fault_index', name: '归一化故障指数', unit: '%', description: '断条故障的综合评估指数' },
      { key: 'broken_bar_count', name: '估计断条数', unit: '', description: '系统估计的断裂导条数量' }
    ]
  },
  { 
    type: 'insulation', 
    name: '绝缘失效',
    timeSeriesYAxisLabel: '绝缘电阻 (MΩ)',
    timeSeriesY1AxisLabel: '泄漏电流 (mA)', /* For dual axis */
    featureTrendYAxisLabel: '指标值 (%)',
    historyYAxisLabel: '绝缘劣化度',
    features: [
      { key: 'insulation_resistance', name: '绝缘电阻', unit: 'MΩ', description: '电机绝缘对地电阻' },
      { key: 'leakage_current', name: '泄漏电流', unit: 'mA', description: '通过绝缘层的电流' },
      { key: 'dielectric_loss', name: '介质损耗', unit: '%', description: '绝缘材料的能量损耗' }
    ]
  },
  { 
    type: 'bearing', 
    name: '轴承故障',
    timeSeriesYAxisLabel: '幅值',
    featureTrendYAxisLabel: '指标值',
    historyYAxisLabel: '故障评分',
    features: [
      { key: 'crest_factor', name: '冲击因子', unit: '', description: '振动信号峰值与有效值之比' },
      { key: 'kurtosis', name: '峭度', unit: '', description: '振动信号的峰态值' },
      { key: 'bearing_characteristic_frequency', name: '特征频率', unit: 'Hz', description: '与轴承故障相关的频率' }
    ]
  },
  { 
    type: 'eccentricity', 
    name: '偏心故障',
    timeSeriesYAxisLabel: '电流 (A)',
    featureTrendYAxisLabel: '指标值 (%)',
    historyYAxisLabel: '故障评分',
    features: [
      { key: 'static_ecc_ratio', name: '静态偏心率', unit: '%', description: '定子转子中心不重合度' },
      { key: 'dynamic_ecc_ratio', name: '动态偏心率', unit: '%', description: '转子旋转中心偏离几何中心程度' },
      { key: 'eccentricity_index', name: '综合指数', unit: '%', description: '反映偏心严重程度的综合指数' }
    ]
  }
]);

// 使用计算属性从数据管理器获取数据
const latestDiagnoses = computed(() => {
  const result = {};
  faultTypes.value.forEach(fault => {
    const data = globalDataManager.getData(fault.type);
    result[fault.type] = data || {
      latest: null,
      timeSeries: { labels: [], datasets: [] },
      spectrum: { labels: [], datasets: [] },
      featureTrend: { labels: [], datasets: [] },
      historyChart: { labels: [], datasets: [] },
      history: [],
      isExpanded: false
    };
  });
  return result;
});

// 展开状态管理
const expandedStates = reactive({
  turn_fault: false,
  broken_bar: false,
  insulation: false,
  bearing: false,
  eccentricity: false
});

// 图表配置 (通用部分，Y轴标签动态设置)
const baseChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' },
    tooltip: { mode: 'index', intersect: false }
  },
  elements: { line: { tension: 0.2 }, point: { radius: 0 } },
  animation: false
};

const timeChartOptions = (faultConfig) => ({
  ...baseChartOptions,
  scales: {
    x: { 
      title: { display: true, text: '时间 (北京时间)' },
      ticks: {
        maxTicksLimit: 10 // 最多显示10个刻度，防止标签重叠
      }
    },
    y: {
      type: 'linear',
      position: 'left',
      title: { display: true, text: faultConfig.timeSeriesYAxisLabel || '幅值' },
      grid: { display: true, color: 'rgba(200, 200, 200, 0.3)', lineWidth: 0.5 }
    },
    ...(faultConfig.timeSeriesY1AxisLabel && {
      y1: {
        type: 'linear',
        position: 'right',
        title: { display: true, text: faultConfig.timeSeriesY1AxisLabel },
        grid: { drawOnChartArea: false }
      }
    })
  },
  plugins: { ...baseChartOptions.plugins, title: { display: true, text: '时域波形' } }
});

const spectrumOptions = (faultConfig) => ({
  ...baseChartOptions,
  scales: {
    x: { title: { display: true, text: faultConfig.spectrumXAxisLabel || '频率 (Hz)' } },
    y: {
      type: 'linear',
      beginAtZero: true,
      title: { display: true, text: faultConfig.spectrumYAxisLabel || '幅值' },
      grid: { display: true, color: 'rgba(200, 200, 200, 0.3)', lineWidth: 0.5 }
    }
  },
  plugins: { ...baseChartOptions.plugins, title: { display: true, text: '频谱分析' } }
});

const featureTrendOptions = (faultConfig) => ({
  ...baseChartOptions,
  scales: {
    x: { title: { display: true, text: '时间' } },
    y: { title: { display: true, text: faultConfig.featureTrendYAxisLabel || '指标值' }, beginAtZero: true }
  },
  plugins: { ...baseChartOptions.plugins, title: { display: true, text: '特征趋势' } }
});

const historyChartOptions = (faultConfig) => ({
  ...baseChartOptions,
  scales: {
    x: { title: { display: true, text: '时间' } },
    y: { title: { display: true, text: faultConfig.historyYAxisLabel || '故障评分' }, min: 0, max: 1 }
  },
  plugins: { ...baseChartOptions.plugins, title: { display: true, text: '历史故障评分' } }
});

const formatToBeijingTime = (isoString) => {
  if (!isoString) return '无';
  try {
    return new Date(isoString).toLocaleTimeString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      hour12: false,
    });
  } catch (e) {
    return 'Invalid Date';
  }
};

// 格式化最后更新时间
const formatLastUpdate = (typeData) => {
  if (!typeData) return '暂无数据';
  
  // 检查latest中的timestamp
  if (typeData.latest && typeData.latest.timestamp) {
    return formatToBeijingTime(typeData.latest.timestamp);
  }
  
  // 检查history中的最新记录
  if (typeData.history && typeData.history.length > 0) {
    const lastRecord = typeData.history[typeData.history.length - 1];
    if (lastRecord.timestamp) {
      return formatToBeijingTime(lastRecord.timestamp);
    }
  }
  
  return '暂无数据';
};

const formatConnectionDuration = () => {
  const duration = globalWebSocketManager.getConnectionDuration();
  return duration.formatted;
};

const startMonitoring = async () => {
  if (isMonitoring.value) return;
  
  try {
    connectionStatus.value = 'connecting';
    await globalWebSocketManager.connect();
    
    isMonitoring.value = true;
    connectionStatus.value = 'connected';
    
    ElMessage.success('已连接到综合实时监控系统');
    emit('combined-started');
    
    // 启动性能监控
    startPerformanceMonitoring();
    
  } catch (error) {
    connectionStatus.value = 'error';
    ElMessage.error('连接失败: ' + error.message);
    console.error('WebSocket连接错误:', error);
  }
};

const stopMonitoring = () => {
  if (!isMonitoring.value) return;
  
  connectionStatus.value = 'disconnecting';
  globalWebSocketManager.disconnect();
  
  isMonitoring.value = false;
  connectionStatus.value = 'disconnected';
  
  ElMessage.info('已断开综合监控连接');
  emit('combined-stopped');
  
  // 停止性能监控
  stopPerformanceMonitoring();
};

// 重置连接时间
const resetConnectionTime = () => {
  globalWebSocketManager.resetConnectionTime();
  ElMessage.success('连接时间已重置');
};

// 性能监控
let performanceTimer = null;

const startPerformanceMonitoring = () => {
  if (performanceTimer) clearInterval(performanceTimer);
  
  performanceTimer = setInterval(() => {
    try {
      const stats = globalWebSocketManager.getStats();
      const dataManagerReport = globalDataManager.getPerformanceReport();
      
      performanceMetrics.value = {
        messageRate: stats.messagesProcessed || 0,
        memoryUsage: dataManagerReport.currentMemoryUsage || '0 MB',
        updateTime: dataManagerReport.avgUpdateTimeMs || '0 ms'
      };
    } catch (error) {
      console.warn('性能监控更新失败:', error);
    }
  }, 2000); // 降低到每2秒更新一次
};

const stopPerformanceMonitoring = () => {
  if (performanceTimer) {
    clearInterval(performanceTimer);
    performanceTimer = null;
  }
};

// 📦 子组件事件处理方法
const toggleMonitoring = (enabled) => {
  if (enabled) {
    startMonitoring();
  } else {
    stopMonitoring();
  }
};

const refreshPerformanceMetrics = () => {
  try {
    const stats = globalWebSocketManager.getStats();
    const dataManagerReport = globalDataManager.getPerformanceReport();
    
    performanceMetrics.value = {
      messageRate: stats.messagesProcessed || 0,
      memoryUsage: dataManagerReport.currentMemoryUsage || '0 MB',
      updateTime: dataManagerReport.avgUpdateTimeMs || '0 ms'
    };
    
    ElMessage.success('性能指标已刷新');
  } catch (error) {
    console.warn('刷新性能指标失败:', error);
    ElMessage.error('刷新性能指标失败');
  }
};

const resetPerformanceMetrics = () => {
  performanceMetrics.value = {
    messageRate: 0,
    memoryUsage: '0 MB',
    updateTime: '0 ms'
  };
  
  if (globalDataManager.resetPerformanceCounters) {
    globalDataManager.resetPerformanceCounters();
  }
  if (globalWebSocketManager.resetStats) {
    globalWebSocketManager.resetStats();
  }
  
  ElMessage.success('性能统计已重置');
};

// �� 统一实时消息处理器 (合并优化版)

// 🔧 性能优化：防抖机制
const updateQueue = new Map(); // 按故障类型缓存更新
const updateTimer = ref(null);
const UPDATE_DEBOUNCE_DELAY = 500; // 500ms防抖延迟
const MAX_UPDATE_FREQUENCY = 1000; // 最大更新频率：1秒

// 防抖更新函数
const debouncedUpdate = () => {
  if (updateTimer.value) {
    clearTimeout(updateTimer.value);
  }
  
  updateTimer.value = setTimeout(() => {
    // 批量处理所有待更新的数据
    const updates = Array.from(updateQueue.entries());
    updateQueue.clear();
    
    console.log(`[性能优化] 批量更新 ${updates.length} 个故障类型的数据`);
    
    // 批量更新DOM
    updates.forEach(([faultType, dataList]) => {
      // 合并同类型的多条数据，只保留最新的
      const latestData = dataList[dataList.length - 1];
      processImmediateUpdate(faultType, latestData);
    });
    
    updateTimer.value = null;
  }, UPDATE_DEBOUNCE_DELAY);
};

// 立即处理更新（用于批量更新）
const processImmediateUpdate = (faultType, data) => {
  try {
    const faultConfig = faultTypes.value.find(f => f.type === faultType);
    if (!faultConfig) return;
    
    const basicData = {
      timestamp: data.timestamp,
      status: data.status,
      score: data.score,
      features: data.features || {},
      vehicle_id: data.vehicle_id,
      health_score: data.health_score
    };
    
    // 智能数据处理
    if (data.charts && Object.keys(data.charts).length > 0) {
      updateDataWithOptimizedCharts(faultType, basicData, data.charts);
    } else {
      updateDataWithTraditionalProcessing(faultType, data);
    }
    
    // 更新历史记录和警报
    updateHistoryAndAlerts(faultType, basicData);
    
  } catch (error) {
    console.error(`处理 ${faultType} 数据时出错:`, error);
  }
};

const handleRealtimeMessage = (data) => {
  try {
    // 处理多故障混合数据 - 立即处理，不防抖
    if (data.fault_type === 'multi_fault') {
      handleMultiFaultData(data);
      return;
    }
    
    const faultType = data.fault_type;
    const faultConfig = faultTypes.value.find(f => f.type === faultType);
    
    if (!faultConfig) {
      console.warn(`未知故障类型: ${faultType}`);
      return;
    }
    
    // 🚀 性能优化：将数据添加到更新队列而不是立即处理
    if (!updateQueue.has(faultType)) {
      updateQueue.set(faultType, []);
    }
    
    // 添加到队列，限制队列长度避免内存泄漏
    const queue = updateQueue.get(faultType);
    queue.push(data);
    
    // 保持队列合理大小，只保留最新的5条数据
    if (queue.length > 5) {
      queue.splice(0, queue.length - 5);
    }
    
    // 触发防抖更新
    debouncedUpdate();
    
  } catch (error) {
    console.error('处理实时消息时出错:', error);
  }
};

// 🚀 优化数据处理：直接使用预处理图表数据
const updateDataWithOptimizedCharts = (faultType, basicData, charts) => {
  try {
    // 更新基础数据
    if (globalDataManager.updateBasicData) {
      globalDataManager.updateBasicData(faultType, basicData);
    } else {
      globalDataManager.processRealtimeData(faultType, { ...basicData, charts });
    }
    
    // 直接更新图表数据（零处理负担）
    const currentData = globalDataManager.getData(faultType);
    if (currentData) {
      // 时域图表
      if (charts.timeSeries || charts.time_series) {
        currentData.timeSeries = charts.timeSeries || charts.time_series;
      }
      
      // 频域/特征趋势图表
      if (charts.spectrum) {
        if (faultType === 'turn_fault') {
          currentData.spectrum = charts.spectrum;
        } else {
          currentData.featureTrend = charts.spectrum;
        }
      }
      
      // 记录性能指标
      if (globalDataManager.recordPerformanceMetric) {
        globalDataManager.recordPerformanceMetric('optimizedUpdate', Date.now());
      }
    }
  } catch (error) {
    console.error('优化数据处理时出错:', error);
  }
};

// 🔄 传统数据处理：兼容旧格式
const updateDataWithTraditionalProcessing = (faultType, data) => {
  try {
    const processedData = globalDataManager.processRealtimeData(faultType, data);
    if (processedData) {
      updateChartData(faultType, processedData);
    }
  } catch (error) {
    console.error('传统数据处理时出错:', error);
  }
};

// 📊 统一历史记录和警报更新  
const updateHistoryAndAlerts = (faultType, basicData) => {
  try {
    const currentData = globalDataManager.getData(faultType);
    if (!currentData) return;
    
    // 更新历史记录
    if (!currentData.history) currentData.history = [];
    currentData.history.push(basicData);
    
    // 保持历史记录数量限制
    if (currentData.history.length > 10) {
      currentData.history = currentData.history.slice(-10);
    }
    
    // 更新历史趋势图表
    const historyLabels = currentData.history.map(item => formatToBeijingTime(item.timestamp));
    const scores = currentData.history.map(item => item.score || 0);
    
    currentData.historyChart = {
      labels: historyLabels,
      datasets: [{
        label: '故障评分',
        data: scores,
        borderColor: '#409EFF',
        backgroundColor: 'rgba(64, 158, 255, 0.1)',
        borderWidth: 2,
        pointRadius: 1,
        fill: true
      }]
    };
    
    // 🚨 更新关键警报 - 修复健康评分显示
    if (basicData.status === 'fault' || basicData.score > 0.7) {
      const alertExists = criticalAlerts.value.find(alert => 
        alert.vehicle_id === basicData.vehicle_id && alert.fault_type === faultType
      );
      
      if (!alertExists) {
        criticalAlerts.value.unshift({
          alert_id: `${basicData.vehicle_id}-${faultType}-${Date.now()}`,
          vehicle_id: basicData.vehicle_id || `${faultType}_vehicle_${Math.random().toString(36).substr(2, 8)}`,
          alert_type: 'critical_fault',
          fault_type: faultType,
          severity: 'critical',
          health_score: basicData.health_score || (100 - basicData.score * 100), // 🔧 正确的健康评分
          timestamp: basicData.timestamp,
          location: getLocationFromVehicleId(basicData.vehicle_id)
        });
        
        // 限制警报数量
        if (criticalAlerts.value.length > 5) {
          criticalAlerts.value = criticalAlerts.value.slice(0, 5);
        }
      }
    }
    
  } catch (error) {
    console.error('更新历史记录和警报时出错:', error);
  }
};

// 🌍 从车辆ID获取位置信息
const getLocationFromVehicleId = (vehicleId) => {
  if (!vehicleId) return '未知位置';
  if (vehicleId.includes('粤B') || vehicleId.includes('SEAL')) return '深圳福田区';
  if (vehicleId.includes('陕A') && vehicleId.includes('QIN')) return '西安高新区';
  if (vehicleId.includes('陕A') && vehicleId.includes('HAN')) return '西安高新区';
  return '未知位置';
};

// 处理多故障混合数据
const handleMultiFaultData = (data) => {
  const activeFaults = data.active_faults || [];
  const faultSeverities = data.fault_severities || {};
  const faultFeatures = data.fault_features || {};
  
  // 为每个活跃故障类型更新数据
  activeFaults.forEach(faultType => {
    if (faultTypes.value.find(f => f.type === faultType)) {
      const faultSpecificData = {
        ...data,
        fault_type: faultType,
        score: faultSeverities[faultType] || 0,
        features: faultFeatures[faultType] || data.features || {},
        status: faultSeverities[faultType] > 0.7 ? 'fault' : 
                faultSeverities[faultType] > 0.3 ? 'warning' : 'normal'
      };
      
      const processedData = globalDataManager.processRealtimeData(faultType, faultSpecificData);
      if (processedData) {
        updateChartData(faultType, processedData);
      }
    }
  });
  
  // 将不活跃的故障类型设为正常状态
  faultTypes.value.forEach(fault => {
    if (!activeFaults.includes(fault.type)) {
      const normalData = {
        fault_type: fault.type,
        score: 0,
        status: 'normal',
        features: {},
        timestamp: new Date().toISOString()
      };
      globalDataManager.processRealtimeData(fault.type, normalData);
    }
  });
};



// 更新图表数据
const updateChartData = (faultType, processedData) => {
  const faultConfig = faultTypes.value.find(f => f.type === faultType);
  if (!faultConfig || !processedData) return;

  // 更新时域数据
  if (processedData.latest?.time_series) {
    updateTimeSeriesData(processedData.latest, processedData, faultConfig);
  }

  // 更新频谱或特征趋势数据
  if (processedData.latest?.frequency_spectrum && faultType === 'turn_fault') {
    updateSpectrumData(processedData.latest, processedData);
  } else if (processedData.latest?.features) {
    updateFeatureTrendData(processedData.latest, processedData, faultConfig);
  }

  // 更新历史趋势图表
  updateHistoryChart(processedData);
};

// 简化的时域数据更新
const updateTimeSeriesData = (data, typeData, faultConfig) => {
  if (!data.time_series?.time) return;

  const time = data.time_series.time;
  const formattedTime = time.map((t, index) => {
    const pointTime = new Date(Date.now() - (time.length - index) * 1000);
    return formatToBeijingTime(pointTime.toISOString());
  });

  let datasets = [];

  // 根据故障类型构建数据集
  switch (data.fault_type) {
    case 'turn_fault':
    case 'eccentricity':
      datasets = [
        { label: 'A相电流', data: data.time_series.values_a || data.time_series.values_ia || [], borderColor: '#409EFF', borderWidth: 1, pointRadius: 0, fill: false },
        { label: 'B相电流', data: data.time_series.values_b || data.time_series.values_ib || [], borderColor: '#67C23A', borderWidth: 1, pointRadius: 0, fill: false },
        { label: 'C相电流', data: data.time_series.values_c || data.time_series.values_ic || [], borderColor: '#E6A23C', borderWidth: 1, pointRadius: 0, fill: false }
      ].filter(ds => ds.data.length > 0);
      break;
    case 'broken_bar':
      const values_a = data.time_series.values_a || data.time_series.values_ia || [];
      if (values_a.length > 0) {
        datasets = [{ label: 'A相电流', data: values_a, borderColor: '#409EFF', borderWidth: 1, pointRadius: 0, fill: false }];
      }
      break;
    case 'insulation':
      const resistance = data.time_series.values_resistance || [];
      const leakage = data.time_series.values_leakage_current || [];
      datasets = [
        resistance.length > 0 ? { label: '绝缘电阻 (MΩ)', data: resistance, borderColor: '#409EFF', borderWidth: 1, pointRadius: 0, yAxisID: 'y' } : null,
        leakage.length > 0 ? { label: '泄漏电流 (mA)', data: leakage, borderColor: '#67C23A', borderWidth: 1, pointRadius: 0, yAxisID: 'y1' } : null
      ].filter(ds => ds !== null);
      break;
    case 'bearing':
      const vibration = data.time_series.values || data.time_series.values_vibration || [];
      if (vibration.length > 0) {
        datasets = [{ label: '振动信号', data: vibration, borderColor: '#409EFF', borderWidth: 1, pointRadius: 0, fill: false }];
      }
      break;
  }

  if (datasets.length > 0) {
    typeData.timeSeries = { labels: formattedTime, datasets };
  }
};

// 简化的频谱数据更新
const updateSpectrumData = (data, typeData) => {
  if (!data.frequency_spectrum?.frequency) return;
  
  const frequency = data.frequency_spectrum.frequency;
  const amplitude_a = data.frequency_spectrum.amplitude_a || [];
  const amplitude_b = data.frequency_spectrum.amplitude_b || [];
  const amplitude_c = data.frequency_spectrum.amplitude_c || [];

  const datasets = [
    amplitude_a.length > 0 ? { label: 'A相频谱', data: amplitude_a, borderColor: '#409EFF', borderWidth: 1, pointRadius: 0, fill: false } : null,
    amplitude_b.length > 0 ? { label: 'B相频谱', data: amplitude_b, borderColor: '#67C23A', borderWidth: 1, pointRadius: 0, fill: false } : null,
    amplitude_c.length > 0 ? { label: 'C相频谱', data: amplitude_c, borderColor: '#E6A23C', borderWidth: 1, pointRadius: 0, fill: false } : null
  ].filter(ds => ds !== null);
  
  if (datasets.length > 0) {
    typeData.spectrum = { labels: frequency, datasets };
  }
};

// 简化的特征趋势数据更新
const updateFeatureTrendData = (data, typeData, faultConfig) => {
  if (!data.features || !typeData.history?.length) return;
  
  const historyLabels = typeData.history.map(item => formatToBeijingTime(item.timestamp));
  const features = faultConfig.features;
  
  const featureDatasets = features.map((feature, index) => {
    const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399'];
    const values = typeData.history.map(item => {
      const value = item.features?.[feature.key];
      if (value === undefined || value === null) return 0;
      
      // 🔧 修复百分比数据处理逻辑 - 与formatFeature保持一致
      if (feature.unit === '%') {
        let percentValue = value;
        
        // 智能判断数值范围，避免重复乘以100
        if (value <= 1 && value >= 0) {
          percentValue = value * 100;
        } else if (value > 100) {
          // 对于异常大的百分比值，进行修正
          if (value > 1000) {
            percentValue = value / 100;
          } else {
            percentValue = value;
          }
        } else {
          percentValue = value;
        }
        
        // 限制显示范围
        percentValue = Math.max(0, Math.min(percentValue, 9999.99));
        return parseFloat(percentValue.toFixed(2));
      }
      
      return value;
    });
    
    return {
      label: `${feature.name} ${feature.unit ? `(${feature.unit})` : ''}`,
      data: values,
      borderColor: colors[index % colors.length],
      borderWidth: 1.5,
      pointRadius: 1,
      fill: false
    };
  });

  if (featureDatasets.length > 0) {
    typeData.featureTrend = { labels: historyLabels, datasets: featureDatasets };
  }
};

// 简化的历史图表更新
const updateHistoryChart = (typeData) => {
  if (!typeData.history?.length) return;
  
  const historyLabels = typeData.history.map(item => formatToBeijingTime(item.timestamp));
  const scores = typeData.history.map(item => item.score || 0);
  
  typeData.historyChart = {
    labels: historyLabels,
    datasets: [{
      label: '故障评分',
      data: scores,
      borderColor: '#409EFF',
      backgroundColor: 'rgba(64, 158, 255, 0.1)',
      borderWidth: 2,
      pointRadius: 1,
      fill: true
    }]
  };
};

// 从本地存储加载配置
const loadConfigFromLocalStorage = () => {
  try {
    for (const fault of faultTypes.value) {
      const savedConfig = localStorage.getItem(`combined_diagnosis_${fault.type}`);
      if (savedConfig) {
        const config = JSON.parse(savedConfig);
        if (config.isExpanded !== undefined) {
          expandedStates[fault.type] = config.isExpanded;
        }
      }
    }
  } catch (error) {
    console.error('加载配置时出错:', error);
  }
};

// 保存配置到本地存储
const saveConfigToLocalStorage = (faultType, config) => {
  try {
    localStorage.setItem(`combined_diagnosis_${faultType}`, JSON.stringify(config));
  } catch (error) {
    console.error('保存配置时出错:', error);
  }
};

// 格式化评分显示
const formatScore = (typeData) => {
  if (!typeData) return '0.0%';
  
  // 检查latest中的score
  if (typeData.latest && typeof typeData.latest.score === 'number') {
    return (typeData.latest.score * 100).toFixed(1) + '%';
  }
  
  // 检查根级别的score
  if (typeof typeData.score === 'number') {
    return (typeData.score * 100).toFixed(1) + '%';
  }
  
  return '0.0%';
};

// 格式化特征值显示
const formatFeature = (diagnosis, feature) => {
  // 如果没有诊断数据或特征数据，返回默认值
  if (!diagnosis || !diagnosis.features || diagnosis.features[feature.key] === undefined || diagnosis.features[feature.key] === null) {
    // 根据特征类型返回合适的默认值
    if (feature.unit === '%') {
      return '0.00%';
    }
    if (feature.unit === '' || !feature.unit) {
      return '0';
    }
    return `0 ${feature.unit}`;
  }
  
  const value = diagnosis.features[feature.key];
  
  // 处理NaN或无效数值
  if (typeof value === 'number' && !isNaN(value)) {
    if (feature.unit === '%') {
      // 🔧 修复百分比数据处理逻辑
      // 智能判断数值范围，避免重复乘以100
      let percentValue = value;
      
      // 如果数值在合理的小数范围内（0-1），则乘以100转换为百分比
      // 如果数值已经在百分比范围内（大于1），则直接使用
      if (value <= 1 && value >= 0) {
        percentValue = value * 100;
      } else if (value > 100) {
        // 对于异常大的百分比值，可能是重复处理导致的，进行修正
        console.warn(`[百分比修正] 检测到异常百分比值: ${value}，尝试修正`);
        // 如果数值过大，尝试除以100进行修正
        if (value > 1000) {
          percentValue = value / 100;
        } else {
          percentValue = value;
        }
      } else {
        // 负值或其他情况，直接使用原值
        percentValue = value;
      }
      
      // 限制显示范围，避免异常大的数值
      percentValue = Math.max(0, Math.min(percentValue, 9999.99));
      
      return percentValue.toFixed(2) + '%';
    }
    return value.toFixed(2) + (feature.unit ? ` ${feature.unit}` : '');
  }
  
  // 如果value是字符串或其他类型
  if (value !== undefined && value !== null) {
    return value.toString() + (feature.unit ? ` ${feature.unit}` : '');
  }
  
  // 最后的兜底处理
  return feature.unit === '%' ? '0.00%' : `0${feature.unit ? ' ' + feature.unit : ''}`;
};

// 获取状态
const getStatus = (typeData) => {
  if (!typeData) return 'unknown';
  
  // 检查latest中的status
  if (typeData.latest && typeData.latest.status) {
    return typeData.latest.status;
  }
  
  // 检查根级别的status
  if (typeData.status) {
    return typeData.status;
  }
  
  return 'unknown';
};

const getStatusText = (status) => {
  const map = { normal: '正常', warning: '预警', fault: '故障', unknown: '未知' };
  return map[status] || '未知';
};

const getTagType = (status) => {
  const map = { normal: 'success', warning: 'warning', fault: 'danger', unknown: 'info' };
  return map[status] || 'info';
};

const getStatusClass = (status) => {
  if (status === 'fault') return 'status-fault';
  if (status === 'warning') return 'status-warning';
  return 'status-normal';
};

const getConnectionStatusType = (status) => {
  const map = { connected: 'success', connecting: 'info', disconnected: 'danger', disconnecting: 'warning', reconnecting: 'warning', error: 'danger' };
  return map[status] || 'info';
};

const getConnectionStatusText = (status) => {
  const map = { connected: '已连接', connecting: '连接中...', disconnected: '未连接', disconnecting: '断开中...', reconnecting: '重连中...', error: '连接错误' };
  return map[status] || '未知状态';
};

const toggleExpand = (faultType) => {
  expandedStates[faultType] = !expandedStates[faultType];
  saveConfigToLocalStorage(faultType, { isExpanded: expandedStates[faultType] });
};

const viewDetails = (faultType) => {
  // 发送查看详情事件给父组件
  isNavigatingToDetails.value = true; // 标记正在通过查看详情按钮跳转
  emit('view-details', faultType);
};

// ==========================================
// 分布式诊断系统方法
// ==========================================

// 初始化分布式诊断系统
const initializeDistributedSystem = async () => {
  // 首先检查认证状态
  if (!checkAuthenticationStatus()) {
    return;
  }
  
  try {
    distributedStatus.initializing = true;
    distributedStatus.lastError = null;
    
    const result = await api.initializeDistributedDiagnosis();
    
    if (result.status === 'success') {
      distributedStatus.system = 'initialized';
      ElMessage.success(result.message || '分布式诊断系统初始化成功');
    } else {
      throw new Error(result.message || '初始化失败');
    }
  } catch (error) {
    console.error('初始化分布式系统失败:', error);
    distributedStatus.system = 'error';
    distributedStatus.lastError = error.message || error;
    ElMessage.error(`初始化失败: ${error.message || error}`);
  } finally {
    distributedStatus.initializing = false;
  }
};

// 启动分布式诊断系统
const startDistributedSystem = async () => {
  // 首先检查认证状态
  if (!checkAuthenticationStatus()) {
    return;
  }
  
  try {
    distributedStatus.starting = true;
    distributedStatus.lastError = null;
    
    const config = {
      consumers_per_fault: 2,
      enable_aggregation: true,
      enable_monitoring: true
    };
    
    const result = await api.startDistributedDiagnosis(config);
    
    if (result.status === 'success') {
      distributedStatus.system = 'running';
      ElMessage.success(result.message || '分布式诊断系统启动成功');
      
      // 启动性能指标更新
      startMetricsMonitoring();
      
      // 启动警报检查
      startAlertMonitoring();
    } else {
      throw new Error(result.message || '启动失败');
    }
  } catch (error) {
    console.error('启动分布式系统失败:', error);
    distributedStatus.system = 'error';
    distributedStatus.lastError = error.message || error;
    ElMessage.error(`启动失败: ${error.message || error}`);
  } finally {
    distributedStatus.starting = false;
  }
};

// 停止分布式诊断系统
const stopDistributedSystem = async () => {
  try {
    distributedStatus.stopping = true;
    
    // 停止车辆模拟
    if (simulationConfig.running) {
      stopVehicleSimulation();
    }
    
    const result = await api.stopDistributedDiagnosis();
    
    if (result.status === 'success') {
      distributedStatus.system = 'stopped';
      ElMessage.success(result.message || '分布式诊断系统已停止');
      
      // 清理指标
      Object.assign(distributedMetrics, {
        processedMessages: 0,
        averageLatency: 0,
        activeConsumers: 0,
        lastUpdated: null
      });
      
      // 清理警报
      criticalAlerts.value = [];
    } else {
      throw new Error(result.message || '停止失败');
    }
  } catch (error) {
    console.error('停止分布式系统失败:', error);
    ElMessage.error(`停止失败: ${error.message || error}`);
  } finally {
    distributedStatus.stopping = false;
  }
};

// 刷新系统指标
const refreshSystemMetrics = async () => {
  try {
    const result = await api.getSystemPerformance();
    
    if (result.data) {
      Object.assign(distributedMetrics, {
        processedMessages: result.data.processed_messages || 0,
        averageLatency: Math.round(result.data.average_latency_ms || 0),
        activeConsumers: result.data.active_consumers || 0,
        lastUpdated: new Date()
      });
    }
  } catch (error) {
    console.error('获取系统指标失败:', error);
  }
};

// 启动性能指标监控
const startMetricsMonitoring = () => {
  // 每10秒更新一次指标
  const metricsInterval = setInterval(() => {
    if (distributedStatus.system === 'running') {
      refreshSystemMetrics();
    } else {
      clearInterval(metricsInterval);
    }
  }, 10000);
};

// 启动警报监控
const startAlertMonitoring = () => {
  // 每15秒检查一次警报
  const alertsInterval = setInterval(async () => {
    if (distributedStatus.system === 'running') {
      try {
        const result = await api.getCriticalAlerts(5);
        if (result.data && result.data.alerts) {
          criticalAlerts.value = result.data.alerts;
        }
      } catch (error) {
        console.error('获取警报失败:', error);
      }
    } else {
      clearInterval(alertsInterval);
    }
  }, 15000);
};

// 开始车辆模拟 (已禁用 - 使用外部模拟器)
const startVehicleSimulation = async () => {
  ElMessage.info('已禁用内置模拟器，请使用外部 run_simulator_background.py');
  console.log('[前端模拟器] 已禁用，使用外部模拟器数据源');
};

// 停止车辆模拟 (已禁用 - 使用外部模拟器)
const stopVehicleSimulation = () => {
  ElMessage.info('内置模拟器已禁用，请通过外部脚本控制模拟器');
  console.log('[前端模拟器] 停止功能已禁用');
};

// ==========================================
// 车队管理功能 (MultiVehicleSimulator)
// ==========================================

// 初始化车队 (已禁用 - 使用外部模拟器)
const initializeFleet = async () => {
  ElMessage.info('内置车队管理已禁用，请使用外部 run_simulator_background.py');
  console.log('[车队管理] 已禁用，使用外部模拟器');
};

// 启动车队模拟 (已禁用 - 使用外部模拟器)
const startFleetSimulation = async () => {
  ElMessage.info('内置车队管理已禁用，请使用外部 run_simulator_background.py');
  console.log('[车队管理] 启动功能已禁用');
};

// 停止车队模拟 (已禁用 - 使用外部模拟器)
const stopFleetSimulation = async () => {
  ElMessage.info('内置车队管理已禁用，请通过外部脚本控制');
  console.log('[车队管理] 停止功能已禁用');
};

// 刷新车队统计 (已禁用 - 使用外部模拟器)
const refreshFleetStats = async () => {
  console.log('[车队管理] 统计功能已禁用，数据来自外部模拟器');
};

// 开始车队监控 (已禁用 - 使用外部模拟器)
let fleetMonitoringInterval = null;
const startFleetMonitoring = () => {
  console.log('[车队监控] 已禁用，使用外部模拟器数据');
};

// 停止车队监控 (已禁用 - 使用外部模拟器)
const stopFleetMonitoring = () => {
  console.log('[车队监控] 停止功能已禁用');
};

// 获取车队状态文本
const getFleetStatusText = (status) => {
  const statusMap = {
    'stopped': '已停止',
    'initialized': '已初始化', 
    'starting': '启动中',
    'running': '运行中',
    'stopping': '停止中',
    'error': '错误'
  };
  return statusMap[status] || status;
};

// 获取车队状态类型
const getFleetStatusType = (status) => {
  const typeMap = {
    'stopped': 'info',
    'initialized': 'warning',
    'starting': 'primary',
    'running': 'success',
    'stopping': 'warning',
    'error': 'danger'
  };
  return typeMap[status] || 'info';
};

// 格式化运行时间
const formatRuntime = (seconds) => {
  if (!seconds) return '0秒';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}时${minutes}分${secs}秒`;
  } else if (minutes > 0) {
    return `${minutes}分${secs}秒`;
  } else {
    return `${secs}秒`;
  }
};

// ==========================================
// 车队数据可视化方法
// ==========================================







// 获取分布式系统状态类型
const getDistributedStatusType = (status) => {
  const map = {
    stopped: 'info',
    initializing: 'warning', 
    initialized: 'success',
    starting: 'warning',
    running: 'success',
    stopping: 'warning',
    error: 'danger',
    unauthorized: 'warning'
  };
  return map[status] || 'info';
};

// 获取分布式系统状态文本
const getDistributedStatusText = (status) => {
  const map = {
    stopped: '已停止',
    initializing: '初始化中...',
    initialized: '已初始化',
    starting: '启动中...',
    running: '运行中',
    stopping: '停止中...',
    error: '错误',
    unauthorized: '请先登录'
  };
  return map[status] || '未知';
};

// 获取警报类型
const getAlertType = (severity) => {
  if (severity === 'critical') return 'error';
  if (severity === 'warning') return 'warning';
  return 'info';
};

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '无时间';
  try {
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) {
      return '时间格式错误';
    }
    return date.toLocaleTimeString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      hour12: false,
    });
  } catch (e) {
    console.warn('时间格式化错误:', timestamp, e);
    return '时间格式错误';
  }
};

// 📚 警报管理方法
const clearCriticalAlerts = () => {
  criticalAlerts.value = [];
  ElMessage.success('已清空所有关键警报');
};

const dismissAlert = (alertId) => {
  const index = criticalAlerts.value.findIndex(alert => alert.alert_id === alertId);
  if (index !== -1) {
    criticalAlerts.value.splice(index, 1);
    ElMessage.info('已忽略该警报');
  }
};

// 检查用户认证状态
const checkAuthenticationStatus = () => {
  const token = localStorage.getItem('access_token');
  if (!token) {
    ElMessage.warning('请先登录后再使用分布式诊断功能');
    // 禁用分布式诊断功能
    distributedStatus.system = 'unauthorized';
    return false;
  }
  return true;
};

onMounted(() => {
  loadConfigFromLocalStorage();
  
  // 检查用户认证状态
  checkAuthenticationStatus();
  
  // 注册WebSocket消息处理器
  globalWebSocketManager.on('message', handleRealtimeMessage);
  
  // 注册连接状态监听器
  globalWebSocketManager.on('open', () => {
    connectionStatus.value = 'connected';
  });
  
  globalWebSocketManager.on('close', () => {
    connectionStatus.value = 'disconnected';
    isMonitoring.value = false;
  });
  
  globalWebSocketManager.on('error', () => {
    connectionStatus.value = 'error';
  });
  
  globalWebSocketManager.on('reconnect', () => {
    connectionStatus.value = 'reconnecting';
  });
});

onUnmounted(() => {
  try {
    console.log('[CombinedRealTimeDiagnosis] 开始组件清理');
    
    // 停止性能监控
    if (typeof stopPerformanceMonitoring === 'function') {
      stopPerformanceMonitoring();
    }
    
    // 停止车队监控
    if (typeof stopFleetMonitoring === 'function') {
      stopFleetMonitoring();
    }
    
    // 🔧 清理防抖定时器，防止内存泄漏
    if (updateTimer && updateTimer.value) {
      clearTimeout(updateTimer.value);
      updateTimer.value = null;
    }
    
    // 清理更新队列
    if (typeof updateQueue !== 'undefined' && updateQueue && typeof updateQueue.clear === 'function') {
      updateQueue.clear();
    }
    
    // 清理图表实例
    if (faultDistributionChartInstance) {
      try {
        faultDistributionChartInstance.destroy();
      } catch (error) {
        console.warn('[CombinedRealTimeDiagnosis] 清理图表实例时出错:', error);
      }
      faultDistributionChartInstance = null;
    }
    
    // 移除WebSocket事件监听器
    if (globalWebSocketManager && typeof globalWebSocketManager.off === 'function') {
      try {
        globalWebSocketManager.off('message', handleRealtimeMessage);
      } catch (error) {
        console.warn('[CombinedRealTimeDiagnosis] 移除WebSocket监听器时出错:', error);
      }
    }
    
    if (!isNavigatingToDetails.value) {
      // 只有在不是通过查看详情按钮跳转时，才停止监控
      if (typeof stopMonitoring === 'function') {
        try {
          stopMonitoring();
        } catch (error) {
          console.warn('[CombinedRealTimeDiagnosis] 停止监控时出错:', error);
        }
      }
      
      // 清理数据管理器
      if (globalDataManager && typeof globalDataManager.clearAllData === 'function') {
        try {
          globalDataManager.clearAllData();
        } catch (error) {
          console.warn('[CombinedRealTimeDiagnosis] 清理数据管理器时出错:', error);
        }
      }
    } else {
      // 如果是通过查看详情按钮跳转，只断开连接，保留数据
      if (globalWebSocketManager && typeof globalWebSocketManager.disconnect === 'function') {
        try {
          globalWebSocketManager.disconnect();
        } catch (error) {
          console.warn('[CombinedRealTimeDiagnosis] 断开WebSocket连接时出错:', error);
        }
      }
    }
    
    console.log('[CombinedRealTimeDiagnosis] 组件清理完成');
  } catch (error) {
    console.error('[CombinedRealTimeDiagnosis] 组件卸载时出错:', error);
  }
});

</script>

<style scoped>
/* ========================================= */
/* CSS 变量定义 - 统一设计系统 */
/* ========================================= */

.combined-diagnosis-container {
  /* 颜色系统 */
  --color-text-primary: #303133;
  --color-text-regular: #606266;
  --color-text-secondary: #909399;
  --color-text-white: rgba(255, 255, 255, 0.9);
  --color-text-white-light: rgba(255, 255, 255, 0.7);
  
  /* 背景色系统 */
  --bg-white: #fff;
  --bg-glass-light: rgba(255, 255, 255, 0.1);
  --bg-glass-medium: rgba(255, 255, 255, 0.15);
  --bg-glass-heavy: rgba(255, 255, 255, 0.9);
  --bg-light-gray: #f9f9f9;
  --bg-warning: #fdf6ec;
  --bg-danger: #fef0f0;
  
  /* 边框色系统 */
  --border-light: #EBEEF5;
  --border-regular: #e4e7ed;
  --border-glass: rgba(255, 255, 255, 0.2);
  
  /* 状态色系统 */
  --color-primary: #409EFF;
  --color-success: #67C23A;
  --color-warning: #E6A23C;
  --color-danger: #F56C6C;
  
  /* 间距系统 */
  --spacing-xs: 8px;
  --spacing-sm: 12px;
  --spacing-md: 16px;
  --spacing-lg: 20px;
  --spacing-xl: 24px;
  
  /* 圆角系统 */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  
  /* 阴影系统 */
  --shadow-light: 0 2px 12px 0 rgba(0,0,0,0.1);
  --shadow-heavy: 0 6px 24px 0 rgba(0,0,0,0.08);
  
  padding: var(--spacing-lg);
  max-width: 1200px;
  margin: 0 auto;
}
/* ========================================= */
/* 通用样式类 */
/* ========================================= */
.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.flex-center {
  display: flex;
  justify-content: center;
  align-items: center;
}

.flex-start {
  display: flex;
  align-items: center;
}

.flex-column {
  display: flex;
  flex-direction: column;
}

/* ========================================= */
/* 主要组件样式 */
/* ========================================= */
.card {
  background: linear-gradient(135deg, #e3e7e3 0%, #764ba2 100%);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-light);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  color: rgba(0, 0, 0, 0.8);
}

/* 已删除 .monitor-description - 不再需要 */

.monitor-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.monitor-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.monitor-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.9);
}

.control-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.runtime-info {
  display: flex;
  justify-content: center;
  gap: var(--spacing-lg);
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm);
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(10px);
}

.info-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: rgba(0, 0, 0, 0.7);
}

.info-item i {
  color: rgba(0, 0, 0, 0.6);
}

.dashboard-grid {
  display: flex;
  flex-direction: column;
  gap: 25px;
}
.summary-card {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  padding: 25px;
  transition: all 0.3s ease;
  background: linear-gradient(135deg, #e3e7e3 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
  color: rgba(0, 0, 0, 0.8);
}

.summary-card.status-warning {
  background-color: var(--bg-warning);
}

.summary-card.status-fault {
  background-color: var(--bg-danger);
}

.summary-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--shadow-heavy);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.2);
  position: relative;
}

.status-tag {
  font-size: 16px;      /* 增大字体 */
  font-weight: bold;    /* 加粗 */
  padding: 0 15px;      /* 增加水平内边距 */
  height: 32px;         /* 固定高度 */
  line-height: 32px;    /* 垂直居中文本 */
  border-radius: 6px;   /* 轻微圆角 */
  position: absolute;   /* 绝对定位 */
  top: 20px;            /* 距离顶部20px */
  right: 25px;          /* 距离右侧25px */
}
.fault-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.9);
}

.card-body p {
  margin: var(--spacing-xs) 0;
  font-size: 14px;
  color: rgba(0, 0, 0, 0.7);
}

.fault-score {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.7);
}

.fault-score strong {
  font-size: 18px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.9);
  margin-left: var(--spacing-xs);
}
.feature-list {
  display: flex;
  flex-wrap: wrap;
  gap: 15px; /* Spacing between feature items */
  border-top: none; /* Remove border from previous step */
  padding-top: 10px;
  margin-top: 15px;
}
.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  background-color: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-md);
  padding: 15px 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  transition: all 0.2s ease;
  border-bottom: none;
  backdrop-filter: blur(5px);
}

.feature-item:hover {
  background-color: rgba(255, 255, 255, 0.15);
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.feature-name {
  font-size: 15px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.9);
  margin-bottom: var(--spacing-xs);
}

.feature-value {
  font-size: 24px;
  font-weight: bold;
  color: #1E90FF;
  margin-bottom: 5px;
  padding: 0;
  background-color: transparent;
}

.status-warning .feature-value {
  color: #4169E1;
}

.status-fault .feature-value {
  color: #0066CC;
}

.feature-description {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.6);
}
.last-update {
  font-size: 12px !important;
  color: rgba(0, 0, 0, 0.6) !important;
  text-align: right;
  margin-top: var(--spacing-lg) !important;
  padding-top: 10px;
  border-top: 1px solid rgba(0, 0, 0, 0.2);
}

.card-footer {
  margin-top: var(--spacing-lg);
  text-align: right;
}

.no-data-message {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
}

.charts-container {
  margin-top: 25px;
  padding-top: var(--spacing-lg);
  border-top: 1px solid rgba(0, 0, 0, 0.2);
}

.charts-container h4 {
  margin-top: 0;
  margin-bottom: var(--spacing-lg);
  font-size: 18px;
  color: rgba(0, 0, 0, 0.9);
}
.chart-wrapper {
  height: 400px;
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}
.chart-wrapper .el-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}
.expand-toggle-button {
  margin-left: 10px; /* Space between link and button */
}
.details-button {
  position: absolute;
  top: 60px;
  right: 25px;
  font-size: 14px;
}

/* 已删除 .connection-time 和 .performance-metrics - 已整合到 .runtime-info */

/* ========================================= */
/* 分布式诊断控制面板样式 */
/* ========================================= */

.distributed-control-panel {
  margin-bottom: 24px;
  background: linear-gradient(135deg, #e3e7e3 0%, #764ba2 100%);
  color: white;
  border: none;
}

.distributed-control-panel h3 {
  color: white;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-description {
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 20px;
  line-height: 1.6;
}

.distributed-controls {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.system-status {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-label {
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
}

.auth-warning {
  margin-top: 12px;
}

.auth-warning .el-alert {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 193, 7, 0.3);
  backdrop-filter: blur(10px);
}

.auth-warning .el-alert__title {
  color: #FFC107;
  font-weight: 600;
}

.auth-warning .el-alert__description {
  color: rgba(255, 255, 255, 0.9);
}

.performance-info {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  backdrop-filter: blur(10px);
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: rgba(255, 255, 255, 0.95);
  font-size: 13px;
  font-weight: 500;
}

.metric-item i {
  color: #FFD700;
}

.control-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.control-buttons .el-button {
  flex: 1;
  min-width: 120px;
}

/* 车队管理样式 */
.fleet-management {
  background: linear-gradient(135deg, #e3e7e3 0%, #764ba2 100%);
  padding: var(--spacing-lg);
  border-radius: var(--radius-lg);
  backdrop-filter: blur(10px);
  margin-bottom: var(--spacing-lg);
  border: 1px solid rgba(0, 0, 0, 0.2);
  color: rgba(0, 0, 0, 0.8);
}

.fleet-status-card {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  color: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(10px);
}

.fleet-status-card.status-running {
  border-left: 5px solid var(--color-success);
}

.fleet-status-card.status-stopped {
  border-left: 5px solid var(--color-text-secondary);
}

.fleet-status-card.status-error {
  border-left: 5px solid var(--color-danger);
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.status-header h4 {
  margin: 0;
  color: rgba(0, 0, 0, 0.9);
}

.status-indicators {
  display: flex;
  align-items: center;
  gap: 10px;
}

.runtime-info {
  font-size: 14px;
  color: #666;
  background: #f5f5f5;
  padding: 4px 8px;
  border-radius: 4px;
}

.fleet-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 15px;
  margin-bottom: var(--spacing-lg);
}

.fleet-action-buttons {
  display: flex;
  gap: var(--spacing-xs);
  flex-wrap: wrap;
}

.fleet-stats {
  margin-top: var(--spacing-lg);
  padding: 15px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: var(--radius-md);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-bottom: var(--spacing-lg);
}

.stat-item {
  display: flex;
  flex-direction: column;
  text-align: center;
  padding: 10px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  backdrop-filter: blur(10px);
}

.stat-label {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.6);
  margin-bottom: 5px;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: rgba(0, 0, 0, 0.9);
}

.stat-value.success {
  color: var(--color-success);
}

.stat-value.error {
  color: var(--color-danger);
}

.vehicle-details {
  margin-top: 15px;
}

.vehicle-detail-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  color: rgba(0, 0, 0, 0.8);
}

.vehicle-info p {
  margin: 5px 0;
  font-size: 14px;
}

.vehicle-metrics {
  display: flex;
  gap: 15px;
}

.metric span {
  font-size: 14px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  color: rgba(0, 0, 0, 0.8);
  backdrop-filter: blur(5px);
}

.vehicle-simulation {
  background: var(--bg-glass-light);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  backdrop-filter: blur(10px);
}

.simulation-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.input-label {
  color: var(--color-text-white);
  font-size: 14px;
  white-space: nowrap;
}

.critical-alerts {
  background: var(--bg-glass-light);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  backdrop-filter: blur(10px);
}

.no-alerts {
  text-align: center;
  padding: var(--spacing-sm);
}

.alerts-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.alert-item {
  background: var(--bg-glass-heavy);
  border-radius: 6px;
}

.alert-time {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.alert-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.fault-list {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.fault-label {
  font-size: 12px;
  color: var(--color-text-regular);
  font-weight: 500;
}

.fault-tag {
  margin: 0 2px;
}

.action-required {
  margin-top: 4px;
}

/* 响应式设计 - 统一管理 */
@media (max-width: 768px) {
  .distributed-controls {
    gap: var(--spacing-md);
  }
  
  .control-buttons {
    flex-direction: column;
  }
  
  .control-buttons .el-button {
    flex: none;
    width: 100%;
  }
  
  .simulation-controls {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-xs);
  }
  
  .performance-info {
    flex-direction: column;
    gap: var(--spacing-xs);
  }
  
  /* 监控控制面板响应式 */
  .monitor-controls {
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: stretch;
  }
  
  .monitor-header {
    justify-content: space-between;
  }
  
  .control-actions {
    justify-content: center;
  }
  
  .runtime-info {
    flex-wrap: wrap;
    gap: var(--spacing-sm);
    justify-content: space-around;
  }
  
  /* 车队图表响应式 */
  .fleet-charts-grid {
    grid-template-columns: 1fr;
    gap: var(--spacing-sm);
  }
  
  .chart-panel {
    padding: var(--spacing-sm);
  }
  
  .data-flow-metrics {
    grid-template-columns: 1fr;
    gap: var(--spacing-xs);
  }
  
  .consumer-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 6px;
  }
  
  .consumer-name {
    text-align: left;
    min-width: auto;
  }
}

/* ==========================================
   车队数据可视化样式
   ========================================== */

/* 车队图表网格布局 */
.fleet-charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: var(--spacing-lg);
  margin-top: var(--spacing-lg);
}

/* 图表面板样式 */
.chart-panel {
  background: linear-gradient(135deg, #e3e7e3 0%, #764ba2 100%);
  border-radius: var(--radius-lg);
  padding: var(--spacing-md);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
  color: rgba(0, 0, 0, 0.8);
}

.chart-panel:hover {
  background: linear-gradient(135deg, #e8ece8 0%, #8a5db8 100%);
  border-color: rgba(0, 0, 0, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

/* 图表头部样式 */
.chart-header {
  display: flex;
  justify-content: between;
  align-items: center;
  margin-bottom: var(--spacing-sm);
  gap: 10px;
}

.chart-header h4 {
  margin: 0;
  color: var(--color-text-white);
  font-size: 14px;
  font-weight: 600;
  flex: 1;
}

/* 饼图容器 */
.pie-chart-container {
  position: relative;
  width: 100%;
  height: 180px;
}

/* 数据流指标样式 */
.data-flow-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.flow-metric {
  background: rgba(255, 255, 255, 0.08);
  padding: 10px var(--spacing-sm);
  border-radius: var(--radius-md);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-label {
  color: var(--color-text-white-light);
  font-size: 12px;
  font-weight: 500;
}

.metric-value {
  color: rgba(255, 255, 255, 0.95);
  font-size: 13px;
  font-weight: 600;
}

/* 数据流进度条样式 */
.data-flow-bars {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.consumer-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-xs);
}

.consumer-name {
  color: rgba(255, 255, 255, 0.8);
  font-size: 11px;
  font-weight: 500;
  min-width: 80px;
  text-align: right;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--bg-glass-light);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  transition: all 0.3s ease;
}

.progress-fill.healthy {
  background: linear-gradient(90deg, var(--color-success), #85CE61);
}

.progress-fill.warning {
  background: linear-gradient(90deg, var(--color-warning), #EEBE77);
}

.progress-fill.error {
  background: linear-gradient(90deg, var(--color-danger), #F78989);
}

.consumer-health {
  color: var(--color-text-white);
  font-size: 11px;
  font-weight: 600;
  min-width: 35px;
  text-align: center;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .fleet-charts-grid {
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: var(--spacing-md);
  }
}

/* 删除重复的响应式规则 - 已合并到上面 */

/* Element Plus 组件样式覆写 */
.distributed-control-panel .el-divider {
  border-color: var(--border-glass);
}

.distributed-control-panel .el-divider__text {
  color: var(--color-text-white);
  background-color: transparent;
  font-weight: 500;
}
</style> 