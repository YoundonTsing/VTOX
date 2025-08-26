<template>
  <div class="vehicle-detail-view">
    <!-- 车辆信息头部 -->
    <div class="detail-header">
      <div class="header-left">
        <el-button type="primary" @click="goBack" class="back-button">
          ← 返回车队监控
        </el-button>
        <div class="vehicle-info">
          <div class="vehicle-title">
            <span class="vehicle-icon">{{ getVehicleIcon(vehicleId) }}</span>
            <h2>{{ getVehicleName(vehicleId) }}</h2>
            <el-tag :type="getVehicleStatusType()" size="large">
              {{ getVehicleStatusText() }}
            </el-tag>
          </div>
          <div class="vehicle-meta">
            <span>📍 {{ getLocationFromVehicleId(vehicleId) }}</span>
            <span>🚗 {{ getVehicleModel(vehicleId) }}</span>
            <span>⏰ {{ formatConnectionTime() }}</span>
          </div>
        </div>
      </div>
      <div class="header-right">
        <div class="health-score">
          <div class="score-circle">
            <div class="score-value" :style="{ color: getHealthColor(overallHealthScore) }">
              {{ overallHealthScore.toFixed(1) }}%
            </div>
            <div class="score-label">健康度</div>
          </div>
        </div>
        <!-- 实时连接状态 -->
        <div class="connection-status">
          <el-tag :type="getConnectionStatusType(connectionStatus)" size="large">
            {{ getConnectionStatusText(connectionStatus) }}
          </el-tag>
          <el-button 
            v-if="connectionStatus !== 'connected'" 
            type="primary" 
            @click="startMonitoring"
            :disabled="connectionStatus === 'connecting'"
            size="small"
          >
            开始监控
          </el-button>
        </div>
      </div>
    </div>

    <!-- 故障状态概览 -->
    <div class="status-overview">
      <div class="overview-grid">
        <div 
          v-for="faultType in faultTypes" 
          :key="faultType.type"
          class="fault-overview-card"
          :class="getFaultStatusClass(vehicleData[faultType.type])"
          @click="scrollToFaultSection(faultType.type)"
        >
          <div class="fault-header">
            <div class="fault-icon">{{ faultType.icon }}</div>
            <div class="fault-info">
              <div class="fault-name">{{ faultType.name }}</div>
              <el-tag :type="getFaultTagType(vehicleData[faultType.type])" size="small">
                {{ getFaultStatusText(vehicleData[faultType.type]) }}
              </el-tag>
            </div>
          </div>
          <div class="fault-score">
            <div class="score-number" :style="{ color: getFaultScoreColor(vehicleData[faultType.type]) }">
              {{ formatFaultScore(vehicleData[faultType.type]) }}%
            </div>
          </div>
          <div class="fault-features">
            <div 
              v-for="feature in faultType.features" 
              :key="feature.key"
              class="feature-mini"
            >
              <span class="feature-mini-name">{{ feature.name }}</span>
              <span class="feature-mini-value">
                {{ formatFeatureValue(vehicleData[faultType.type], feature) }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 详细故障诊断图表 -->
    <div v-if="connectionStatus === 'connected'" class="fault-details-container">
      <div 
        v-for="faultType in faultTypes" 
        :key="faultType.type"
        :ref="el => faultSectionRefs[faultType.type] = el"
        class="fault-detail-section"
      >
        <div class="section-header">
          <h3>{{ faultType.icon }} {{ faultType.name }}详细分析</h3>
          <div class="section-actions">
            <el-button type="primary" size="small" @click="exportFaultData(faultType.type)">
              📊 导出数据
            </el-button>
            <el-button 
              type="info" 
              size="small" 
              @click="toggleSectionExpand(faultType.type)"
            >
              {{ expandedSections.has(faultType.type) ? '收起' : '展开' }}
            </el-button>
          </div>
        </div>

        <!-- 实时数据图表 -->
        <el-collapse-transition>
          <div v-show="expandedSections.has(faultType.type)" class="charts-grid">
          <div class="chart-container">
            <div class="chart-header">
              <h4>📈 时域信号</h4>
                <div class="chart-info">
                  <span>更新: {{ formatLastUpdate(vehicleData[faultType.type]) }}</span>
                </div>
            </div>
            <div class="chart-content">
                <high-performance-line-chart
                  v-if="vehicleData[faultType.type]?.timeSeries && vehicleData[faultType.type].timeSeries.labels?.length > 0"
                  :chart-data="vehicleData[faultType.type].timeSeries"
                  :chart-id="`vehicle-time-series-${faultType.type}`"
                  :height="300"
                  :options="getTimeChartOptions(faultType)"
                  :max-data-points="50"
                  :sampling-rate="3"
                  update-mode="incremental"
                />
                <div v-else class="chart-placeholder">
                <div class="placeholder-icon">📈</div>
                  <div class="placeholder-text">等待{{ faultType.name }}时域数据...</div>
              </div>
            </div>
          </div>

          <div class="chart-container">
            <div class="chart-header">
                <h4>{{ faultType.type === 'turn_fault' ? '📊 频域分析' : '📊 特征趋势' }}</h4>
            </div>
            <div class="chart-content">
                <high-performance-line-chart
                  v-if="getSecondChartData(vehicleData[faultType.type], faultType.type)"
                  :chart-data="getSecondChartData(vehicleData[faultType.type], faultType.type)"
                  :chart-id="`vehicle-second-chart-${faultType.type}`"
                  :height="300"
                  :options="getSecondChartOptions(faultType)"
                  :max-data-points="40"
                  :sampling-rate="2"
                  update-mode="incremental"
                />
                <div v-else class="chart-placeholder">
                <div class="placeholder-icon">📊</div>
                  <div class="placeholder-text">
                    等待{{ faultType.type === 'turn_fault' ? '频域分析' : '特征趋势' }}数据...
              </div>
            </div>
          </div>
        </div>

            <div class="chart-container history-chart-container">
              <div class="chart-header">
                <h4>📈 历史趋势</h4>
              </div>
              <div class="chart-content">
                <high-performance-line-chart
                  v-if="vehicleData[faultType.type]?.historyChart && vehicleData[faultType.type].historyChart.labels?.length > 0"
                  :chart-data="vehicleData[faultType.type].historyChart"
                  :chart-id="`vehicle-history-chart-${faultType.type}`"
                  :height="380"
                  :options="getHistoryChartOptions(faultType)"
                  :max-data-points="20"
                  :sampling-rate="1"
                  update-mode="incremental"
                />
                <div v-else class="chart-placeholder">
                  <div class="placeholder-icon">📈</div>
                  <div class="placeholder-text">等待历史趋势数据...</div>
                </div>
              </div>
              <!-- 日期显示 -->
              <div 
                v-if="vehicleData[faultType.type]?.history && vehicleData[faultType.type].history.length > 0" 
                class="chart-date-info"
              >
                <span class="chart-date">
                  📅 {{ getHistoryDateRange(vehicleData[faultType.type].history) }}
                </span>
              </div>
            </div>
          </div>
        </el-collapse-transition>
      </div>
    </div>

    <!-- 等待连接提示 -->
    <div v-else class="waiting-message">
      <el-empty 
        :description="connectionStatus === 'connecting' ? '正在连接实时数据...' : '请点击开始监控查看实时数据'" 
        :image-size="100" 
      />
    </div>

    <!-- 调试信息面板 (仅开发环境) -->
    <div v-if="connectionStatus === 'connected'" class="debug-panel">
      <el-collapse>
        <el-collapse-item title="🔍 调试信息" name="debug">
          <div class="debug-content">
            <div class="debug-section">
              <h4>车辆ID: {{ vehicleId }}</h4>
              <p>连接状态: {{ connectionStatus }}</p>
              <p>整体健康评分: {{ overallHealthScore.toFixed(1) }}%</p>
            </div>
            
            <div class="debug-section" v-for="fault in faultTypes" :key="fault.type">
              <h5>{{ fault.name }} ({{ fault.type }})</h5>
              <div class="debug-data">
                <p>最新数据: {{ vehicleData[fault.type]?.latest ? '有' : '无' }}</p>
                <p>历史记录: {{ vehicleData[fault.type]?.history?.length || 0 }} 条</p>
                <p>时域数据: {{ vehicleData[fault.type]?.timeSeries?.labels?.length || 0 }} 点</p>
                <p>特征值: {{ vehicleData[fault.type]?.latest?.features ? Object.keys(vehicleData[fault.type].latest.features).length : 0 }} 个</p>
                <div v-if="vehicleData[fault.type]?.latest?.features" class="features-debug">
                  <span v-for="(value, key) in vehicleData[fault.type].latest.features" :key="key" class="feature-debug">
                    {{ key }}: {{ value }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';

// 导入全局数据管理器和WebSocket管理器
import globalDataManager from '@/utils/dataManager.js';
import globalWebSocketManager from '@/utils/webSocketManager.js';
import HighPerformanceLineChart from '@/components/charts/HighPerformanceLineChart.vue';

const route = useRoute();
const router = useRouter();

// 车辆ID - 解码URL参数中的中文字符
const vehicleId = ref(decodeURIComponent(route.params.vehicleId || ''));
const connectionStatus = ref('disconnected');
const connectionStartTime = ref(null);
const faultSectionRefs = reactive({});
const expandedSections = ref(new Set(['turn_fault', 'insulation'])); // 默认展开一些重要故障

// 添加响应式触发器
const dataUpdateTrigger = ref(0);

// 故障类型定义
const faultTypes = ref([
  { 
    type: 'turn_fault', 
    name: '匝间短路故障', 
    icon: '🎯',
    features: [
      { key: 'current_imbalance', name: '电流不平衡度', unit: '%' },
      { key: 'negative_sequence_ratio', name: '负序分量比例', unit: '%' },
      { key: 'third_harmonic_ratio', name: '三次谐波比例', unit: '%' }
    ]
  },
  { 
    type: 'insulation', 
    name: '绝缘失效故障', 
    icon: '🔌',
    features: [
      { key: 'insulation_resistance', name: '绝缘电阻', unit: 'MΩ' },
      { key: 'leakage_current', name: '泄漏电流', unit: 'mA' },
      { key: 'dielectric_loss', name: '介质损耗', unit: '%' }
    ]
  },
  { 
    type: 'bearing', 
    name: '轴承故障', 
    icon: '⚙️',
    features: [
      { key: 'crest_factor', name: '冲击因子', unit: '' },
      { key: 'kurtosis', name: '峭度', unit: '' },
      { key: 'bearing_characteristic_frequency', name: '特征频率', unit: 'Hz' }
    ]
  },
  { 
    type: 'eccentricity', 
    name: '偏心故障', 
    icon: '🔄',
    features: [
      { key: 'static_ecc_ratio', name: '静态偏心率', unit: '%' },
      { key: 'dynamic_ecc_ratio', name: '动态偏心率', unit: '%' },
      { key: 'eccentricity_index', name: '综合指数', unit: '%' }
    ]
  },
  { 
    type: 'broken_bar', 
    name: '断条故障', 
    icon: '🔗',
    features: [
      { key: 'sideband_ratio', name: '边带幅值比', unit: '%' },
      { key: 'normalized_fault_index', name: '归一化故障指数', unit: '%' },
      { key: 'broken_bar_count', name: '估计断条数', unit: '' }
    ]
  }
]);

// 使用计算属性获取过滤后的车辆数据
const vehicleData = computed(() => {
  // 监听数据更新触发器以确保响应式更新
  dataUpdateTrigger.value;
  
  const result = {};
  faultTypes.value.forEach(fault => {
    const allData = globalDataManager.getData(fault.type);
    

    
    // 从历史记录中筛选当前车辆的数据
    const vehicleHistory = allData && allData.history ? 
      allData.history.filter(item => item.vehicle_id === vehicleId.value) : [];
    
    // 检查最新数据是否属于当前车辆
    const latestBelongsToVehicle = allData && allData.latest && 
      allData.latest.vehicle_id === vehicleId.value;
    
    if (latestBelongsToVehicle || vehicleHistory.length > 0) {
      // 为当前车辆重建数据结构
      const vehicleSpecificData = {
        latest: latestBelongsToVehicle ? allData.latest : (vehicleHistory.length > 0 ? vehicleHistory[vehicleHistory.length - 1] : null),
        history: vehicleHistory,
        timeSeries: { labels: [], datasets: [] },
        spectrum: { labels: [], datasets: [] },
        featureTrend: { labels: [], datasets: [] },
        historyChart: { labels: [], datasets: [] }
      };
      
      // 重建历史趋势图表（如果有历史数据）
      if (vehicleHistory.length > 0) {
        rebuildChartsForVehicle(vehicleSpecificData, fault.type);
      }
      
      // 如果最新数据属于当前车辆，重建实时图表数据
      if (latestBelongsToVehicle && allData.latest) {
        // 重建时域图表 - 等待后端发送time_series数据
        if (allData.latest.time_series) {
          rebuildTimeSeriesChart(vehicleSpecificData, allData.latest, fault.type);
        } else {
          // console.log(`⚠️  [${fault.type}] 未接收到time_series数据`);
        }
        
        // 重建频谱图表 - 检查spectrum字段或frequency_spectrum字段
        if (allData.latest.spectrum && allData.latest.spectrum.labels) {
          rebuildSpectrumFromSpectrum(vehicleSpecificData, allData.latest);
        } else if (allData.latest.frequency_spectrum && fault.type === 'turn_fault') {
          rebuildSpectrumChart(vehicleSpecificData, allData.latest);
        }
        
        // 如果没有历史数据但有最新数据，尝试从最新数据构建特征趋势
        if (vehicleHistory.length === 0 && allData.latest.features && fault.features) {
          rebuildFeatureTrendFromLatest(vehicleSpecificData, allData.latest, fault);
        }
      }
      
      result[fault.type] = vehicleSpecificData;
    } else {
      result[fault.type] = {
        latest: null,
        timeSeries: { labels: [], datasets: [] },
        spectrum: { labels: [], datasets: [] },
        featureTrend: { labels: [], datasets: [] },
        historyChart: { labels: [], datasets: [] },
        history: []
      };
    }
  });
  return result;
});

// 计算整体健康评分
const overallHealthScore = computed(() => {
  const scores = faultTypes.value.map(fault => {
    const data = vehicleData.value[fault.type];
    if (data && data.latest && data.latest.vehicle_id === vehicleId.value) {
      return data.latest.health_score || (100 - (data.latest.score || 0) * 100);
    }
    return 100;
  });
  
  if (scores.length === 0) return 100;
  return scores.reduce((a, b) => a + b, 0) / scores.length;
});

// 为特定车辆重建图表数据
const rebuildChartsForVehicle = (vehicleData, faultType) => {
  if (!vehicleData.history || vehicleData.history.length === 0) return;
  
  const faultConfig = faultTypes.value.find(f => f.type === faultType);
  if (!faultConfig) return;
  
  try {
    // 重建历史趋势图表 - 只使用时间部分作为标签
    const historyLabels = vehicleData.history.map(item => formatToBeijingTimeOnly(item.timestamp));
    const scores = vehicleData.history.map(item => item.score || 0);
    
    vehicleData.historyChart = {
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
    
    // 重建特征趋势图表
    if (faultConfig.features && vehicleData.history.length > 1) {
      const featureDatasets = faultConfig.features.map((feature, index) => {
        const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399'];
        const values = vehicleData.history.map(item => {
          const value = item.features?.[feature.key];
          if (value === undefined || value === null) return 0;
          
          // 智能百分比处理
          if (feature.unit === '%') {
            let percentValue = value;
            if (value <= 1 && value >= 0) {
              percentValue = value * 100;
            } else if (value > 1000) {
              percentValue = value / 100;
            }
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
      
      vehicleData.featureTrend = {
        labels: historyLabels, // 使用相同的时间标签
        datasets: featureDatasets
      };
    }
    
    // 如果有最新的时域数据，尝试重建时域图表
    const latestItem = vehicleData.history[vehicleData.history.length - 1];
    if (latestItem && latestItem.time_series) {
      rebuildTimeSeriesChart(vehicleData, latestItem, faultType);
    }
    
  } catch (error) {
    console.error(`重建${faultType}图表时出错:`, error);
  }
};

// 重建时域图表
const rebuildTimeSeriesChart = (vehicleData, latestData, faultType) => {
  if (!latestData.time_series?.time) {
    // console.log(`⚠️  [${faultType}] 缺少time_series.time数据:`, latestData.time_series);
    return;
  }
  
  try {
    const time = latestData.time_series.time;
    const formattedTime = time.map((t, index) => {
      // 对于实时数据，使用更简洁的时间格式
      if (typeof t === 'number') {
        // 如果是数值类型，假设是相对时间（秒）
        return `${t.toFixed(3)}s`;
      } else {
        // 如果是时间戳，只显示时间部分
        const pointTime = new Date(Date.now() - (time.length - index) * 1000);
        return formatToBeijingTimeOnly(pointTime.toISOString());
      }
    });

    let datasets = [];

    // 根据故障类型构建数据集 - 处理后端发送的数据格式
    switch (faultType) {
      case 'turn_fault':
      case 'eccentricity':
        const values_a = latestData.time_series.values_ia || latestData.time_series.values_a || [];
        const values_b = latestData.time_series.values_ib || latestData.time_series.values_b || [];
        const values_c = latestData.time_series.values_ic || latestData.time_series.values_c || [];
        
        // console.log(`📊 [${faultType}] 三相电流数据:`, {
        //   'A相': values_a.length,
        //   'B相': values_b.length, 
        //   'C相': values_c.length,
        //   'A相示例': values_a.slice(0, 3),
        //   'B相示例': values_b.slice(0, 3),
        //   'C相示例': values_c.slice(0, 3)
        // });
        
        datasets = [
          { label: 'A相电流', data: values_a, borderColor: '#409EFF', borderWidth: 1, pointRadius: 0, fill: false },
          { label: 'B相电流', data: values_b, borderColor: '#67C23A', borderWidth: 1, pointRadius: 0, fill: false },
          { label: 'C相电流', data: values_c, borderColor: '#E6A23C', borderWidth: 1, pointRadius: 0, fill: false }
        ].filter(ds => ds.data.length > 0);
        break;
      case 'broken_bar':
        const broken_values_a = latestData.time_series.values_ia || latestData.time_series.values_a || [];
        if (broken_values_a.length > 0) {
          datasets = [{ label: 'A相电流', data: broken_values_a, borderColor: '#409EFF', borderWidth: 1, pointRadius: 0, fill: false }];
        }
        // console.log(`📊 [${faultType}] A相电流数据:`, broken_values_a.length, '个点');
        break;
      case 'insulation':
        const resistance = latestData.time_series.values_resistance || [];
        const leakage = latestData.time_series.values_leakage_current || [];
        datasets = [
          resistance.length > 0 ? { label: '绝缘电阻 (MΩ)', data: resistance, borderColor: '#409EFF', borderWidth: 1, pointRadius: 0, yAxisID: 'y' } : null,
          leakage.length > 0 ? { label: '泄漏电流 (mA)', data: leakage, borderColor: '#67C23A', borderWidth: 1, pointRadius: 0, yAxisID: 'y1' } : null
        ].filter(ds => ds !== null);
        // console.log(`📊 [${faultType}] 绝缘数据:`, {
        //   '绝缘电阻': resistance.length,
        //   '泄漏电流': leakage.length
        // });
        break;
      case 'bearing':
        const vibration = latestData.time_series.values_vibration || latestData.time_series.values || [];
        if (vibration.length > 0) {
          datasets = [{ label: '振动信号', data: vibration, borderColor: '#409EFF', borderWidth: 1, pointRadius: 0, fill: false }];
        }
        // console.log(`📊 [${faultType}] 振动数据:`, vibration.length, '个点');
        break;
    }

    if (datasets.length > 0) {
      vehicleData.timeSeries = { labels: formattedTime, datasets };
      // console.log(`✅ [${faultType}] 时域图表构建成功: ${formattedTime.length}个时间点, ${datasets.length}个数据集`);
    } else {
      // console.log(`❌ [${faultType}] 时域图表构建失败: 没有有效数据集`);
    }
    
    // 如果有频谱数据，也重建频谱图表
    if (latestData.frequency_spectrum && faultType === 'turn_fault') {
      rebuildSpectrumChart(vehicleData, latestData);
    }
    
  } catch (error) {
    console.error(`❌ [${faultType}] 重建时域图表时出错:`, error);
  }
};

// 重建频谱图表
const rebuildSpectrumChart = (vehicleData, latestData) => {
  if (!latestData.frequency_spectrum?.frequency) return;
  
  try {
    const frequency = latestData.frequency_spectrum.frequency;
    const amplitude_a = latestData.frequency_spectrum.amplitude_a || [];
    const amplitude_b = latestData.frequency_spectrum.amplitude_b || [];
    const amplitude_c = latestData.frequency_spectrum.amplitude_c || [];

    const datasets = [
      amplitude_a.length > 0 ? { label: 'A相频谱', data: amplitude_a, borderColor: '#409EFF', borderWidth: 1, pointRadius: 0, fill: false } : null,
      amplitude_b.length > 0 ? { label: 'B相频谱', data: amplitude_b, borderColor: '#67C23A', borderWidth: 1, pointRadius: 0, fill: false } : null,
      amplitude_c.length > 0 ? { label: 'C相频谱', data: amplitude_c, borderColor: '#E6A23C', borderWidth: 1, pointRadius: 0, fill: false } : null
    ].filter(ds => ds !== null);
    
    if (datasets.length > 0) {
      vehicleData.spectrum = { labels: frequency, datasets };
      // console.log(`✅ 频谱图表已构建: ${frequency.length}个频率点, ${datasets.length}个数据集`);
    }
  } catch (error) {
    console.error('重建频谱图表时出错:', error);
  }
};

// 实时数据消息处理
const handleRealtimeMessage = (data) => {
  try {
    // 只处理当前车辆的数据
    if (data.vehicle_id !== vehicleId.value) {
      return; // 忽略其他车辆的数据
    }
    
    const faultType = data.fault_type;
    
    // 忽略unknown类型的消息和其他不支持的类型
    if (!faultType || faultType === 'unknown' || faultType === 'multi_fault') {
      return; // 静默忽略，不输出警告
    }
    
    const faultConfig = faultTypes.value.find(f => f.type === faultType);
    
    if (!faultConfig) {
      // console.warn(`未知故障类型: ${faultType}`);
      return;
    }
    
    // 使用全局数据管理器处理数据
    globalDataManager.processRealtimeData(faultType, data);
    
    // 触发Vue响应式更新
    dataUpdateTrigger.value++;
    
  } catch (error) {
    console.error('处理车辆实时消息时出错:', error);
  }
};

// 工具函数
const getVehicleIcon = (vehicleId) => {
  if (vehicleId.includes('SEAL')) return '🦭';
  if (vehicleId.includes('QIN')) return '🏮';
  if (vehicleId.includes('HAN')) return '🏛️';
  return '🚗';
};

const getVehicleName = (vehicleId) => {
  const parts = vehicleId.split('_');
  return parts.length > 1 ? parts.slice(0, -1).join('_') : vehicleId;
};

const getVehicleModel = (vehicleId) => {
  if (vehicleId.includes('SEAL')) return '比亚迪海豹';
  if (vehicleId.includes('QIN')) return '比亚迪秦';
  if (vehicleId.includes('HAN')) return '比亚迪汉';
  return '未知型号';
};

const getLocationFromVehicleId = (vehicleId) => {
  if (vehicleId.includes('粤B')) return '深圳福田区';
  if (vehicleId.includes('陕A')) return '西安高新区';
  return '未知位置';
};

const getHealthColor = (score) => {
  if (score >= 90) return '#67c23a';
  if (score >= 70) return '#e6a23c';
  return '#f56c6c';
};

const getVehicleStatusText = () => {
  const score = overallHealthScore.value;
  if (score >= 90) return '健康';
  if (score >= 70) return '预警';
  return '故障';
};

const getVehicleStatusType = () => {
  const score = overallHealthScore.value;
  if (score >= 90) return 'success';
  if (score >= 70) return 'warning';
  return 'danger';
};

const getConnectionStatusType = (status) => {
  const map = { connected: 'success', connecting: 'info', disconnected: 'danger', error: 'danger' };
  return map[status] || 'info';
};

const getConnectionStatusText = (status) => {
  const map = { connected: '已连接', connecting: '连接中...', disconnected: '未连接', error: '连接错误' };
  return map[status] || '未知状态';
};

const getFaultStatusClass = (faultData) => {
  if (!faultData || !faultData.latest) return 'fault-unknown';
  const score = faultData.latest.score || 0;
  if (score < 0.3) return 'fault-normal';
  if (score < 0.7) return 'fault-warning';
  return 'fault-danger';
};

const getFaultStatusText = (faultData) => {
  if (!faultData || !faultData.latest) return '未知';
  const score = faultData.latest.score || 0;
  if (score < 0.3) return '正常';
  if (score < 0.7) return '预警';
  return '故障';
};

const getFaultTagType = (faultData) => {
  if (!faultData || !faultData.latest) return 'info';
  const score = faultData.latest.score || 0;
  if (score < 0.3) return 'success';
  if (score < 0.7) return 'warning';
  return 'danger';
};

const getFaultScoreColor = (faultData) => {
  if (!faultData || !faultData.latest) return '#909399';
  const score = faultData.latest.score || 0;
  if (score < 0.3) return '#67c23a';
  if (score < 0.7) return '#e6a23c';
  return '#f56c6c';
};

const formatFaultScore = (faultData) => {
  if (!faultData || !faultData.latest) return '0.0';
  return ((faultData.latest.score || 0) * 100).toFixed(1);
};

const formatFeatureValue = (faultData, feature) => {
  if (!faultData || !faultData.latest || !faultData.latest.features) {
    return feature.unit === '%' ? '0.00%' : `0 ${feature.unit}`;
  }
  
  const value = faultData.latest.features[feature.key];
  if (value === undefined || value === null) {
    return feature.unit === '%' ? '0.00%' : `0 ${feature.unit}`;
  }
  
  if (typeof value === 'number' && !isNaN(value)) {
    if (feature.unit === '%') {
      // 智能百分比处理
      let percentValue = value;
      if (value <= 1 && value >= 0) {
        percentValue = value * 100;
      } else if (value > 1000) {
        percentValue = value / 100;
      }
      percentValue = Math.max(0, Math.min(percentValue, 9999.99));
      return percentValue.toFixed(2) + '%';
    }
    return value.toFixed(2) + (feature.unit ? ` ${feature.unit}` : '');
  }
  
  return value.toString() + (feature.unit ? ` ${feature.unit}` : '');
};

const formatLastUpdate = (faultData) => {
  if (!faultData || !faultData.latest || !faultData.latest.timestamp) return '暂无数据';
  
  try {
    return new Date(faultData.latest.timestamp).toLocaleTimeString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      hour12: false,
    });
  } catch (e) {
    return '时间格式错误';
  }
};

const formatConnectionTime = () => {
  if (!connectionStartTime.value) return '--';
  const duration = Date.now() - connectionStartTime.value;
  const hours = Math.floor(duration / 3600000);
  const minutes = Math.floor((duration % 3600000) / 60000);
  return `${hours}h${minutes}m`;
};

// 格式化为北京时间
const formatToBeijingTime = (isoString) => {
  try {
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  } catch (e) {
    return isoString;
  }
};

// 格式化为北京时间（只返回时间部分）
const formatToBeijingTimeOnly = (isoString) => {
  try {
    const date = new Date(isoString);
    return date.toLocaleTimeString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  } catch (e) {
    return isoString;
  }
};

// 格式化为北京日期（只返回日期部分）
const formatToBeijingDateOnly = (isoString) => {
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString('zh-CN', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  } catch (e) {
    return isoString;
  }
};

// 图表配置
const baseChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { 
      position: 'top',
      labels: { color: 'rgba(255, 255, 255, 0.9)' }
    },
    tooltip: { 
      mode: 'index', 
      intersect: false,
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      titleColor: 'rgba(255, 255, 255, 0.9)',
      bodyColor: 'rgba(255, 255, 255, 0.8)',
      borderColor: 'rgba(255, 255, 255, 0.3)',
      borderWidth: 1
    }
  },
  elements: { line: { tension: 0.2 }, point: { radius: 0 } },
  animation: false
};

const getTimeChartOptions = (faultType) => {
  const baseConfig = {
    ...baseChartOptions,
    scales: {
      x: { 
        title: { display: true, text: '时间', color: 'rgba(255, 255, 255, 0.9)' },
        ticks: { 
          maxTicksLimit: 10,
          color: 'rgba(255, 255, 255, 0.8)'
        },
        grid: { 
          display: true, 
          color: 'rgba(255, 255, 255, 0.2)',
          borderColor: 'rgba(255, 255, 255, 0.3)'
        }
      },
      y: {
        title: { display: true, text: getYAxisLabel(faultType, 'time'), color: 'rgba(255, 255, 255, 0.9)' },
        ticks: { color: 'rgba(255, 255, 255, 0.8)' },
        grid: { 
          display: true, 
          color: 'rgba(255, 255, 255, 0.15)',
          borderColor: 'rgba(255, 255, 255, 0.3)'
        }
      }
    },
    plugins: { 
      ...baseChartOptions.plugins, 
      title: { display: true, text: '时域波形', color: 'rgba(255, 255, 255, 0.9)' },
      legend: { 
        position: 'top',
        labels: { color: 'rgba(255, 255, 255, 0.9)' }
      }
    }
  };

  // 为绝缘故障类型添加双Y轴支持
  if (faultType.type === 'insulation') {
    baseConfig.scales.y1 = {
      type: 'linear',
      display: true,
      position: 'right',
      title: { display: true, text: '泄漏电流 (mA)', color: 'rgba(255, 255, 255, 0.9)' },
      ticks: { color: 'rgba(255, 255, 255, 0.8)' },
      grid: { 
        drawOnChartArea: false,
        color: 'rgba(255, 255, 255, 0.15)',
        borderColor: 'rgba(255, 255, 255, 0.3)'
      }
    };
  }

  return baseConfig;
};

const getSecondChartOptions = (faultType) => ({
  ...baseChartOptions,
  scales: {
    x: { 
      title: { 
        display: true, 
        text: faultType.type === 'turn_fault' ? '频率 (Hz)' : '时间',
        color: 'rgba(255, 255, 255, 0.9)'
      },
      ticks: { color: 'rgba(255, 255, 255, 0.8)' },
      grid: { 
        display: true, 
        color: 'rgba(255, 255, 255, 0.2)',
        borderColor: 'rgba(255, 255, 255, 0.3)'
      }
    },
    y: { 
      title: { 
        display: true, 
        text: getYAxisLabel(faultType, 'second'),
        color: 'rgba(255, 255, 255, 0.9)'
      },
      ticks: { color: 'rgba(255, 255, 255, 0.8)' },
      beginAtZero: true,
      grid: { 
        display: true, 
        color: 'rgba(255, 255, 255, 0.15)',
        borderColor: 'rgba(255, 255, 255, 0.3)'
      }
    }
  },
  plugins: { 
    ...baseChartOptions.plugins, 
    title: { 
      display: true, 
      text: faultType.type === 'turn_fault' ? '频谱分析' : '特征趋势',
      color: 'rgba(255, 255, 255, 0.9)'
    },
    legend: { 
      position: 'top',
      labels: { color: 'rgba(255, 255, 255, 0.9)' }
    }
  }
});

const getHistoryChartOptions = (faultType) => ({
  ...baseChartOptions,
  scales: {
    x: { 
      title: { display: true, text: '时间', color: 'rgba(255, 255, 255, 0.9)' },
      ticks: { 
        color: 'rgba(255, 255, 255, 0.8)',
        maxTicksLimit: 8,
        callback: function(value, index, values) {
          // 只显示时间部分，不显示日期
          const label = this.getLabelForValue(value);
          if (label) {
            const parts = label.split(' ');
            return parts.length > 1 ? parts[1] : label; // 返回时间部分
          }
          return label;
        }
      },
      grid: { 
        display: true, 
        color: 'rgba(255, 255, 255, 0.2)', // 白色网格线，在蓝色背景下清晰可见
        borderColor: 'rgba(255, 255, 255, 0.3)'
      }
    },
    y: { 
      title: { display: true, text: '故障评分', color: 'rgba(255, 255, 255, 0.9)' }, 
      min: 0, 
      max: 1,
      ticks: { color: 'rgba(255, 255, 255, 0.8)' },
      grid: { 
        display: true, 
        color: 'rgba(255, 255, 255, 0.15)',
        borderColor: 'rgba(255, 255, 255, 0.3)'
      }
    }
  },
  plugins: { 
    ...baseChartOptions.plugins, 
    title: { display: true, text: '历史故障评分', color: 'rgba(255, 255, 255, 0.9)' },
    legend: { 
      position: 'top',
      labels: { color: 'rgba(255, 255, 255, 0.9)' }
    }
  }
});

const getYAxisLabel = (faultType, chartType) => {
  const labels = {
    turn_fault: { time: '电流 (A)', second: '幅值' },
    insulation: { time: '绝缘电阻 (MΩ)', second: '指标值 (%)' },
    bearing: { time: '幅值', second: '指标值' },
    eccentricity: { time: '电流 (A)', second: '指标值 (%)' },
    broken_bar: { time: '电流 (A)', second: '指标值 (%)' }
  };
  return labels[faultType.type]?.[chartType] || '数值';
};

const getSecondChartData = (faultData, faultType) => {
  if (!faultData) return null;
  
  if (faultType === 'turn_fault') {
    // 检查是否有频谱数据
    if (faultData.spectrum && faultData.spectrum.labels && faultData.spectrum.labels.length > 0) {
      return faultData.spectrum;
    }
  }
  
  // 对于非turn_fault类型，或者turn_fault没有频谱数据时，返回特征趋势
  if (faultData.featureTrend && faultData.featureTrend.labels && faultData.featureTrend.labels.length > 0) {
    return faultData.featureTrend;
  }
  
  return null;
};

// 注释：前端模拟数据生成逻辑已移至后端
// 现在前端专注于数据接收和图表渲染

// 从spectrum字段重建频谱图表
const rebuildSpectrumFromSpectrum = (vehicleData, latestData) => {
  if (!latestData.spectrum || !latestData.spectrum.labels) {
    return;
  }
  
  try {
    // 直接使用现有的spectrum数据
    vehicleData.spectrum = {
      labels: latestData.spectrum.labels,
      datasets: latestData.spectrum.datasets || []
    };
    // console.log(`✅ 频谱图表已构建: ${latestData.spectrum.labels.length}个频率点, ${latestData.spectrum.datasets?.length || 0}个数据集`);
  } catch (error) {
    console.error('从spectrum重建频谱图表时出错:', error);
  }
};

// 从最新数据构建特征趋势（当没有历史数据时）
const rebuildFeatureTrendFromLatest = (vehicleData, latestData, faultConfig) => {
  if (!latestData.features || !faultConfig.features) return;
  
  try {
    const currentTime = formatToBeijingTimeOnly(latestData.timestamp);
    const datasets = faultConfig.features.map((feature, index) => {
      const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399'];
      const value = latestData.features[feature.key];
      
      if (value === undefined || value === null) return null;
      
      // 智能百分比处理
      let processedValue = value;
      if (feature.unit === '%') {
        if (value <= 1 && value >= 0) {
          processedValue = value * 100;
        } else if (value > 1000) {
          processedValue = value / 100;
        }
        processedValue = Math.max(0, Math.min(processedValue, 9999.99));
        processedValue = parseFloat(processedValue.toFixed(2));
      }
      
      return {
        label: `${feature.name} ${feature.unit ? `(${feature.unit})` : ''}`,
        data: [processedValue], // 只有一个数据点
        borderColor: colors[index % colors.length],
        borderWidth: 2,
        pointRadius: 4,
        fill: false
      };
    }).filter(ds => ds !== null);
    
    if (datasets.length > 0) {
      vehicleData.featureTrend = {
        labels: [currentTime], // 只有一个时间点
        datasets: datasets
      };
      // console.log(`✅ 特征趋势图表已构建（单点）: ${datasets.length}个特征`);
    }
  } catch (error) {
    console.error('从最新数据构建特征趋势时出错:', error);
  }
};

// 获取历史数据的日期范围
const getHistoryDateRange = (historyData) => {
  if (!historyData || historyData.length === 0) return '';
  
  if (historyData.length === 1) {
    return formatToBeijingDateOnly(historyData[0].timestamp);
  }
  
  const firstDate = formatToBeijingDateOnly(historyData[0].timestamp);
  const lastDate = formatToBeijingDateOnly(historyData[historyData.length - 1].timestamp);
  
  if (firstDate === lastDate) {
    return firstDate;
  } else {
    return `${firstDate} - ${lastDate}`;
  }
};

// 操作函数
const startMonitoring = async () => {
  try {
    connectionStatus.value = 'connecting';
    await globalWebSocketManager.connect();
    
    connectionStatus.value = 'connected';
    connectionStartTime.value = Date.now();
    
    ElMessage.success(`开始监控车辆 ${getVehicleName(vehicleId.value)}`);
    
  } catch (error) {
    connectionStatus.value = 'error';
    ElMessage.error('连接失败: ' + error.message);
    console.error('WebSocket连接错误:', error);
  }
};

const goBack = () => {
  router.push({ name: 'FleetDistributedMonitor' });
};

const scrollToFaultSection = (faultType) => {
  const element = faultSectionRefs[faultType];
  if (element) {
    element.scrollIntoView({ behavior: 'smooth' });
    // 自动展开该部分
    if (!expandedSections.value.has(faultType)) {
      expandedSections.value.add(faultType);
    }
  }
};

const toggleSectionExpand = (faultType) => {
  if (expandedSections.value.has(faultType)) {
    expandedSections.value.delete(faultType);
  } else {
    expandedSections.value.add(faultType);
  }
};

const exportFaultData = (faultType) => {
  const data = vehicleData.value[faultType];
  if (data && data.history && data.history.length > 0) {
    const dataStr = JSON.stringify(data.history, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${vehicleId.value}_${faultType}_data.json`;
    a.click();
    URL.revokeObjectURL(url);
    ElMessage.success(`${faultType}数据已导出`);
  } else {
    ElMessage.warning('暂无数据可导出');
  }
};

onMounted(() => {
  
  // 注册WebSocket消息处理器
  globalWebSocketManager.on('message', handleRealtimeMessage);
  
  // 注册连接状态监听器
  globalWebSocketManager.on('open', () => {
    connectionStatus.value = 'connected';
  });
  
  globalWebSocketManager.on('close', () => {
    connectionStatus.value = 'disconnected';
  });
  
  globalWebSocketManager.on('error', () => {
    connectionStatus.value = 'error';
  });
  
  // 如果全局WebSocket已连接，直接使用
  if (globalWebSocketManager.getIsConnected()) {
    connectionStatus.value = 'connected';
    connectionStartTime.value = Date.now();
  }
});

onUnmounted(() => {
  try {
    // 移除WebSocket事件监听器
    if (globalWebSocketManager && typeof globalWebSocketManager.off === 'function') {
      globalWebSocketManager.off('message', handleRealtimeMessage);
    }
  } catch (error) {
    console.error('车辆详情页面卸载时出错:', error);
  }
});
</script>

<style scoped>
.vehicle-detail-view {
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: calc(100vh - 60px);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  padding: 25px 30px;
  margin-bottom: 25px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.back-button {
  margin-bottom: 15px;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  font-weight: 600;
}

.vehicle-title {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 10px;
}

.vehicle-icon {
  font-size: 32px;
}

.vehicle-title h2 {
  margin: 0;
  color: white;
  font-size: 28px;
  font-weight: 600;
}

.vehicle-meta {
  display: flex;
  gap: 20px;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
}

.header-right {
  display: flex;
  gap: 20px;
  align-items: center;
}

.health-score .score-circle {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.score-value {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 5px;
}

.score-label {
  font-size: 12px;
  color: #666;
}

.connection-status {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
}

.status-overview {
  margin-bottom: 30px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.fault-overview-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  cursor: pointer;
  transition: all 0.3s ease;
}

.fault-overview-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  background: rgba(255, 255, 255, 0.15);
}

.fault-overview-card.fault-normal {
  border-left: 4px solid #67c23a;
}

.fault-overview-card.fault-warning {
  border-left: 4px solid #e6a23c;
}

.fault-overview-card.fault-danger {
  border-left: 4px solid #f56c6c;
}

.fault-header {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}

.fault-icon {
  font-size: 24px;
}

.fault-info {
  flex: 1;
}

.fault-name {
  color: white;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 5px;
}

.fault-score {
  text-align: center;
  margin-bottom: 15px;
}

.score-number {
  font-size: 32px;
  font-weight: bold;
}

.fault-features {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.feature-mini {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  padding: 5px 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  min-width: 80px;
}

.feature-mini-name {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 3px;
}

.feature-mini-value {
  font-size: 12px;
  font-weight: bold;
  color: white;
}

.fault-details-container {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.fault-detail-section {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  padding: 25px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.section-header h3 {
  margin: 0;
  color: white;
  font-size: 20px;
  font-weight: 600;
}

.section-actions {
  display: flex;
  gap: 10px;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 25px;
  margin-top: 20px;
}

/* 确保历史趋势图表占据足够空间 */
.history-chart-container {
  min-height: 480px;
}

.chart-container {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 15px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.chart-header h4 {
  margin: 0;
  color: white;
  font-size: 14px;
  font-weight: 600;
}

.chart-info {
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
}

.chart-content {
  height: 300px;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 历史趋势图表特殊样式 */
.history-chart-container .chart-content {
  height: 380px;
}

.chart-date-info {
  padding: 12px 15px;
  text-align: center;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  border-radius: 0 0 10px 10px;
  margin-top: 5px;
}

.chart-date {
  color: rgba(255, 255, 255, 0.8);
  font-size: 12px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: rgba(255, 255, 255, 0.6);
}

.placeholder-icon {
  font-size: 48px;
}

.placeholder-text {
  font-size: 14px;
}

.waiting-message {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

/* 调试面板样式 */
.debug-panel {
  margin-top: 30px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.debug-content {
  padding: 15px;
  color: rgba(255, 255, 255, 0.9);
}

.debug-section {
  margin-bottom: 20px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
}

.debug-section h4, .debug-section h5 {
  margin: 0 0 10px 0;
  color: white;
  font-weight: 600;
}

.debug-section p {
  margin: 5px 0;
  font-size: 14px;
}

.debug-data {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

.features-debug {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.feature-debug {
  background: rgba(64, 158, 255, 0.2);
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  border: 1px solid rgba(64, 158, 255, 0.3);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
  
  .history-chart-container .chart-content {
    height: 350px;
  }
  
  .history-chart-container {
    min-height: 420px;
  }
}

@media (max-width: 768px) {
  .detail-header {
    flex-direction: column;
    gap: 20px;
    align-items: stretch;
  }
  
  .header-right {
    flex-direction: row;
    justify-content: space-between;
  }
  
  .overview-grid {
    grid-template-columns: 1fr;
  }
  
  .vehicle-meta {
    flex-direction: column;
    gap: 10px;
  }
  
  .debug-data {
    grid-template-columns: 1fr;
  }
}
</style> 