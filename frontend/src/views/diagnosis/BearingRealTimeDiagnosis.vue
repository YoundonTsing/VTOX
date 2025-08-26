<template>
  <div class="diagnosis-container">
    <div class="page-header">
      <h2 class="page-title">轴承故障诊断</h2>
      <el-button type="primary" @click="showConfig = !showConfig">
        {{ showConfig ? '隐藏配置' : '阈值配置' }}
      </el-button>
    </div>

    <!-- 阈值配置面板 -->
    <el-collapse-transition>
      <div v-if="showConfig">
        <threshold-config config-type="bearing" @update:thresholds="updateThresholds" />
      </div>
    </el-collapse-transition>

    <!-- 实时监控控制面板 -->
    <div class="card">
      <h3>实时轴承故障监控</h3>
      <p class="monitor-description">
        连接到实时数据流，系统将持续接收电机运行数据并进行轴承故障诊断。
      </p>
      
      <div class="monitor-controls">
        <div class="connection-status">
          <el-tag :type="getConnectionStatusType(connectionStatus)">
            {{ getConnectionStatusText(connectionStatus) }}
          </el-tag>
          <div class="connection-health" v-if="connectionStatus === 'connected'">
            <span class="health-indicator" :class="connectionHealth"></span>
            <span class="health-text">{{ connectionHealth === 'good' ? '连接良好' : '连接不稳定' }}</span>
          </div>
          <span class="monitor-time" v-if="connectionStatus === 'connected'">
            监控时长: {{ monitoringDurationText }}
          </span>
        </div>
        
        <div class="control-actions">
          <el-button type="primary" @click="startMonitoring" :disabled="connectionStatus === 'connected'">
            开始监控
          </el-button>
          <el-button type="danger" @click="stopMonitoring" :disabled="connectionStatus !== 'connected'">
            停止监控
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 实时监控状态面板 -->
    <div v-if="connectionStatus === 'connected'" class="card status-panel">
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="status-card">
            <div class="status-title">当前状态</div>
            <div class="status-value" :class="getStatusClass(latestDiagnosis?.status || 'normal')">
              {{ getStatusText(latestDiagnosis?.status || 'normal') }}
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="status-card">
            <div class="status-title">故障评分</div>
            <div class="status-value">
              {{ latestDiagnosis ? (latestDiagnosis.score * 100).toFixed(1) + '%' : '0.0%' }}
            </div>
            <div class="gauge">
              <div class="gauge-fill" :style="{ width: `${(latestDiagnosis?.score || 0) * 100}%` }"></div>
              <div class="threshold-markers">
                <div class="threshold-marker threshold-marker-warning" :style="{ left: `${thresholds.warning * 100}%` }">
                  <div class="marker-line"></div>
                </div>
                <div class="threshold-marker threshold-marker-fault" :style="{ left: `${thresholds.fault * 100}%` }">
                  <div class="marker-line"></div>
                </div>
              </div>
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="status-card">
            <div class="status-title">故障严重程度</div>
            <div class="status-value">
              {{ latestDiagnosis?.features ? (latestDiagnosis.features.fault_severity * 100).toFixed(1) + '%' : '0.0%' }}
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
    
    <!-- 实时诊断结果 -->
    <div v-if="connectionStatus === 'connected' && latestDiagnosis" class="card">
      <el-tabs type="border-card">
        <!-- 时域波形 -->
        <el-tab-pane label="振动信号波形">
          <div class="chart-container">
            <line-chart
              v-if="timeSeriesData && timeSeriesData.labels && timeSeriesData.labels.length > 0"
              :chart-data="timeSeriesData"
              chart-id="time-series-chart"
              :height="500"
              :options="timeChartOptions"
              :key="`timeseries-${Date.now()}`"
            />
            <div v-else class="no-data-message">
              <el-empty description="暂无波形数据" />
            </div>
          </div>
        </el-tab-pane>
        
        <!-- 频谱分析 -->
        <el-tab-pane label="频谱分析">
          <div class="chart-container">
            <line-chart
              v-if="spectrumData && spectrumData.labels && spectrumData.labels.length > 0"
              :chart-data="spectrumData"
              chart-id="spectrum-chart"
              :height="500"
              :options="spectrumOptions"
              :key="`spectrum-${Date.now()}`"
            />
            <div v-else class="no-data-message">
              <el-empty description="暂无频谱数据" />
            </div>
          </div>
        </el-tab-pane>
        
        <!-- 特征指标 -->
        <el-tab-pane label="特征指标">
          <div class="features-container">
            <el-row :gutter="50">
              <el-col :span="8">
                <div class="feature-card" :class="{ 'feature-warning': isFeatureWarning('bearing_characteristic_frequency') }">
                  <div class="feature-title">轴承特征频率</div>
                  <div class="feature-value">
                    {{ latestDiagnosis.features?.bearing_characteristic_frequency ? 
                      latestDiagnosis.features.bearing_characteristic_frequency.toFixed(2) + ' Hz' : '0.00 Hz' }}
                  </div>
                  <div class="feature-desc">与轴承故障相关的频率</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="feature-card" :class="{ 'feature-warning': isFeatureWarning('crest_factor') }">
                  <div class="feature-title">冲击因子</div>
                  <div class="feature-value">
                    {{ latestDiagnosis.features?.crest_factor ? 
                      latestDiagnosis.features.crest_factor.toFixed(2) : '0.00' }}
                  </div>
                  <div class="feature-desc">振动信号峰值与有效值之比</div>
                </div>
              </el-col>
              <el-col :span="8">
                <div class="feature-card" :class="{ 'feature-warning': isFeatureWarning('kurtosis') }">
                  <div class="feature-title">峭度</div>
                  <div class="feature-value">
                    {{ latestDiagnosis.features?.kurtosis ? 
                      latestDiagnosis.features.kurtosis.toFixed(2) : '0.00' }}
                  </div>
                  <div class="feature-desc">振动信号的峰态值</div>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-tab-pane>
      </el-tabs>
      
      <!-- 诊断结论 -->
      <div class="diagnosis-conclusion">
        <h3>诊断结论与建议</h3>
        <div class="conclusion-content">
          <p>{{ latestDiagnosis.diagnosis_conclusion }}</p>
          <ul v-if="latestDiagnosis.suggestions && latestDiagnosis.suggestions.length > 0">
            <li v-for="(suggestion, index) in latestDiagnosis.suggestions" :key="index">
              {{ suggestion }}
            </li>
          </ul>
        </div>
      </div>
    </div>
    
    <!-- 历史记录 -->
    <div v-if="connectionStatus === 'connected' && diagnosisHistory.length > 0" class="card">
      <h3>故障评分历史</h3>
      <el-tabs>
        <el-tab-pane label="图表">
          <div class="chart-container">
            <line-chart
              v-if="historyChartData"
              :chart-data="historyChartData"
              chart-id="history-chart"
              :height="450"
              :options="historyChartOptions"
              :key="`history-${Date.now()}`"
            />
            <div v-else class="no-data-message">
              <el-empty description="暂无历史数据" />
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="表格">
          <el-table :data="diagnosisHistoryTable" stripe style="width: 100%" height="500" border>
            <el-table-column prop="time" label="时间" width="180" />
            <el-table-column prop="score" label="故障评分" width="120">
              <template #default="scope">
                <el-progress 
                  :percentage="scope.row.score * 100" 
                  :status="getProgressStatus(scope.row.score)"
                  :stroke-width="15"
                />
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="scope">
                <el-tag :type="getTagType(scope.row.status)">
                  {{ getStatusText(scope.row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="bearingCharacteristicFrequency" label="轴承特征频率(Hz)" width="150" />
            <el-table-column prop="crestFactor" label="冲击因子" width="150" />
            <el-table-column prop="kurtosis" label="峭度" width="150" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 历史故障记录 -->
    <div v-if="connectionStatus === 'connected'" class="card">
      <div class="card-header">
        <h3>历史故障记录</h3>
        <el-button type="primary" size="small" @click="exportAllFaultRecords" :disabled="faultHistory.length === 0">
          导出所有记录
        </el-button>
      </div>
      <el-table
        :data="faultHistory"
        stripe
        style="width: 100%"
        height="300"
        border
        :empty-text="'暂无故障记录'"
      >
        <el-table-column prop="time" label="故障时间" width="180" />
        <el-table-column prop="duration" label="持续时间" width="120" />
        <el-table-column prop="severity" label="严重程度" width="120">
          <template #default="scope">
            <el-progress
              :percentage="scope.row.severity * 100"
              :status="getProgressStatus(scope.row.severity)"
              :stroke-width="15"
            />
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getTagType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 拆分特征指标为独立列 -->
        <el-table-column prop="features.bearing_characteristic_frequency" label="轴承特征频率(Hz)" width="140">
          <template #default="scope">
            {{ scope.row.features.bearing_characteristic_frequency.toFixed(2) + ' Hz' }}
          </template>
        </el-table-column>
        <el-table-column prop="features.crest_factor" label="冲击因子" width="140">
          <template #default="scope">
            {{ scope.row.features.crest_factor.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="features.kurtosis" label="峭度" width="140">
          <template #default="scope">
            {{ scope.row.features.kurtosis.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center"> <!-- 添加 align="center" -->
          <template #default="scope">
                                <el-button type="text" size="small" @click="showFaultDetails(scope.row)">详情</el-button>
                    <el-button type="text" size="small" @click="exportFaultRecord(scope.row)">导出</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ThresholdConfig from '@/components/ThresholdConfig.vue'
import LineChart from '@/components/charts/LineChart.vue'

// 添加 autoStart 属性
const props = defineProps({
  autoStart: {
    type: Boolean,
    default: false
  }
});

// 防抖函数 - 用于图表更新优化
const debounce = (func, delay) => {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(null, args), delay);
  };
};

// 消息提示防抖 - 避免频繁弹出相同类型的消息
const messageDebounceMap = new Map();
const debouncedMessage = (message, type, duration) => {
  const key = `${type}-${message}`;
  if (messageDebounceMap.has(key)) {
    clearTimeout(messageDebounceMap.get(key));
  }
  
  const timeoutId = setTimeout(() => {
    ElMessage({
      message,
      type,
      duration
    });
    messageDebounceMap.delete(key);
  }, 2000); // 2秒内相同消息只显示一次
  
  messageDebounceMap.set(key, timeoutId);
};

// 响应式状态
const showConfig = ref(false)
const connectionStatus = ref('disconnected') // 'disconnected', 'connecting', 'connected', 'disconnecting', 'reconnecting', 'error'
const connectionHealth = ref('unknown') // 'good', 'poor', 'unknown'
const monitoringStartTime = ref(null)
const monitoringDurationText = ref('0秒') // 添加监控时长文本
const wsConnection = ref(null)
const latestDiagnosis = ref(null)
const diagnosisHistory = ref([])
const timeSeriesData = ref(null)
const spectrumData = ref(null)
const durationUpdateTimer = ref(null) // 添加定时器引用
const faultHistory = ref([]) // 添加故障历史记录

// 阈值配置
const thresholds = reactive({
  warning: 0.3,  // 预警阈值
  fault: 0.6     // 故障阈值
})

// 图表配置
const timeChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      title: {
        display: true,
        text: '时间 (s)',
        padding: { top: 10 }
      },
      grid: {
        display: true,
        color: 'rgba(200, 200, 200, 0.3)',
        lineWidth: 0.5
      },
      ticks: {
        callback: function(value) {
          // 将X轴坐标格式化为保留两位小数
          return Number(value).toFixed(2);
        },
        padding: 8,  // 增加标签与轴线的距离
        font: {
          size: 11   // 稍微减小字体大小
        }
      },
      afterFit: function(scaleInstance) {
        // 增加X轴高度，为标签留出更多空间
        scaleInstance.height = scaleInstance.height + 20;
      }
    },
    y: {
      title: {
        display: true,
        text: '幅值'
      },
      grid: {
        display: true,
        color: 'rgba(200, 200, 200, 0.3)',
        lineWidth: 0.5
      }
    }
  },
  plugins: {
    title: {
      display: true,
      text: '振动信号波形'
    },
    legend: {
      position: 'top'
    },
    tooltip: {
      callbacks: {
        title: function(tooltipItems) {
          // 在提示框中也格式化时间值
          return '时间: ' + Number(tooltipItems[0].label).toFixed(2) + ' s';
        }
      }
    }
  },
  animation: false // 禁用动画以提高性能
}

const spectrumOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      title: {
        display: true,
        text: '频率 (Hz)',
        padding: { top: 10 }
      },
      grid: {
        display: true,
        color: 'rgba(200, 200, 200, 0.3)',
        lineWidth: 0.5
      },
      ticks: {
        maxTicksLimit: 10, 
        padding: 8,  // 增加标签与轴线的距离
        font: {
          size: 11   // 稍微减小字体大小
        }
      },
      min: 0,   // 设置X轴最小值
      max: 2000, // 设置X轴最大值
      afterFit: function(scaleInstance) {
        // 增加X轴高度，为标签留出更多空间
        scaleInstance.height = scaleInstance.height + 20;
      }
    },
    y: {
      title: {
        display: true,
        text: '幅值'
      },
      // 使用线性坐标轴代替对数坐标轴
      type: 'linear',
      beginAtZero: true,
      grid: {
        display: true,
        color: 'rgba(200, 200, 200, 0.3)',
        lineWidth: 0.5
      }
    }
  },
  plugins: {
    title: {
      display: true,
      text: '频谱分析'
    },
    legend: {
      position: 'top'
    },
    tooltip: {
      mode: 'index',
      intersect: false
    }
  },
  elements: {
    line: {
      tension: 0.2 // 添加一些平滑度
    },
    point: {
      radius: 0
    }
  },
  animation: false
}

const historyChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      title: {
        display: true,
        text: '时间',
        padding: { top: 10 }
      },
      grid: {
        display: true,
        color: 'rgba(200, 200, 200, 0.3)',
        lineWidth: 0.5
      },
      ticks: {
        maxRotation: 45,
        minRotation: 45,
        autoSkip: true,
        maxTicksLimit: 20,
        padding: 8,  // 增加标签与轴线的距离
        font: {
          size: 11   // 稍微减小字体大小
        }
      },
      afterFit: function(scaleInstance) {
        // 增加X轴高度，为标签留出更多空间
        scaleInstance.height = scaleInstance.height + 20;
      }
    },
    y: {
      title: {
        display: true,
        text: '故障评分'
      },
      min: 0,
      max: 1,
      grid: {
        display: true,
        color: 'rgba(200, 200, 200, 0.3)',
        lineWidth: 0.5
      }
    }
  },
  plugins: {
    title: {
      display: true,
      text: '故障评分历史'
    },
    tooltip: {
      mode: 'index',
      intersect: false
    },
    legend: {
      position: 'top'
    }
  },
  elements: {
    line: {
      tension: 0.2 // 添加一些平滑度
    },
    point: {
      radius: 2,
      hoverRadius: 5
    }
  },
  animation: false
}

// 更新监控时长的函数
const updateMonitoringDuration = () => {
  if (!monitoringStartTime.value) {
    monitoringDurationText.value = '0秒'
    return
  }
  
  const currentTime = Date.now()
  const seconds = Math.floor((currentTime - monitoringStartTime.value) / 1000)
  
  if (seconds < 60) {
    monitoringDurationText.value = `${seconds}秒`
    return
  }
  
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  
  if (minutes < 60) {
    monitoringDurationText.value = `${minutes}分${remainingSeconds}秒`
    return
  }
  
  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  monitoringDurationText.value = `${hours}时${remainingMinutes}分${remainingSeconds}秒`
}

// 历史图表数据 - 使用防抖优化更新频率
const historyChartData = ref(null)

// 防抖版本的历史图表更新函数
const debouncedUpdateHistoryChart = debounce(() => {
  if (diagnosisHistory.value.length === 0) {
    historyChartData.value = null
    return
  }
  
  // 按时间排序，确保最新的数据在最后
  const sortedHistory = [...diagnosisHistory.value].sort((a, b) => {
    return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  })
  
  // 格式化时间标签
  const labels = sortedHistory.map(item => {
    const date = new Date(item.timestamp)
    return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`
  })
  
  // 提取故障评分
  const scores = sortedHistory.map(item => item.score)
  
  
  historyChartData.value = {
    labels,
    datasets: [
      {
        label: '故障评分',
        data: scores,
        borderColor: '#409EFF',
        backgroundColor: 'rgba(64, 158, 255, 0.1)',
        borderWidth: 2,
        pointRadius: 2,
        fill: true,
        yAxisID: 'y'
      },
      {
        label: '预警阈值',
        data: Array(labels.length).fill(thresholds.warning),
        borderColor: '#E6A23C',
        borderWidth: 1,
        borderDash: [5, 5],
        pointRadius: 0,
        fill: false,
        yAxisID: 'y'
      },
      {
        label: '故障阈值',
        data: Array(labels.length).fill(thresholds.fault),
        borderColor: '#F56C6C',
        borderWidth: 1,
        borderDash: [5, 5],
        pointRadius: 0,
        fill: false,
        yAxisID: 'y'
      }
    ]
  }
}, 100) // 100ms防抖，与综合监控页面保持一致

// 历史数据表格
const diagnosisHistoryTable = computed(() => {
  return diagnosisHistory.value.map(item => ({
    time: new Date(item.timestamp).toLocaleTimeString(),
    score: item.score,
    status: item.status,
    bearingCharacteristicFrequency: item.features?.bearing_characteristic_frequency ? item.features.bearing_characteristic_frequency.toFixed(2) : '0.00',
    crestFactor: item.features?.crest_factor ? item.features.crest_factor.toFixed(2) : '0.00',
    kurtosis: item.features?.kurtosis ? item.features.kurtosis.toFixed(2) : '0.00'
  }))
})

// 获取进度条状态
const getProgressStatus = (score) => {
  if (score > thresholds.fault) return 'exception'
  if (score > thresholds.warning) return 'warning'
  return 'success'
}

// 获取标签类型
const getTagType = (status) => {
  switch (status) {
    case 'normal': return 'success'
    case 'warning': return 'warning'
    case 'fault': return 'danger'
    default: return 'info'
  }
}

// 开始监控
const startMonitoring = () => {
  if (connectionStatus.value === 'connected') return
  
  // 如果是第一次连接或之前断开连接超过一定时间，才清空历史数据
  const now = Date.now()
  const reconnectThreshold = 10000; // 10秒
  
  if (!monitoringStartTime.value || (now - monitoringStartTime.value > reconnectThreshold)) {
    // 清空历史数据
    diagnosisHistory.value = []
    latestDiagnosis.value = null
    timeSeriesData.value = null
    spectrumData.value = null
  }
  
  // 连接到WebSocket
  connectWebSocket()
}

// 连接WebSocket
const connectWebSocket = () => {
  const wsUrl = 'ws://localhost:8000/ws/frontend'
  
  // 更新状态为连接中
  connectionStatus.value = 'connecting'
  
  wsConnection.value = new WebSocket(wsUrl)
  
  // 添加历史数据存储和恢复功能
  const saveHistoryToLocalStorage = () => {
    if (diagnosisHistory.value.length > 0) {
      try {
        // 只保存最近的20条记录，进一步减少数据量
        const historyToSave = diagnosisHistory.value.slice(-20);
        localStorage.setItem('bearingDiagnosisHistory', JSON.stringify(historyToSave));
        localStorage.setItem('bearingHistoryTimestamp', Date.now().toString());
      } catch (error) {
        console.error('保存历史数据失败:', error);
      }
    }
  }

  const loadHistoryFromLocalStorage = () => {
    try {
      const savedHistory = localStorage.getItem('bearingDiagnosisHistory');
      const historyTimestamp = localStorage.getItem('bearingHistoryTimestamp');
      
      if (savedHistory && historyTimestamp) {
        const now = Date.now();
        const timestamp = parseInt(historyTimestamp);
        const age = now - timestamp;
        
        // 只恢复30分钟内的数据
        if (age < 30 * 60 * 1000) {
          const parsedHistory = JSON.parse(savedHistory);
          if (Array.isArray(parsedHistory) && parsedHistory.length > 0) {
            diagnosisHistory.value = parsedHistory;
            latestDiagnosis.value = parsedHistory[parsedHistory.length - 1];
            
            // 恢复故障记录
            parsedHistory.forEach(record => {
              if (record.status === 'fault' || record.status === 'warning') {
                recordFault(record);
              }
            });
            
            ElMessage.info(`已恢复${parsedHistory.length}条历史诊断记录`);
            return true;
          }
        } else {
          console.log('历史数据过期，不进行恢复');
          // 清除过期数据
          localStorage.removeItem('bearingDiagnosisHistory');
          localStorage.removeItem('bearingHistoryTimestamp');
        }
      }
    } catch (error) {
      console.error('加载历史数据失败:', error);
    }
    return false;
  }

  wsConnection.value.onopen = () => {
    connectionStatus.value = 'connected';
    monitoringStartTime.value = Date.now();
    monitoringDurationText.value = '0秒';
    
    // 启动定时器，每秒更新一次监控时长显示
    if (durationUpdateTimer.value) {
      clearInterval(durationUpdateTimer.value);
    }
    durationUpdateTimer.value = setInterval(updateMonitoringDuration, 1000);
    
    // 启动心跳检测
    startHeartbeat();
    
    // 尝试恢复历史数据
    const historyRestored = loadHistoryFromLocalStorage();
    
    ElMessage.success(`已连接到实时监控系统${historyRestored ? '并恢复历史数据' : ''}`);
  }
  
  wsConnection.value.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      
      // 更新最后一次心跳响应时间
      lastHeartbeatResponse.value = Date.now()
      
      // 处理心跳响应
      if (data.type === 'heartbeat_response') {
        // console.log('收到心跳响应:', data) // 优化：移除频繁日志
        return
      }
      
      // 检查是否为轴承故障诊断结果
      if (data.fault_type === 'bearing') {
        
        // 更新最新诊断结果
        latestDiagnosis.value = data
        
        // 添加到历史记录
        diagnosisHistory.value.push(data)
        if (diagnosisHistory.value.length > 20) { // 优化：从50减少到20条
          diagnosisHistory.value.shift()
        }
        
        // 更新历史图表 - 使用防抖优化
        debouncedUpdateHistoryChart()
        
        // 检查并记录故障
        recordFault(data)
        
        // 更新时域图表数据
        if (data.time_series) {
          try {
            // 确保数据存在且格式正确
            const time = data.time_series.time || [];
            const values = data.time_series.values || [];
            
            // 检查数据是否有效
            if (time.length > 0 && values.length === time.length) {
              
              // 格式化时间数据，保留两位小数
              const formattedTime = time.map(t => Number(t).toFixed(2));
              
              timeSeriesData.value = {
                labels: formattedTime,
                datasets: [
                  {
                    label: '振动信号',
                    data: values,
                    borderColor: '#409EFF',
                    backgroundColor: 'rgba(64, 158, 255, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0
                  }
                ]
              }
              
              // console.log('时域数据已更新，数据点数量:', formattedTime.length); // 优化：移除频繁日志
            } else {
              console.warn('时域数据格式不正确或长度不匹配');
              timeSeriesData.value = null;
            }
          } catch (error) {
            console.error('处理时域数据时出错:', error);
            timeSeriesData.value = null;
          }
        }
        
        // 更新频谱图表数据
        if (data.frequency_spectrum) {
          try {
            // 确保数据存在且格式正确
            const frequency = data.frequency_spectrum.frequency || [];
            const amplitude = data.frequency_spectrum.amplitude || [];
            
            // 检查数据是否有效
            if (frequency.length > 0 && amplitude.length === frequency.length) {
              
              // 限制数据点数量，避免图表过于密集
              const maxPoints = 50; // 与综合监控同步优化：从100减少到50点
              const step = frequency.length > maxPoints ? Math.floor(frequency.length / maxPoints) : 1;
              
              const filteredFrequency = [];
              const filteredAmplitude = [];
              
              for (let i = 0; i < frequency.length; i += step) {
                filteredFrequency.push(frequency[i]);
                filteredAmplitude.push(amplitude[i]);
              }
              
              spectrumData.value = {
                labels: filteredFrequency,
                datasets: [
                  {
                    label: '幅值',
                    data: filteredAmplitude,
                    borderColor: '#409EFF',
                    backgroundColor: 'rgba(64, 158, 255, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: false
                  }
                ]
              };
              
              // console.log('频谱数据已更新，数据点数量:', filteredFrequency.length); // 优化：移除频繁日志
            } else {
              console.warn('频谱数据格式不正确或长度不匹配');
              spectrumData.value = null;
            }
          } catch (error) {
            console.error('处理频谱数据时出错:', error);
            spectrumData.value = null;
          }
        }
        
        // 检查故障状态并提醒 - 使用防抖优化
        if (data.status === 'fault') {
          debouncedMessage('警告：检测到轴承故障！', 'error', 5000);
        } else if (data.status === 'warning') {
          debouncedMessage('注意：检测到轴承故障预警信号', 'warning', 3000);
        }
      }
    } catch (error) {
      console.error('处理WebSocket消息时出错:', error)
    }
  }
  
  wsConnection.value.onclose = (event) => {
    console.log('WebSocket连接关闭:', event.code, event.reason)
    
    // 保存历史数据到本地存储
    saveHistoryToLocalStorage();
    
    // 清除定时器
    if (durationUpdateTimer.value) {
      clearInterval(durationUpdateTimer.value)
      durationUpdateTimer.value = null
    }
    
    // 如果不是用户主动关闭的连接，尝试重连
    if (connectionStatus.value !== 'disconnecting') {
      connectionStatus.value = 'reconnecting'
      console.log('尝试重新连接WebSocket...')
      
      // 延迟重连，避免立即重连导致的连接风暴
      setTimeout(() => {
        if (connectionStatus.value === 'reconnecting') {
          connectWebSocket()
        }
      }, 2000)
    } else {
      connectionStatus.value = 'disconnected'
      monitoringDurationText.value = '0秒'
      ElMessage.info('实时监控连接已关闭')
    }
  }
  
  wsConnection.value.onerror = (error) => {
    console.error('WebSocket连接错误:', error)
    connectionStatus.value = 'error'
    
    // 清除定时器
    if (durationUpdateTimer.value) {
      clearInterval(durationUpdateTimer.value)
      durationUpdateTimer.value = null
    }
    
    ElMessage.error('连接实时监控系统失败')
  }
}

// 心跳检测
const heartbeatInterval = ref(null)
const lastHeartbeatResponse = ref(Date.now())
const heartbeatTimeout = 10000 // 10秒无响应判定为连接异常

// 启动心跳检测
const startHeartbeat = () => {
  if (heartbeatInterval.value) {
    clearInterval(heartbeatInterval.value)
  }
  
  // 发送心跳并检查连接状态
  heartbeatInterval.value = setInterval(() => {
    if (wsConnection.value && wsConnection.value.readyState === WebSocket.OPEN) {
      try {
        // 发送心跳消息
        wsConnection.value.send(JSON.stringify({ type: 'heartbeat', timestamp: Date.now() }))
        
        // 检查上次心跳响应时间，如果超过超时时间，认为连接异常
        const now = Date.now()
        if (now - lastHeartbeatResponse.value > heartbeatTimeout) {
          console.warn('心跳检测超时，可能连接异常')
          connectionHealth.value = 'poor'
        } else {
          connectionHealth.value = 'good'
        }
      } catch (error) {
        console.error('发送心跳消息失败:', error)
        connectionHealth.value = 'poor'
      }
    }
  }, 5000) // 每5秒发送一次心跳
}

// 停止心跳检测
const stopHeartbeat = () => {
  if (heartbeatInterval.value) {
    clearInterval(heartbeatInterval.value)
    heartbeatInterval.value = null
  }
}

// 停止监控
const stopMonitoring = () => {
  if (wsConnection.value) {
    connectionStatus.value = 'disconnecting'
    wsConnection.value.close()
    wsConnection.value = null
  }
  
  // 清除定时器
  if (durationUpdateTimer.value) {
    clearInterval(durationUpdateTimer.value)
    durationUpdateTimer.value = null
  }
  
  // 停止心跳检测
  stopHeartbeat()
  
  connectionStatus.value = 'disconnected'
  monitoringDurationText.value = '0秒'
  // 保留monitoringStartTime以便判断重连时间间隔
}

// 获取状态类名
const getStatusClass = (status) => {
  switch (status) {
    case 'normal': return 'status-normal'
    case 'warning': return 'status-warning'
    case 'fault': return 'status-fault'
    default: return ''
  }
}

// 获取状态文本
const getStatusText = (status) => {
  switch (status) {
    case 'normal': return '正常'
    case 'warning': return '预警'
    case 'fault': return '故障'
    default: return '未知'
  }
}

// 判断特征是否达到预警值
const isFeatureWarning = (featureName) => {
  if (!latestDiagnosis.value || !latestDiagnosis.value.features) return false
  
  const value = latestDiagnosis.value.features[featureName]
  if (featureName === 'bearing_characteristic_frequency') return value > 1000 // 假设大于1000Hz为预警
  if (featureName === 'crest_factor') return value > 3.0 // 假设大于3.0为预警
  if (featureName === 'kurtosis') return value > 3.5 // 假设大于3.5为预警
  
  return false
}

// 更新阈值
const updateThresholds = (newThresholds) => {
  Object.assign(thresholds, newThresholds)
}

// 显示故障详情
const showFaultDetails = (fault) => {
  ElMessageBox.alert(
    `<div class="fault-details">
      <p><strong>故障时间:</strong> ${fault.time}</p>
      <p><strong>持续时间:</strong> ${fault.duration}</p>
      <p><strong>严重程度:</strong> ${(fault.severity * 100).toFixed(2)}%</p>
      <p><strong>状态:</strong> ${getStatusText(fault.status)}</p>
      <p><strong>特征指标:</strong></p>
      <ul>
        <li>轴承特征频率: ${fault.features.bearing_characteristic_frequency.toFixed(2)} Hz</li>
        <li>冲击因子: ${fault.features.crest_factor.toFixed(2)}</li>
        <li>峭度: ${fault.features.kurtosis.toFixed(2)}</li>
      </ul>
      <p><strong>诊断结论:</strong> ${fault.diagnosis_conclusion}</p>
      <p><strong>建议措施:</strong></r
      <ul>
        ${fault.suggestions.map(s => `<li>${s}</li>`).join('')}
      </ul>
    </div>`,
    '故障详情',
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: '确定'
    }
  )
}

// 导出故障记录
const exportFaultRecord = (fault) => {
  // 创建CSV内容
  const csvContent = [
    '故障记录导出',
    `故障时间,${fault.time}`,
    `持续时间,${fault.duration}`,
    `严重程度,${(fault.severity * 100).toFixed(2)}%`,
    `状态,${getStatusText(fault.status)}`,
    '',
    '特征指标,数值',
    `轴承特征频率,${fault.features.bearing_characteristic_frequency.toFixed(2)} Hz`,
    `冲击因子,${fault.features.crest_factor.toFixed(2)}`,
    `峭度,${fault.features.kurtosis.toFixed(2)}`,
    '',
    '诊断结论',
    fault.diagnosis_conclusion,
    '',
    '建议措施',
    ...fault.suggestions
  ].join('\n')
  
  // 创建Blob对象
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  
  // 创建下载链接
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `故障记录_轴承故障_${fault.time.replace(/[: ]/g, '_')}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  ElMessage.success('故障记录已导出')
}

// 记录故障
const recordFault = (diagnosis) => {
  // 只记录故障和预警状态
  if (diagnosis.status !== 'fault' && diagnosis.status !== 'warning') return
  
  // 检查是否已经有相同时间的故障记录
  const existingIndex = faultHistory.value.findIndex(f => 
    f.time === new Date(diagnosis.timestamp).toLocaleString()
  )
  
  if (existingIndex >= 0) {
    // 更新现有记录
    const existing = faultHistory.value[existingIndex]
    // 更新持续时间
    const endTime = new Date()
    const startTime = new Date(existing.rawTimestamp)
    const durationMs = endTime - startTime
    const durationSec = Math.floor(durationMs / 1000)
    let durationText = ''
    
    if (durationSec < 60) {
      durationText = `${durationSec}秒`
    } else {
      const minutes = Math.floor(durationSec / 60)
      const seconds = durationSec % 60
      durationText = `${minutes}分${seconds}秒`
    }
    
    // 更新记录
    faultHistory.value[existingIndex] = {
      ...existing,
      duration: durationText,
      severity: Math.max(existing.severity, diagnosis.features.fault_severity),
      features: diagnosis.features,
      status: diagnosis.status
    }
  } else {
    // 添加新记录
    faultHistory.value.unshift({
      time: new Date(diagnosis.timestamp).toLocaleString(),
      rawTimestamp: diagnosis.timestamp,
      duration: '刚刚开始',
      severity: diagnosis.features.fault_severity,
      status: diagnosis.status,
      features: diagnosis.features,
      diagnosis_conclusion: diagnosis.diagnosis_conclusion,
      suggestions: diagnosis.suggestions
    })
    
    // 限制记录数量 - 进一步优化
    if (faultHistory.value.length > 20) { // 优化：从50减少到20条
      faultHistory.value = faultHistory.value.slice(0, 20)
    }
  }
}

// 导出所有故障记录
const exportAllFaultRecords = () => {
  if (faultHistory.value.length === 0) {
    ElMessage.info('没有历史故障记录可以导出。')
    return
  }

  const headers = [
    '故障时间',
    '持续时间',
    '严重程度',
    '状态',
    '轴承特征频率(Hz)',
    '冲击因子',
    '峭度'
  ].join(',')

  const rows = faultHistory.value.map(record => {
    const time = `"${record.time}"` // 用双引号包裹时间，防止逗号问题
    const duration = `"${record.duration}"`
    const severity = (record.severity * 100).toFixed(2) + '%'
    const status = getStatusText(record.status)
    const bearingCharacteristicFrequency = record.features.bearing_characteristic_frequency.toFixed(2)
    const crestFactor = record.features.crest_factor.toFixed(2)
    const kurtosis = record.features.kurtosis.toFixed(2)

    return [
      time,
      duration,
      severity,
      status,
      bearingCharacteristicFrequency,
      crestFactor,
      kurtosis
    ].join(',')
  })

  const csvContent = [headers, ...rows].join('\n')

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `所有故障记录_轴承故障_${new Date().toISOString().slice(0, 10)}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  ElMessage.success('所有故障记录已导出成功！')
}

// 组件卸载时关闭连接
onUnmounted(() => {
  stopMonitoring()
  saveHistoryToLocalStorage()
  
  // 清理消息防抖定时器
  messageDebounceMap.forEach(timeoutId => {
    clearTimeout(timeoutId);
  });
  messageDebounceMap.clear();
})

// 组件挂载时加载阈值配置
onMounted(() => {
  // 从localStorage加载阈值配置
  const savedThresholds = localStorage.getItem('bearingThresholds')
  if (savedThresholds) {
    try {
      const parsed = JSON.parse(savedThresholds)
      Object.assign(thresholds, parsed)
    } catch (e) {
      console.error('解析保存的阈值配置失败:', e)
    }
  }
  
  // 初始化监控时长
  updateMonitoringDuration()
  
  // 在组件挂载时，如果 autoStart 为 true，则自动开始监控
  if (props.autoStart) {
    startMonitoring();
  }
})

// 监听 autoStart 属性变化，如果变为 true 且当前未连接，则开始监控
watch(() => props.autoStart, (newValue) => {
  if (newValue && connectionStatus.value !== 'connected') {
    startMonitoring();
  }
});

// 获取连接状态标签类型
const getConnectionStatusType = (status) => {
  switch (status) {
    case 'connected': return 'success'
    case 'connecting': return 'info'
    case 'disconnected': return 'danger'
    case 'disconnecting': return 'warning'
    case 'reconnecting': return 'warning'
    case 'error': return 'danger'
    default: return 'info'
  }
}

// 获取连接状态文本
const getConnectionStatusText = (status) => {
  switch (status) {
    case 'connected': return '已连接'
    case 'connecting': return '连接中...'
    case 'disconnected': return '未连接'
    case 'disconnecting': return '断开中...'
    case 'reconnecting': return '重新连接中...'
    case 'error': return '连接错误'
    default: return '未知状态'
  }
}
</script>

<style scoped>
.diagnosis-container {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  color: #303133;
  margin: 0;
}

.card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 20px;
  width: 100%;
}

.monitor-description {
  margin: 15px 0;
  color: #606266;
}

.monitor-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 15px;
}

.monitor-time {
  font-family: monospace;
  font-size: 14px;
  color: #606266;
}

.status-panel {
  margin-top: 20px;
}

.status-card {
  text-align: center;
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #EBEEF5;
  height: 100%;
}

.status-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.status-value {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 10px;
}

.status-normal {
  color: #67C23A;
}

.status-warning {
  color: #E6A23C;
}

.status-fault {
  color: #F56C6C;
}

.gauge {
  height: 10px;
  background-color: #f5f7fa;
  border-radius: 5px;
  position: relative;
  overflow: hidden;
}

.gauge-fill {
  height: 100%;
  background: linear-gradient(to right, #67C23A, #E6A23C, #F56C6C);
  border-radius: 5px;
  transition: width 0.5s;
}

.threshold-markers {
  position: relative;
  height: 20px;
}

.threshold-marker {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
}

.marker-line {
  width: 2px;
  height: 10px;
  background-color: #303133;
}

.threshold-marker-warning .marker-line {
  background-color: #E6A23C;
}

.threshold-marker-fault .marker-line {
  background-color: #F56C6C;
}

.features-container {
  margin: 20px 0;
}

.feature-card {
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #EBEEF5;
  text-align: center;
  transition: all 0.3s;
  height: 100%;
}

.feature-warning {
  border-color: #E6A23C;
  background-color: rgba(230, 162, 60, 0.1);
}

.feature-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 10px;
}

.feature-value {
  font-size: 24px;
  color: #409EFF;
  margin-bottom: 10px;
}

.feature-warning .feature-value {
  color: #E6A23C;
}

.feature-desc {
  font-size: 12px;
  color: #909399;
}

.diagnosis-conclusion {
  margin-top: 20px;
}

.conclusion-content {
  padding: 15px;
  border-left: 4px solid #409EFF;
  background-color: #f5f7fa;
  border-radius: 0 4px 4px 0;
}

.chart-container {
  position: relative;
  height: 450px; /* 设置图表容器高度 */
}

.no-data-message {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  text-align: center;
}

/* 故障记录样式 */
.feature-indicators {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.feature-indicator {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 4px;
  background-color: #f5f7fa;
  font-size: 12px;
}

.feature-indicator.warning {
  background-color: rgba(230, 162, 60, 0.1);
  color: #E6A23C;
  border: 1px solid rgba(230, 162, 60, 0.2);
}

.feature-indicator i {
  margin-right: 4px;
  color: #E6A23C;
}

.fault-details {
  text-align: left;
  line-height: 1.6;
}

.fault-details p {
  margin: 8px 0;
}

.fault-details ul {
  margin: 8px 0;
  padding-left: 20px;
}

.fault-details li {
  margin: 4px 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.connection-health {
  display: flex;
  align-items: center;
  margin-left: 10px;
}

.health-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 5px;
}

.health-indicator.good {
  background-color: #67C23A;
  box-shadow: 0 0 5px #67C23A;
}

.health-indicator.poor {
  background-color: #E6A23C;
  box-shadow: 0 0 5px #E6A23C;
}

.health-indicator.unknown {
  background-color: #909399;
}

.health-text {
  font-size: 12px;
  color: #606266;
}
</style> 