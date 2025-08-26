<template>
  <div class="fault-history-container">
    <h2 class="page-title">故障历史记录</h2>
    <p class="page-description">
      实时监测过程中检测到的所有故障记录将在此显示，按故障类型分类展示。
    </p>

    <el-tabs type="border-card" class="fault-tabs">
      <el-tab-pane v-for="faultType in faultTypes" :key="faultType.type" :label="faultType.name">
        <div class="tab-header">
          <h3>{{ faultType.name }}历史记录</h3>
          <div class="tab-actions">
            <el-dropdown @command="handleExport($event, faultType.type)">
              <el-button type="primary" size="small">
                导出记录 <el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="json">JSON格式</el-dropdown-item>
                  <el-dropdown-item command="csv">CSV格式</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button type="danger" size="small" @click="clearFaultRecords(faultType.type)">
              清空记录
            </el-button>
          </div>
        </div>

        <div v-if="faultRecords[faultType.type].length === 0" class="no-data">
          <el-empty description="暂无故障记录" />
        </div>
        <div v-else class="fault-records">
          <el-timeline>
            <el-timeline-item
              v-for="(record, index) in faultRecords[faultType.type]"
              :key="index"
              :timestamp="formatTimestamp(record.timestamp)"
              :type="getStatusType(record.status)"
              :hollow="record.status === 'normal'"
              size="large"
            >
              <el-card class="fault-card" :class="getStatusClass(record.status)">
                <div class="fault-header">
                  <span class="fault-status">{{ getStatusText(record.status) }}</span>
                  <span class="fault-score">故障评分: {{ (record.score * 100).toFixed(1) }}%</span>
                </div>
                <div class="fault-features">
                  <div v-for="feature in getFaultFeatures(faultType.type, record)" :key="feature.key" class="feature-item">
                    <span class="feature-name">{{ feature.name }}:</span>
                    <span class="feature-value">{{ formatFeatureValue(feature, record.features[feature.key]) }}</span>
                  </div>
                </div>
                <div class="fault-actions">
                  <el-button type="primary" link @click="viewFaultDetails(record)">
                    查看详情
                  </el-button>
                </div>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 故障详情对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="故障详情"
      width="70%"
      destroy-on-close
    >
      <div v-if="selectedFault" class="fault-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="故障类型">{{ getFaultTypeName(selectedFault.fault_type) }}</el-descriptions-item>
          <el-descriptions-item label="故障状态">
            <el-tag :type="getStatusType(selectedFault.status)">{{ getStatusText(selectedFault.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="故障评分">{{ (selectedFault.score * 100).toFixed(1) }}%</el-descriptions-item>
          <el-descriptions-item label="检测时间">{{ formatTimestamp(selectedFault.timestamp) }}</el-descriptions-item>
        </el-descriptions>

        <h4>故障特征</h4>
        <el-table :data="selectedFaultFeatures" stripe style="width: 100%">
          <el-table-column prop="name" label="特征名称" width="180" />
          <el-table-column prop="value" label="特征值" width="180" />
          <el-table-column prop="description" label="描述" />
        </el-table>

        <div v-if="selectedFault.time_series" class="charts-container">
          <h4>时域波形</h4>
          <div class="chart-wrapper">
            <line-chart
              v-if="timeSeriesData && timeSeriesData.labels.length > 0"
              :chart-data="timeSeriesData"
              chart-id="detail-time-series-chart"
              :height="300"
              :options="timeChartOptions"
            />
            <el-empty v-else description="无时域波形数据" />
          </div>
        </div>

        <div v-if="selectedFault.frequency_spectrum" class="charts-container">
          <h4>频谱分析</h4>
          <div class="chart-wrapper">
            <line-chart
              v-if="spectrumData && spectrumData.labels.length > 0"
              :chart-data="spectrumData"
              chart-id="detail-spectrum-chart"
              :height="300"
              :options="spectrumOptions"
            />
            <el-empty v-else description="无频谱数据" />
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import LineChart from '@/components/charts/LineChart.vue';
import { ArrowDown } from '@element-plus/icons-vue';

// 故障类型定义
const faultTypes = [
  { 
    type: 'turn_fault', 
    name: '匝间短路故障',
    features: [
      { key: 'current_imbalance', name: '电流不平衡度', unit: '%', description: '三相电流幅值偏差' },
      { key: 'negative_sequence_ratio', name: '负序分量比例', unit: '%', description: '负序电流分量占比' },
      { key: 'third_harmonic_ratio', name: '三次谐波比例', unit: '%', description: '三次谐波与基波幅值比' }
    ]
  },
  { 
    type: 'broken_bar', 
    name: '断条故障',
    features: [
      { key: 'sideband_ratio', name: '边带幅值比', unit: '%', description: '断条特征边带与基波幅值比' },
      { key: 'normalized_fault_index', name: '归一化故障指数', unit: '%', description: '断条故障的综合评估指数' },
      { key: 'broken_bar_count', name: '估计断条数', unit: '', description: '系统估计的断裂导条数量' }
    ]
  },
  { 
    type: 'insulation', 
    name: '绝缘失效',
    features: [
      { key: 'insulation_resistance', name: '绝缘电阻', unit: 'MΩ', description: '电机绝缘对地电阻' },
      { key: 'leakage_current', name: '泄漏电流', unit: 'mA', description: '通过绝缘层的电流' },
      { key: 'dielectric_loss', name: '介质损耗', unit: '%', description: '绝缘材料的能量损耗' }
    ]
  },
  { 
    type: 'bearing', 
    name: '轴承故障',
    features: [
      { key: 'crest_factor', name: '冲击因子', unit: '', description: '振动信号峰值与有效值之比' },
      { key: 'kurtosis', name: '峭度', unit: '', description: '振动信号的峰态值' },
      { key: 'bearing_characteristic_frequency', name: '特征频率', unit: 'Hz', description: '与轴承故障相关的频率' }
    ]
  },
  { 
    type: 'eccentricity', 
    name: '偏心故障',
    features: [
      { key: 'static_ecc_ratio', name: '静态偏心率', unit: '%', description: '定子转子中心不重合度' },
      { key: 'dynamic_ecc_ratio', name: '动态偏心率', unit: '%', description: '转子旋转中心偏离几何中心程度' },
      { key: 'eccentricity_index', name: '综合指数', unit: '%', description: '反映偏心严重程度的综合指数' }
    ]
  }
];

// 故障记录数据
const faultRecords = reactive({
  turn_fault: [],
  broken_bar: [],
  insulation: [],
  bearing: [],
  eccentricity: []
});

// 对话框相关状态
const dialogVisible = ref(false);
const selectedFault = ref(null);
const selectedFaultFeatures = ref([]);
const timeSeriesData = ref(null);
const spectrumData = ref(null);

// 故障提示消息管理
const activeMessages = ref([]);
const MAX_MESSAGES = 3;

// 消息提示防抖 - 避免频繁弹出相同类型的消息
const messageDebounceMap = new Map();
const debouncedMessage = (message, type, duration) => {
  const key = `${type}-${message}`;
  if (messageDebounceMap.has(key)) {
    clearTimeout(messageDebounceMap.get(key));
    return; // 如果相同消息正在防抖中，直接返回
  }
  
  const timeoutId = setTimeout(() => {
    // 显示受限制的故障提示消息
    showLimitedMessage({
      message,
      type,
      duration
    });
    messageDebounceMap.delete(key);
  }, 2000); // 2秒内相同消息只显示一次
  
  messageDebounceMap.set(key, timeoutId);
};

// 显示受限制的故障提示消息
const showLimitedMessage = (messageConfig) => {
  // 如果已经达到最大消息数量，先关闭最早的消息
  if (activeMessages.value.length >= MAX_MESSAGES) {
    const oldestMessage = activeMessages.value.shift();
    if (oldestMessage && oldestMessage.close) {
      oldestMessage.close();
    }
  }
  
  // 创建新消息
  const messageInstance = ElMessage({
    ...messageConfig,
    onClose: () => {
      // 从活跃消息列表中移除
      const index = activeMessages.value.findIndex(msg => msg === messageInstance);
      if (index > -1) {
        activeMessages.value.splice(index, 1);
      }
    }
  });
  
  // 添加到活跃消息列表
  activeMessages.value.push(messageInstance);
  
  return messageInstance;
};

// 图表配置
const baseChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' },
    tooltip: { mode: 'index', intersect: false }
  },
  elements: { line: { tension: 0.2 }, point: { radius: 0 } }
};

const timeChartOptions = {
  ...baseChartOptions,
  scales: {
    x: { title: { display: true, text: '时间 (s)' } },
    y: { title: { display: true, text: '幅值' } }
  },
  plugins: { ...baseChartOptions.plugins, title: { display: true, text: '时域波形' } }
};

const spectrumOptions = {
  ...baseChartOptions,
  scales: {
    x: { title: { display: true, text: '频率 (Hz)' } },
    y: { title: { display: true, text: '幅值' }, beginAtZero: true }
  },
  plugins: { ...baseChartOptions.plugins, title: { display: true, text: '频谱分析' } }
};

// 在组件挂载时从本地存储加载故障记录
onMounted(() => {
  loadFaultRecordsFromStorage();
  // 添加WebSocket监听，接收实时故障记录
  setupWebSocketListener();
});

// 在组件卸载时清理活跃的消息和防抖定时器
onUnmounted(() => {
  // 关闭所有活跃的消息
  activeMessages.value.forEach(message => {
    if (message && message.close) {
      message.close();
    }
  });
  // 清空消息列表
  activeMessages.value = [];
  
  // 清理消息防抖定时器
  messageDebounceMap.forEach(timeoutId => {
    clearTimeout(timeoutId);
  });
  messageDebounceMap.clear();
});

// 从本地存储加载故障记录
const loadFaultRecordsFromStorage = () => {
  try {
    faultTypes.forEach(type => {
      const storageKey = `fault_history_${type.type}`;
      const savedRecords = localStorage.getItem(storageKey);
      if (savedRecords) {
        faultRecords[type.type] = JSON.parse(savedRecords);
      }
    });
  } catch (error) {
    console.error('加载故障记录时出错:', error);
  }
};

// 保存故障记录到本地存储
const saveFaultRecordsToStorage = (type) => {
  try {
    const storageKey = `fault_history_${type}`;
    const records = faultRecords[type];
    
    // 限制存储的记录数量和数据大小
    const maxRecords = 20; // 每种故障类型最多存储20条记录 - 优化：减少内存占用
    const recordsToSave = records.slice(0, maxRecords);
    
    // 精简存储的数据，只保留必要字段
    const simplifiedRecords = recordsToSave.map(record => ({
      timestamp: record.timestamp,
      status: record.status,
      score: record.score,
      fault_type: record.fault_type,
      // 只保留主要特征，去掉大数据量的time_series和frequency_spectrum
      features: record.features ? {
        // 根据故障类型选择性保留关键特征
        ...(record.fault_type === 'turn_fault' && record.features.I2_avg !== undefined ? { I2_avg: record.features.I2_avg } : {}),
        ...(record.fault_type === 'broken_bar' && record.features.sideband_amplitude !== undefined ? { sideband_amplitude: record.features.sideband_amplitude } : {}),
        ...(record.fault_type === 'bearing' && record.features.bearing_fault_freq_amplitude !== undefined ? { bearing_fault_freq_amplitude: record.features.bearing_fault_freq_amplitude } : {}),
        ...(record.fault_type === 'insulation' && record.features.insulation_resistance !== undefined ? { insulation_resistance: record.features.insulation_resistance, leakage_current: record.features.leakage_current } : {}),
        ...(record.fault_type === 'eccentricity' && record.features.static_ecc_ratio !== undefined ? { static_ecc_ratio: record.features.static_ecc_ratio, dynamic_ecc_ratio: record.features.dynamic_ecc_ratio } : {}),
        fault_severity: record.features.fault_severity
      } : undefined,
      diagnosis_conclusion: record.diagnosis_conclusion
    }));
    
    // 检查存储大小，如果还是太大就进一步精简
    const dataString = JSON.stringify(simplifiedRecords);
    const dataSizeKB = new Blob([dataString]).size / 1024;
    
    if (dataSizeKB > 500) { // 如果单个故障类型数据超过500KB
      console.warn(`[FaultHistory] ${type} 数据过大 (${dataSizeKB.toFixed(1)}KB)，进一步精简`);
      // 进一步减少记录数量
      const furtherSimplified = simplifiedRecords.slice(0, 20).map(record => ({
        timestamp: record.timestamp,
        status: record.status,
        score: record.score,
        fault_type: record.fault_type,
        diagnosis_conclusion: record.diagnosis_conclusion
      }));
      localStorage.setItem(storageKey, JSON.stringify(furtherSimplified));
    } else {
      localStorage.setItem(storageKey, dataString);
    }
    
    console.log(`[FaultHistory] 已保存 ${type} 故障记录: ${simplifiedRecords.length} 条 (${dataSizeKB.toFixed(1)}KB)`);
    
  } catch (error) {
    console.error('保存故障记录时出错:', error);
    
    // 如果仍然出现配额错误，尝试清理旧数据
    if (error.name === 'QuotaExceededError') {
      console.warn(`[FaultHistory] 存储配额不足，尝试清理 ${type} 的旧数据`);
      try {
        // 只保留最近10条最重要的记录
        const criticalRecords = faultRecords[type]
          .slice(0, 10)
          .map(record => ({
            timestamp: record.timestamp,
            status: record.status,
            score: record.score,
            fault_type: record.fault_type
          }));
        
        localStorage.setItem(`fault_history_${type}`, JSON.stringify(criticalRecords));
        console.log(`[FaultHistory] 已精简保存 ${type} 关键记录: ${criticalRecords.length} 条`);
        
        // 显示受限制的存储提示 - 使用防抖优化
        debouncedMessage(
          `存储空间不足，已自动清理${getFaultTypeName(type)}历史记录`,
          'warning',
          3000
        );
        
      } catch (secondError) {
        console.error('精简保存也失败:', secondError);
        // 最后手段：删除该类型的所有存储
        try {
          localStorage.removeItem(`fault_history_${type}`);
          debouncedMessage(
            `${getFaultTypeName(type)}历史记录存储失败，已清空本地缓存`,
            'error',
            5000
          );
        } catch (clearError) {
          console.error('清空存储也失败:', clearError);
        }
      }
    }
  }
};

// 设置WebSocket监听
const setupWebSocketListener = () => {
  const wsUrl = 'ws://localhost:8000/ws/frontend';
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    console.log('[FaultHistory] WebSocket连接已建立');
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      
      // 检查是否为故障诊断结果
      if (data.fault_type && data.status && (data.status === 'warning' || data.status === 'fault')) {
        // 移除频繁的日志输出以优化性能
        
        // 添加到对应的故障类型记录中
        if (faultRecords[data.fault_type]) {
          // 检查是否已存在相同时间戳的记录，避免重复
          const existingIndex = faultRecords[data.fault_type].findIndex(
            record => record.timestamp === data.timestamp
          );
          
          if (existingIndex === -1) {
            // 添加到记录开头，使最新的记录显示在前面
            faultRecords[data.fault_type].unshift(data);
            
            // 限制记录数量，避免过多 - 优化：减少到20条
            if (faultRecords[data.fault_type].length > 20) {
              faultRecords[data.fault_type].pop();
            }
            
            // 保存到本地存储
            saveFaultRecordsToStorage(data.fault_type);
            
            // 显示受限制的故障通知 - 使用防抖优化
            debouncedMessage(
              `检测到新的${getFaultTypeName(data.fault_type)}${getStatusText(data.status)}`,
              data.status === 'fault' ? 'error' : 'warning',
              3000
            );
          }
        }
      }
    } catch (error) {
      console.error('处理WebSocket消息时出错:', error);
    }
  };

  ws.onclose = () => {
    console.log('[FaultHistory] WebSocket连接已关闭，5秒后尝试重连');
    setTimeout(setupWebSocketListener, 5000);
  };

  ws.onerror = (error) => {
    console.error('[FaultHistory] WebSocket连接错误:', error);
  };
};

// 格式化时间戳
const formatTimestamp = (timestamp) => {
  if (!timestamp) return '未知时间';
  try {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  } catch (e) {
    return '无效时间';
  }
};

// 获取状态文本
const getStatusText = (status) => {
  const map = { normal: '正常', warning: '预警', fault: '故障', unknown: '未知' };
  return map[status] || '未知';
};

// 获取状态类型（用于Element Plus组件）
const getStatusType = (status) => {
  const map = { normal: 'success', warning: 'warning', fault: 'danger', unknown: 'info' };
  return map[status] || 'info';
};

// 获取状态CSS类
const getStatusClass = (status) => {
  if (status === 'fault') return 'status-fault';
  if (status === 'warning') return 'status-warning';
  return 'status-normal';
};

// 获取故障类型名称
const getFaultTypeName = (type) => {
  const faultType = faultTypes.find(t => t.type === type);
  return faultType ? faultType.name : '未知故障';
};

// 获取故障特征
const getFaultFeatures = (type, record) => {
  const faultType = faultTypes.find(t => t.type === type);
  return faultType ? faultType.features : [];
};

// 格式化特征值
const formatFeatureValue = (feature, value) => {
  if (value === undefined || value === null) return 'N/A';
  
  if (feature.unit === '%') {
    return (value * 100).toFixed(2) + '%';
  }
  
  if (typeof value === 'number') {
    return value.toFixed(2) + (feature.unit ? ` ${feature.unit}` : '');
  }
  
  return value;
};

// 查看故障详情
const viewFaultDetails = (record) => {
  selectedFault.value = record;
  
  // 准备特征数据
  const faultType = faultTypes.find(t => t.type === record.fault_type);
  if (faultType && record.features) {
    selectedFaultFeatures.value = faultType.features.map(feature => ({
      name: feature.name,
      value: formatFeatureValue(feature, record.features[feature.key]),
      description: feature.description
    }));
  } else {
    selectedFaultFeatures.value = [];
  }
  
  // 准备时域数据
  if (record.time_series) {
    prepareTimeSeriesData(record);
  } else {
    timeSeriesData.value = null;
  }
  
  // 准备频谱数据
  if (record.frequency_spectrum) {
    prepareSpectrumData(record);
  } else {
    spectrumData.value = null;
  }
  
  dialogVisible.value = true;
};

// 准备时域数据
const prepareTimeSeriesData = (record) => {
  const time = record.time_series.time || [];
  let datasets = [];

  if (record.fault_type === 'turn_fault' || record.fault_type === 'eccentricity') {
    // 三相电流数据
    const values_a = record.time_series.values_a || record.time_series.values_ia || [];
    const values_b = record.time_series.values_b || record.time_series.values_ib || [];
    const values_c = record.time_series.values_c || record.time_series.values_ic || [];
    
    if (time.length > 0 && values_a.length === time.length) {
      datasets = [
        { label: 'A相电流', data: values_a, borderColor: '#409EFF', borderWidth: 1, pointRadius: 0, fill: false },
        { label: 'B相电流', data: values_b, borderColor: '#67C23A', borderWidth: 1, pointRadius: 0, fill: false },
        { label: 'C相电流', data: values_c, borderColor: '#E6A23C', borderWidth: 1, pointRadius: 0, fill: false }
      ];
      timeSeriesData.value = { labels: time, datasets };
    }
  } else if (record.fault_type === 'broken_bar') {
    // 断条故障只需要单相电流
    const values_a = record.time_series.values_a || record.time_series.values_ia || [];
    
    if (time.length > 0 && values_a.length === time.length) {
      datasets = [
        { label: 'A相电流', data: values_a, borderColor: '#409EFF', borderWidth: 1, pointRadius: 0, fill: false }
      ];
      timeSeriesData.value = { labels: time, datasets };
    }
  } else if (record.fault_type === 'insulation') {
    // 绝缘故障需要电阻和泄漏电流
    const valuesResistance = record.time_series.values_resistance || [];
    const valuesLeakageCurrent = record.time_series.values_leakage_current || [];
    
    if (time.length > 0) {
      datasets = [
        { label: '绝缘电阻 (MΩ)', data: valuesResistance, borderColor: '#409EFF', backgroundColor: 'rgba(64, 158, 255, 0.1)', borderWidth: 1, pointRadius: 0 },
        { label: '泄漏电流 (mA)', data: valuesLeakageCurrent, borderColor: '#67C23A', backgroundColor: 'rgba(103, 194, 58, 0.1)', borderWidth: 1, pointRadius: 0 }
      ];
      timeSeriesData.value = { labels: time, datasets };
    }
  } else if (record.fault_type === 'bearing') {
    // 轴承故障需要振动数据
    const values = record.time_series.values || record.time_series.values_vibration || [];
    
    if (time.length > 0 && values.length === time.length) {
      datasets = [
        { label: '振动信号', data: values, borderColor: '#409EFF', borderWidth: 1, pointRadius: 0, fill: false }
      ];
      timeSeriesData.value = { labels: time, datasets };
    }
  }
};

// 准备频谱数据
const prepareSpectrumData = (record) => {
  if (!record.frequency_spectrum) return;
  
  const frequency = record.frequency_spectrum.frequency || [];
  const amplitude_a = record.frequency_spectrum.amplitude_a || [];
  const amplitude_b = record.frequency_spectrum.amplitude_b || [];
  const amplitude_c = record.frequency_spectrum.amplitude_c || [];

  if (frequency.length > 0 && amplitude_a.length === frequency.length) {
    const datasets = [
      { label: 'A相频谱', data: amplitude_a, borderColor: '#409EFF', backgroundColor: 'rgba(64, 158, 255, 0.1)', borderWidth: 1, pointRadius: 0, fill: false }
    ];
    
    if (amplitude_b.length > 0) {
      datasets.push({ label: 'B相频谱', data: amplitude_b, borderColor: '#67C23A', backgroundColor: 'rgba(103, 194, 58, 0.1)', borderWidth: 1, pointRadius: 0, fill: false });
    }
    
    if (amplitude_c.length > 0) {
      datasets.push({ label: 'C相频谱', data: amplitude_c, borderColor: '#E6A23C', backgroundColor: 'rgba(230, 162, 60, 0.1)', borderWidth: 1, pointRadius: 0, fill: false });
    }
    
    spectrumData.value = { labels: frequency, datasets };
  }
};

// 处理导出下拉菜单选择
const handleExport = (command, type) => {
  if (command === 'json') {
    exportFaultRecords(type);
  } else if (command === 'csv') {
    exportFaultRecordsAsCSV(type);
  }
};

// 导出故障记录为CSV格式
const exportFaultRecordsAsCSV = (type) => {
  if (faultRecords[type].length === 0) {
    ElMessage.warning('没有可导出的故障记录');
    return;
  }
  
  try {
    // 获取故障类型特征
    const faultType = faultTypes.find(t => t.type === type);
    if (!faultType) {
      ElMessage.error('未找到故障类型配置');
      return;
    }
    
    // 准备CSV标题行
    const headers = [
      '时间', 
      '状态', 
      '故障评分(%)'
    ];
    
    // 添加特征名称到标题行
    faultType.features.forEach(feature => {
      headers.push(feature.name + (feature.unit ? `(${feature.unit})` : ''));
    });
    
    // 准备CSV内容行
    const rows = faultRecords[type].map(record => {
      const row = [
        formatTimestamp(record.timestamp),
        getStatusText(record.status),
        (record.score * 100).toFixed(1)
      ];
      
      // 添加特征值
      faultType.features.forEach(feature => {
        if (record.features && record.features[feature.key] !== undefined) {
          let value = record.features[feature.key];
          if (feature.unit === '%') {
            value = (value * 100).toFixed(2);
          } else if (typeof value === 'number') {
            value = value.toFixed(2);
          }
          row.push(value);
        } else {
          row.push('N/A');
        }
      });
      
      return row;
    });
    
    // 将数组转换为CSV字符串
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');
    
    // 创建Blob对象
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    
    // 创建下载链接
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${type}_故障记录_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.csv`;
    
    // 触发下载
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    ElMessage.success('故障记录已导出为CSV格式');
  } catch (error) {
    console.error('导出CSV故障记录时出错:', error);
    ElMessage.error('导出故障记录失败');
  }
};

// 导出故障记录为JSON格式 (原有函数重命名)
const exportFaultRecords = (type) => {
  if (faultRecords[type].length === 0) {
    ElMessage.warning('没有可导出的故障记录');
    return;
  }
  
  try {
    // 准备导出数据
    const exportData = {
      fault_type: type,
      fault_type_name: getFaultTypeName(type),
      export_time: new Date().toISOString(),
      records: faultRecords[type]
    };
    
    // 转换为JSON字符串
    const jsonString = JSON.stringify(exportData, null, 2);
    
    // 创建Blob对象
    const blob = new Blob([jsonString], { type: 'application/json' });
    
    // 创建下载链接
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${type}_故障记录_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
    
    // 触发下载
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    ElMessage.success('故障记录已导出为JSON格式');
  } catch (error) {
    console.error('导出JSON故障记录时出错:', error);
    ElMessage.error('导出故障记录失败');
  }
};

// 清空故障记录
const clearFaultRecords = (type) => {
  ElMessageBox.confirm(
    `确定要清空所有${getFaultTypeName(type)}的故障记录吗？此操作不可恢复。`,
    '确认清空',
    {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
    .then(() => {
      // 清空内存中的记录
      faultRecords[type] = [];
      
      // 清空localStorage中的记录
      try {
        localStorage.removeItem(`fault_history_${type}`);
        console.log(`[FaultHistory] 已清空 ${type} 的localStorage存储`);
      } catch (error) {
        console.error(`清空 ${type} localStorage时出错:`, error);
      }
      
      ElMessage.success(`${getFaultTypeName(type)}故障记录已清空`);
    })
    .catch(() => {
      // 用户取消操作
    });
};
</script>

<style scoped>
.fault-history-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  margin-bottom: 10px;
  color: #303133;
}

.page-description {
  color: #606266;
  margin-bottom: 20px;
}

.fault-tabs {
  margin-top: 20px;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.tab-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.tab-actions {
  display: flex;
  gap: 10px;
}

.no-data {
  height: 200px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.fault-records {
  margin-top: 20px;
}

.fault-card {
  margin-bottom: 10px;
  border-radius: 8px;
  transition: all 0.3s;
}

.fault-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.fault-card.status-warning {
  background-color: #fdf6ec;
  border-color: #e6a23c;
}

.fault-card.status-fault {
  background-color: #fef0f0;
  border-color: #f56c6c;
}

.fault-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.fault-status {
  font-weight: bold;
  font-size: 16px;
}

.fault-score {
  font-weight: bold;
}

.fault-features {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 15px;
}

.feature-item {
  background-color: rgba(255, 255, 255, 0.7);
  padding: 8px 12px;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.feature-name {
  font-weight: 600;
  margin-right: 5px;
}

.feature-value {
  font-weight: 500;
}

.fault-actions {
  text-align: right;
  margin-top: 10px;
}

.fault-detail {
  padding: 10px;
}

.charts-container {
  margin-top: 20px;
}

.charts-container h4 {
  margin-bottom: 15px;
  font-size: 16px;
  color: #303133;
}

.chart-wrapper {
  height: 300px;
  width: 100%;
  margin-bottom: 20px;
}
</style> 