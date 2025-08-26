<template>
  <div class="trend-analysis-container">
    <h2 class="page-title">趋势分析</h2>
    <p class="page-description">
      分析各类故障指标的历史趋势变化，帮助预测潜在故障风险。
    </p>

    <!-- 故障类型和时间范围选择 -->
    <div class="filter-section">
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="filter-item">
            <span class="filter-label">故障类型:</span>
            <el-select v-model="selectedFaultType" placeholder="选择故障类型" style="width: 100%">
              <el-option
                v-for="fault in faultTypes"
                :key="fault.type"
                :label="fault.name"
                :value="fault.type"
              />
            </el-select>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="filter-item">
            <span class="filter-label">指标选择:</span>
            <el-select 
              v-model="selectedFeatures" 
              multiple 
              collapse-tags 
              placeholder="选择指标" 
              style="width: 100%"
            >
              <el-option
                v-for="feature in availableFeatures"
                :key="feature.key"
                :label="feature.name"
                :value="feature.key"
              />
            </el-select>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="filter-item">
            <span class="filter-label">时间范围:</span>
            <el-date-picker
              v-model="timeRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              style="width: 100%"
            />
          </div>
        </el-col>
      </el-row>
      <div class="filter-actions">
        <el-button type="primary" @click="applyFilters">应用筛选</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>
    </div>

    <!-- 趋势图表 -->
    <div class="chart-section">
      <el-card v-if="isLoading" class="loading-card">
        <div class="loading-container">
          <el-skeleton :rows="10" animated />
        </div>
      </el-card>
      
      <el-card v-else-if="!hasData" class="empty-card">
        <div class="empty-container">
          <el-empty description="暂无趋势数据，请选择故障类型和时间范围" />
        </div>
      </el-card>
      
      <el-card v-else class="chart-card">
        <div class="chart-header">
          <h3>{{ getFaultTypeName(selectedFaultType) }}趋势分析</h3>
          <div class="chart-actions">
            <el-button type="primary" size="small" @click="exportChart">
              导出图表
            </el-button>
            <el-button size="small" @click="refreshData">
              刷新数据
            </el-button>
          </div>
        </div>
        <div class="chart-wrapper">
          <line-chart
            v-if="trendData && trendData.labels && trendData.labels.length > 0"
            :chart-data="trendData"
            chart-id="trend-analysis-chart"
            :height="500"
            :options="chartOptions"
          />
        </div>
      </el-card>
    </div>

    <!-- 数据统计表格 -->
    <el-card v-if="hasData" class="stats-card">
      <template #header>
        <div class="stats-header">
          <h3>数据统计</h3>
          <el-button type="primary" link @click="exportData">导出数据</el-button>
        </div>
      </template>
      <el-table :data="statsData" border style="width: 100%">
        <el-table-column prop="feature" label="指标名称" width="180" />
        <el-table-column prop="min" label="最小值" />
        <el-table-column prop="max" label="最大值" />
        <el-table-column prop="avg" label="平均值" />
        <el-table-column prop="current" label="当前值" />
        <el-table-column prop="trend" label="趋势">
          <template #default="scope">
            <el-tag :type="getTrendType(scope.row.trend)">
              {{ getTrendText(scope.row.trend) }}
              <el-icon v-if="scope.row.trend === 'up'"><arrow-up /></el-icon>
              <el-icon v-else-if="scope.row.trend === 'down'"><arrow-down /></el-icon>
              <el-icon v-else><minus /></el-icon>
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 相关性分析 -->
    <el-card v-if="hasData && selectedFeatures.length > 1" class="correlation-card">
      <template #header>
        <div class="correlation-header">
          <h3>指标相关性分析</h3>
        </div>
      </template>
      <div class="correlation-chart">
        <el-table :data="correlationData" border style="width: 100%">
          <el-table-column prop="feature1" label="指标1" width="180" />
          <el-table-column prop="feature2" label="指标2" width="180" />
          <el-table-column prop="correlation" label="相关系数" />
          <el-table-column prop="strength" label="相关性强度">
            <template #default="scope">
              <el-tag :type="getCorrelationType(scope.row.correlation)">
                {{ getCorrelationText(scope.row.correlation) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { ElMessage } from 'element-plus';
import { ArrowUp, ArrowDown, Minus } from '@element-plus/icons-vue';
import LineChart from '@/components/charts/LineChart.vue';

// 故障类型定义
const faultTypes = [
  { 
    type: 'turn_fault', 
    name: '匝间短路故障',
    features: [
      { key: 'current_imbalance', name: '电流不平衡度', unit: '%' },
      { key: 'negative_sequence_ratio', name: '负序分量比例', unit: '%' },
      { key: 'third_harmonic_ratio', name: '三次谐波比例', unit: '%' },
      { key: 'fault_score', name: '故障评分', unit: '%' }
    ]
  },
  { 
    type: 'broken_bar', 
    name: '断条故障',
    features: [
      { key: 'sideband_ratio', name: '边带幅值比', unit: '%' },
      { key: 'normalized_fault_index', name: '归一化故障指数', unit: '%' },
      { key: 'broken_bar_count', name: '估计断条数', unit: '' },
      { key: 'fault_score', name: '故障评分', unit: '%' }
    ]
  },
  { 
    type: 'insulation', 
    name: '绝缘失效',
    features: [
      { key: 'insulation_resistance', name: '绝缘电阻', unit: 'MΩ' },
      { key: 'leakage_current', name: '泄漏电流', unit: 'mA' },
      { key: 'dielectric_loss', name: '介质损耗', unit: '%' },
      { key: 'fault_score', name: '故障评分', unit: '%' }
    ]
  },
  { 
    type: 'bearing', 
    name: '轴承故障',
    features: [
      { key: 'crest_factor', name: '冲击因子', unit: '' },
      { key: 'kurtosis', name: '峭度', unit: '' },
      { key: 'bearing_characteristic_frequency', name: '特征频率', unit: 'Hz' },
      { key: 'fault_score', name: '故障评分', unit: '%' }
    ]
  },
  { 
    type: 'eccentricity', 
    name: '偏心故障',
    features: [
      { key: 'static_ecc_ratio', name: '静态偏心率', unit: '%' },
      { key: 'dynamic_ecc_ratio', name: '动态偏心率', unit: '%' },
      { key: 'eccentricity_index', name: '综合指数', unit: '%' },
      { key: 'fault_score', name: '故障评分', unit: '%' }
    ]
  }
];

// 状态变量
const selectedFaultType = ref('turn_fault');
const selectedFeatures = ref(['fault_score']);
const timeRange = ref([new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), new Date()]);
const isLoading = ref(false);
const hasData = ref(false);
const trendData = ref(null);
const statsData = ref([]);
const correlationData = ref([]);

// 计算可用的特征选项
const availableFeatures = computed(() => {
  const faultType = faultTypes.find(f => f.type === selectedFaultType.value);
  return faultType ? faultType.features : [];
});

// 图表配置
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'top' },
    tooltip: { mode: 'index', intersect: false }
  },
  scales: {
    x: { 
      title: { display: true, text: '时间' },
      ticks: { maxTicksLimit: 10 }
    },
    y: { 
      title: { display: true, text: '指标值' },
      beginAtZero: true
    }
  }
};

// 在组件挂载时加载初始数据
onMounted(() => {
  loadTrendData();
});

// 应用筛选条件
const applyFilters = () => {
  if (selectedFeatures.value.length === 0) {
    ElMessage.warning('请至少选择一个指标');
    return;
  }
  
  loadTrendData();
};

// 重置筛选条件
const resetFilters = () => {
  selectedFaultType.value = 'turn_fault';
  selectedFeatures.value = ['fault_score'];
  timeRange.value = [new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), new Date()];
};

// 刷新数据
const refreshData = () => {
  loadTrendData();
};

// 加载趋势数据
const loadTrendData = () => {
  isLoading.value = true;
  hasData.value = false;
  
  // 模拟API请求延迟
  setTimeout(() => {
    try {
      // 生成模拟数据
      const data = generateMockTrendData();
      
      // 设置趋势图表数据
      trendData.value = {
        labels: data.timestamps.map(formatTimestamp),
        datasets: selectedFeatures.value.map(feature => {
          const featureInfo = availableFeatures.value.find(f => f.key === feature);
          const color = getRandomColor(feature);
          return {
            label: featureInfo ? featureInfo.name : feature,
            data: data.values[feature] || [],
            borderColor: color,
            backgroundColor: `${color}33`,
            borderWidth: 2,
            pointRadius: 1,
            fill: false
          };
        })
      };
      
      // 计算统计数据
      statsData.value = calculateStats(data);
      
      // 计算相关性数据
      if (selectedFeatures.value.length > 1) {
        correlationData.value = calculateCorrelations(data);
      } else {
        correlationData.value = [];
      }
      
      hasData.value = true;
      isLoading.value = false;
    } catch (error) {
      console.error('加载趋势数据时出错:', error);
      ElMessage.error('加载趋势数据失败');
      isLoading.value = false;
    }
  }, 1000);
};

// 生成模拟趋势数据
const generateMockTrendData = () => {
  const startDate = timeRange.value[0] || new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
  const endDate = timeRange.value[1] || new Date();
  
  // 计算时间间隔点
  const startTime = startDate.getTime();
  const endTime = endDate.getTime();
  const duration = endTime - startTime;
  const pointCount = 100; // 生成100个数据点
  const interval = duration / pointCount;
  
  // 生成时间戳
  const timestamps = [];
  for (let i = 0; i < pointCount; i++) {
    timestamps.push(new Date(startTime + i * interval).toISOString());
  }
  
  // 为每个选定的特征生成数据
  const values = {};
  selectedFeatures.value.forEach(feature => {
    const featureInfo = availableFeatures.value.find(f => f.key === feature);
    const unit = featureInfo ? featureInfo.unit : '';
    
    // 根据特征类型生成不同的模拟数据
    let baseValue, variance;
    
    if (feature === 'fault_score') {
      baseValue = 0.2; // 故障评分基准值
      variance = 0.1; // 波动范围
    } else if (feature.includes('ratio') || feature.includes('loss') || feature.includes('index')) {
      baseValue = 0.3; // 比率类指标基准值
      variance = 0.15; // 波动范围
    } else if (feature === 'insulation_resistance') {
      baseValue = 100; // 绝缘电阻基准值
      variance = 20; // 波动范围
    } else if (feature === 'leakage_current') {
      baseValue = 2; // 泄漏电流基准值
      variance = 0.5; // 波动范围
    } else if (feature === 'crest_factor') {
      baseValue = 3; // 冲击因子基准值
      variance = 0.8; // 波动范围
    } else if (feature === 'kurtosis') {
      baseValue = 4; // 峭度基准值
      variance = 1; // 波动范围
    } else if (feature === 'bearing_characteristic_frequency') {
      baseValue = 50; // 特征频率基准值
      variance = 10; // 波动范围
    } else if (feature === 'broken_bar_count') {
      baseValue = 1; // 断条数基准值
      variance = 0.5; // 波动范围
    } else {
      baseValue = 0.5; // 默认基准值
      variance = 0.2; // 默认波动范围
    }
    
    // 生成带趋势的随机数据
    const featureValues = [];
    let trend = Math.random() * 0.4 - 0.2; // 随机趋势
    let value = baseValue;
    
    for (let i = 0; i < pointCount; i++) {
      // 添加随机波动和趋势
      value += (Math.random() * 2 - 1) * variance * 0.1 + trend * 0.01;
      
      // 确保值在合理范围内
      if (feature === 'fault_score' || feature.includes('ratio') || feature.includes('loss') || feature.includes('index')) {
        value = Math.max(0, Math.min(1, value)); // 限制在0-1之间
      } else if (feature === 'insulation_resistance') {
        value = Math.max(10, value); // 绝缘电阻不应太低
      } else if (feature === 'broken_bar_count') {
        value = Math.max(0, value);
        if (Math.random() > 0.95) value = Math.floor(value + 1); // 偶尔增加断条数
      } else {
        value = Math.max(0, value); // 确保非负
      }
      
      featureValues.push(value);
    }
    
    values[feature] = featureValues;
  });
  
  return { timestamps, values };
};

// 计算统计数据
const calculateStats = (data) => {
  const stats = [];
  
  selectedFeatures.value.forEach(feature => {
    const values = data.values[feature] || [];
    if (values.length === 0) return;
    
    const featureInfo = availableFeatures.value.find(f => f.key === feature);
    const unit = featureInfo ? featureInfo.unit : '';
    
    const min = Math.min(...values);
    const max = Math.max(...values);
    const sum = values.reduce((a, b) => a + b, 0);
    const avg = sum / values.length;
    const current = values[values.length - 1];
    
    // 确定趋势
    let trend = 'stable';
    if (values.length >= 10) {
      const recentValues = values.slice(-10);
      const recentAvg = recentValues.reduce((a, b) => a + b, 0) / recentValues.length;
      const prevValues = values.slice(-20, -10);
      const prevAvg = prevValues.length > 0 ? prevValues.reduce((a, b) => a + b, 0) / prevValues.length : recentAvg;
      
      const change = (recentAvg - prevAvg) / prevAvg;
      if (change > 0.05) trend = 'up';
      else if (change < -0.05) trend = 'down';
    }
    
    stats.push({
      feature: featureInfo ? featureInfo.name : feature,
      min: formatValue(min, unit),
      max: formatValue(max, unit),
      avg: formatValue(avg, unit),
      current: formatValue(current, unit),
      trend
    });
  });
  
  return stats;
};

// 计算相关性
const calculateCorrelations = (data) => {
  const correlations = [];
  
  for (let i = 0; i < selectedFeatures.value.length; i++) {
    const feature1 = selectedFeatures.value[i];
    const values1 = data.values[feature1] || [];
    const featureInfo1 = availableFeatures.value.find(f => f.key === feature1);
    
    for (let j = i + 1; j < selectedFeatures.value.length; j++) {
      const feature2 = selectedFeatures.value[j];
      const values2 = data.values[feature2] || [];
      const featureInfo2 = availableFeatures.value.find(f => f.key === feature2);
      
      if (values1.length === values2.length && values1.length > 0) {
        const correlation = calculatePearsonCorrelation(values1, values2);
        
        correlations.push({
          feature1: featureInfo1 ? featureInfo1.name : feature1,
          feature2: featureInfo2 ? featureInfo2.name : feature2,
          correlation: correlation.toFixed(4),
          strength: Math.abs(correlation)
        });
      }
    }
  }
  
  return correlations;
};

// 计算皮尔逊相关系数
const calculatePearsonCorrelation = (x, y) => {
  const n = x.length;
  let sumX = 0;
  let sumY = 0;
  let sumXY = 0;
  let sumX2 = 0;
  let sumY2 = 0;
  
  for (let i = 0; i < n; i++) {
    sumX += x[i];
    sumY += y[i];
    sumXY += x[i] * y[i];
    sumX2 += x[i] * x[i];
    sumY2 += y[i] * y[i];
  }
  
  const numerator = n * sumXY - sumX * sumY;
  const denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
  
  if (denominator === 0) return 0;
  return numerator / denominator;
};

// 格式化时间戳
const formatTimestamp = (timestamp) => {
  if (!timestamp) return '';
  try {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  } catch (e) {
    return '';
  }
};

// 格式化数值
const formatValue = (value, unit) => {
  if (value === undefined || value === null) return 'N/A';
  
  if (unit === '%') {
    return (value * 100).toFixed(2) + '%';
  }
  
  if (typeof value === 'number') {
    if (Number.isInteger(value)) {
      return value.toString() + (unit ? ` ${unit}` : '');
    }
    return value.toFixed(2) + (unit ? ` ${unit}` : '');
  }
  
  return value + (unit ? ` ${unit}` : '');
};

// 获取故障类型名称
const getFaultTypeName = (type) => {
  const faultType = faultTypes.find(f => f.type === type);
  return faultType ? faultType.name : '未知故障';
};

// 获取趋势类型（用于Element Plus组件）
const getTrendType = (trend) => {
  const map = { up: 'danger', down: 'success', stable: 'info' };
  return map[trend] || 'info';
};

// 获取趋势文本
const getTrendText = (trend) => {
  const map = { up: '上升', down: '下降', stable: '稳定' };
  return map[trend] || '未知';
};

// 获取相关性类型（用于Element Plus组件）
const getCorrelationType = (correlation) => {
  const absCorr = Math.abs(parseFloat(correlation));
  if (absCorr >= 0.7) return 'danger';
  if (absCorr >= 0.4) return 'warning';
  return 'info';
};

// 获取相关性文本
const getCorrelationText = (correlation) => {
  const absCorr = Math.abs(parseFloat(correlation));
  if (absCorr >= 0.7) return '强相关';
  if (absCorr >= 0.4) return '中等相关';
  return '弱相关';
};

// 根据特征生成随机颜色
const getRandomColor = (seed) => {
  // 使用简单的哈希函数将特征字符串转换为数字
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = seed.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  // 将哈希转换为颜色
  const colors = [
    '#409EFF', // 蓝色
    '#67C23A', // 绿色
    '#E6A23C', // 黄色
    '#F56C6C', // 红色
    '#909399', // 灰色
    '#9B59B6', // 紫色
    '#2ECC71', // 浅绿色
    '#E74C3C', // 橙红色
    '#3498DB', // 天蓝色
    '#1ABC9C'  // 青色
  ];
  
  return colors[Math.abs(hash) % colors.length];
};

// 导出图表
const exportChart = () => {
  ElMessage.success('图表导出功能将在后续版本中实现');
};

// 导出数据
const exportData = () => {
  ElMessage.success('数据导出功能将在后续版本中实现');
};
</script>

<style scoped>
.trend-analysis-container {
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

.filter-section {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.filter-item {
  margin-bottom: 15px;
}

.filter-label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #606266;
}

.filter-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 15px;
  gap: 10px;
}

.chart-section {
  margin-bottom: 20px;
}

.loading-card,
.empty-card {
  min-height: 500px;
}

.loading-container,
.empty-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 500px;
}

.chart-card {
  padding: 0;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #ebeef5;
}

.chart-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.chart-actions {
  display: flex;
  gap: 10px;
}

.chart-wrapper {
  height: 500px;
  padding: 20px;
}

.stats-card,
.correlation-card {
  margin-bottom: 20px;
}

.stats-header,
.correlation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-header h3,
.correlation-header h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.correlation-chart {
  margin-top: 10px;
}
</style> 