<template>
  <div class="time-series-container">
    <div class="chart-header">
      <h3>{{ chartTitle }}</h3>
      <div class="chart-controls">
        <el-select v-model="selectedFeatures" multiple collapse-tags placeholder="选择特征">
          <el-option
            v-for="feature in filteredFeatures"
            :key="feature.key"
            :label="feature.label"
            :value="feature.key"
          />
        </el-select>
      </div>
    </div>
    <div :id="chartId" class="chart"></div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, computed, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: {
    type: Array,
    required: true
  },
  timestamps: {
    type: Array,
    required: true
  },
  chartType: {
    type: String,
    default: 'insulation'  // 'insulation' 或 'temperature' 或 'efficiency'
  },
  chartId: {
    type: String,
    default: () => `chart-${Date.now()}-${Math.floor(Math.random() * 1000)}`
  }
})

// 可用特征列表
const availableFeatures = ref([
  // 匝间短路特征
  { key: 'I2_avg', label: '负序电流', group: 'turn-to-turn' },
  { key: 'I2_I1_ratio', label: '负序/正序比值', group: 'turn-to-turn' },
  { key: 'unbalance_avg', label: '电流不平衡度', group: 'turn-to-turn' },
  { key: 'kurtosis_delta_iq', label: 'ΔI_q峭度', group: 'turn-to-turn' },
  { key: 'delta_eta_avg', label: '效率残差', group: 'turn-to-turn' },
  
  // 绝缘诊断特征
  { key: 'temp_ratio', label: '绕组温度比率', group: 'insulation' },
  { key: 'temp_rise_rate', label: '温升速率', group: 'insulation' },
  { key: 'thermal_residual', label: '温度残差', group: 'insulation' },
  { key: 'efficiency_residual', label: '效率残差', group: 'insulation' },
  { key: 'current_residual_trend', label: '电流残差趋势', group: 'insulation' },
  { key: 'thermal_aging', label: '热老化累积', group: 'insulation' }
])

// 默认选择的特征
const selectedFeatures = ref(getDefaultFeatures())

// 计算属性：根据图表类型获取标题
const chartTitle = computed(() => {
  switch (props.chartType) {
    case 'temperature':
      return '温度特征时序变化'
    case 'efficiency':
      return '效率与电流特征时序变化'
    case 'turn-to-turn':
      return '匝间短路特征时序变化'
    default:
      return '特征参数时序变化'
  }
})

// 计算属性：根据图表类型筛选可用特征
const filteredFeatures = computed(() => {
  if (props.chartType === 'temperature') {
    return availableFeatures.value.filter(feature => 
      ['temp_ratio', 'temp_rise_rate', 'thermal_residual'].includes(feature.key)
    )
  } else if (props.chartType === 'efficiency') {
    return availableFeatures.value.filter(feature => 
      ['efficiency_residual', 'current_residual_trend', 'thermal_aging'].includes(feature.key)
    )
  } else if (props.chartType === 'turn-to-turn') {
    return availableFeatures.value.filter(feature => 
      ['I2_avg', 'I2_I1_ratio', 'unbalance_avg', 'kurtosis_delta_iq', 'delta_eta_avg'].includes(feature.key)
    )
  } else {
    return availableFeatures.value.filter(feature => feature.group === 'insulation')
  }
})

// 根据图表类型获取默认特征
function getDefaultFeatures() {
  switch (props.chartType) {
    case 'temperature':
      return ['temp_ratio', 'temp_rise_rate', 'thermal_residual']
    case 'efficiency':
      return ['efficiency_residual', 'current_residual_trend', 'thermal_aging']
    case 'turn-to-turn':
      return ['I2_avg', 'unbalance_avg', 'kurtosis_delta_iq']
    default:
      return ['temp_ratio', 'temp_rise_rate', 'thermal_residual']
  }
}

// 图表实例
let chartInstance = null
let resizeHandler = null // 添加resize handler引用

// 更新图表
const updateChart = () => {
  // 移除频繁的控制台日志以减少内存占用
  // console.log('Updating chart', props.chartId, 'with data length:', props.data?.length, 'timestamps:', props.timestamps?.length)
  
  if (!props.data || !props.timestamps || props.data.length === 0) {
    // console.warn('No data or timestamps for chart', props.chartId)
    return
  }
  
  const chartDom = document.getElementById(props.chartId)
  if (!chartDom) {
    console.error('Chart DOM element not found:', props.chartId)
    return
  }
  
  // 如果已经初始化过，销毁旧实例
  if (chartInstance) {
    try {
      chartInstance.dispose()
    } catch (e) {
      console.warn('Failed to dispose chart:', e)
    }
    chartInstance = null
  }
  
  // console.log('Initializing chart', props.chartId)
  // 初始化图表
  try {
    chartInstance = echarts.init(chartDom)
    
    // 格式化时间戳 - 优化性能
    const formattedDates = props.timestamps.map(timestamp => {
      try {
        if (timestamp instanceof Date) {
          return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
        return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      } catch (e) {
        return '无效时间'
      }
    })
    
    // 处理要显示的系列数据
    const seriesData = []
    
    // 特征颜色映射
    const colorMap = {
      // 匝间短路特征颜色
      I2_avg: '#5470c6',
      I2_I1_ratio: '#91cc75',
      unbalance_avg: '#fac858',
      kurtosis_delta_iq: '#ee6666',
      delta_eta_avg: '#73c0de',
      
      // 绝缘诊断特征颜色
      temp_ratio: '#5470c6',
      temp_rise_rate: '#91cc75',
      thermal_residual: '#fac858',
      efficiency_residual: '#ee6666',
      current_residual_trend: '#73c0de',
      thermal_aging: '#3ba272'
    }
    
    // 特征值范围映射
    const featureRanges = {
      // 匝间短路特征范围
      I2_avg: [0, 0.2],
      I2_I1_ratio: [0, 0.1],
      unbalance_avg: [0, 20],
      kurtosis_delta_iq: [0, 10],
      delta_eta_avg: [-0.05, 0.01],
      
      // 绝缘诊断特征范围
      temp_ratio: [0.8, 1.5],
      temp_rise_rate: [0, 5],
      thermal_residual: [0, 20],
      efficiency_residual: [-0.05, 0.01],
      current_residual_trend: [0, 0.02],
      thermal_aging: [0, 500]
    }
    
    // 为每个选择的特征创建系列
    selectedFeatures.value.forEach(feature => {
      const featureName = availableFeatures.value.find(f => f.key === feature)?.label || feature
      
      // 提取该特征的数据
      const featureData = props.data.map(item => {
        // 检查特征是否存在
        if (item && feature in item) {
          let value = item[feature]
          
          // 检查值是否有效
          if (value === null || value === undefined || isNaN(value)) {
            console.warn(`Invalid value for feature ${feature}:`, value)
            return null
          }
          
          // 对效率残差（通常为负值）进行特殊处理
          if ((feature === 'delta_eta_avg' || feature === 'efficiency_residual') && value < 0) {
            value = -value  // 取绝对值方便比较趋势
          }
          
          return value
        } else {
          console.warn(`Feature ${feature} not found in data item:`, item)
          return null
        }
      }).filter(value => value !== null)
      
      seriesData.push({
        name: featureName,
        type: 'line',
        smooth: true,
        lineStyle: {
          width: 2,
          color: colorMap[feature] || null
        },
        showSymbol: false,
        data: featureData,
        // 为每个系列设置单独的Y轴
        yAxisIndex: 0,
        // 处理数据中的null值
        connectNulls: true
      })
    })
    
    // 计算Y轴的最小值和最大值
    let yAxisMin = Infinity
    let yAxisMax = -Infinity
    
    // 如果只选择了一个特征，使用预定义的范围
    if (selectedFeatures.value.length === 1) {
      const feature = selectedFeatures.value[0]
      const range = featureRanges[feature]
      if (range) {
        yAxisMin = range[0]
        yAxisMax = range[1]
      } else {
        // 如果没有预定义范围，自动计算
        calculateAxisRange()
      }
    } else {
      // 对于多个特征，自动计算合适的范围
      calculateAxisRange()
    }
    
    // 辅助函数：计算轴范围
    function calculateAxisRange() {
      // 收集所有有效数据点
      const allValues = []
      
      selectedFeatures.value.forEach(feature => {
        props.data.forEach(item => {
          if (item && feature in item && item[feature] !== null && item[feature] !== undefined && !isNaN(item[feature])) {
            allValues.push(item[feature])
          }
        })
      })
      
      if (allValues.length > 0) {
        yAxisMin = Math.min(...allValues)
        yAxisMax = Math.max(...allValues)
        
        // 为范围添加一些边距
        const padding = Math.max(0.1, (yAxisMax - yAxisMin) * 0.1)
        yAxisMin = Math.max(0, yAxisMin - padding)
        yAxisMax = yAxisMax + padding
        
        // 确保最小值和最大值不同
        if (yAxisMin === yAxisMax) {
          yAxisMin = Math.max(0, yAxisMin - 0.1)
          yAxisMax = yAxisMax + 0.1
        }
      } else {
        // 如果没有有效数据，使用默认范围
        yAxisMin = 0
        yAxisMax = 10
      }
    }
    
    // 图表配置项
    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#6a7985'
          }
        }
      },
      legend: {
        data: selectedFeatures.value.map(feature => {
          return availableFeatures.value.find(f => f.key === feature)?.label || feature
        })
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: [
        {
          type: 'category',
          boundaryGap: false,
          data: formattedDates
        }
      ],
      yAxis: [
        {
          type: 'value',
          splitLine: {
            lineStyle: {
              type: 'dashed'
            }
          },
          scale: true,
          splitNumber: 5,
          axisLabel: {
            formatter: function(value) {
              // 对于小数值，保留适当的小数位数
              if (Math.abs(value) < 0.1) {
                return value.toFixed(3);
              } else if (Math.abs(value) < 1) {
                return value.toFixed(2);
              } else if (Math.abs(value) < 10) {
                return value.toFixed(1);
              } else {
                return value.toFixed(0);
              }
            }
          },
          // 设置Y轴范围，但不设置alignTicks
          min: yAxisMin,
          max: yAxisMax
          // 移除alignTicks设置
        }
      ],
      series: seriesData
    }
    
    // 设置图表配置
    chartInstance.setOption(option)
    // console.log('Chart', props.chartId, 'initialized with options:', option)
    
  } catch (error) {
    console.error('Error initializing chart:', error)
  }
}

// 创建resize handler函数
resizeHandler = () => {
  if (chartInstance) {
    try {
      chartInstance.resize()
    } catch (e) {
      console.warn('Chart resize failed:', e)
    }
  }
}

// 监听选择的特征变化，更新图表
watch(selectedFeatures, () => {
  updateChart()
})

// 监听图表类型变化，更新默认特征
watch(() => props.chartType, (newType) => {
  selectedFeatures.value = getDefaultFeatures()
  updateChart()
})

// 监听数据变化，更新图表 - 添加防抖
const debouncedUpdate = debounce(updateChart, 100)
watch(() => [props.data, props.timestamps], () => {
  debouncedUpdate()
}, { deep: true })

// 添加防抖函数
function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// 组件挂载时初始化图表和事件监听
onMounted(() => {
  setTimeout(updateChart, 100)
  // 添加窗口大小变化监听
  if (resizeHandler) {
    window.addEventListener('resize', resizeHandler)
  }
})

// 组件卸载时清理所有资源
onUnmounted(() => {
  // 清理图表实例
  if (chartInstance) {
    try {
      chartInstance.dispose()
    } catch (e) {
      console.warn('Failed to dispose chart on unmount:', e)
    }
    chartInstance = null
  }
  
  // 清理事件监听器
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
    resizeHandler = null
  }
})
</script>

<style scoped>
.time-series-container {
  margin: 20px 0;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.chart-header h3 {
  margin: 0;
  font-size: 16px;
  color: #606266;
}

.chart-controls {
  display: flex;
  gap: 10px;
}

.chart {
  width: 100%;
  height: 400px;
}
</style> 