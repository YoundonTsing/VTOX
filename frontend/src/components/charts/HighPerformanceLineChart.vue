<template>
  <div class="high-performance-chart-container" :style="{ height: `${height}px` }">
    <canvas 
      :id="chartId" 
      ref="canvasRef"
      :width="canvasWidth"
      :height="canvasHeight"
    ></canvas>
    <div v-if="!hasData" class="no-data-overlay">
      <p>暂无数据</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import Chart from 'chart.js/auto'

const props = defineProps({
  chartData: {
    type: Object,
    required: false,
    default: () => null
  },
  chartId: {
    type: String,
    required: true
  },
  height: {
    type: Number,
    default: 300
  },
  options: {
    type: Object,
    default: () => ({})
  },
  updateMode: {
    type: String,
    default: 'incremental', // 'incremental' | 'replace'
    validator: (value) => ['incremental', 'replace'].includes(value)
  },
  maxDataPoints: {
    type: Number,
    default: 100 // 限制最大数据点数
  },
  samplingRate: {
    type: Number,
    default: 1 // 采样率，1=不采样，2=每2个点取1个
  }
})

const canvasRef = ref(null)
const chart = ref(null)
const canvasWidth = ref(800)
const canvasHeight = ref(400)
const isUpdating = ref(false)
const dataBuffer = ref([]) // 数据缓冲区
const updateQueue = ref([]) // 更新队列

// 计算属性：判断是否有数据
const hasData = computed(() => {
  return props.chartData && 
         props.chartData.datasets && 
         props.chartData.datasets.length > 0 &&
         props.chartData.datasets.some(ds => ds.data && ds.data.length > 0)
})

// 防抖更新函数 - 100ms内的多次更新合并为一次
let updateTimer = null
const debouncedUpdate = (updateFn) => {
  if (updateTimer) {
    clearTimeout(updateTimer)
  }
  updateTimer = setTimeout(() => {
    if (!isUpdating.value) {
      updateFn()
    }
  }, 100)
}

// 数据采样函数 - 减少数据点数量
const sampleData = (data, rate = 1) => {
  if (rate <= 1 || !Array.isArray(data)) return data
  
  const sampled = []
  for (let i = 0; i < data.length; i += rate) {
    sampled.push(data[i])
  }
  return sampled
}

// 数据压缩函数 - 限制数据点数量
const compressData = (chartData) => {
  if (!chartData || !chartData.datasets) return chartData
  
  const compressed = {
    ...chartData,
    datasets: chartData.datasets.map(dataset => {
      if (!dataset.data || dataset.data.length <= props.maxDataPoints) {
        return dataset
      }
      
      // 采样数据
      const sampledData = sampleData(dataset.data, props.samplingRate)
      
      // 如果采样后仍超过限制，进一步压缩
      let finalData = sampledData
      if (sampledData.length > props.maxDataPoints) {
        const step = Math.ceil(sampledData.length / props.maxDataPoints)
        finalData = sampleData(sampledData, step)
      }
      
      return {
        ...dataset,
        data: finalData
      }
    })
  }
  
  // 同步压缩标签
  if (compressed.labels && compressed.labels.length > compressed.datasets[0]?.data?.length) {
    const targetLength = compressed.datasets[0]?.data?.length || 0
    if (targetLength > 0) {
      const step = Math.ceil(compressed.labels.length / targetLength)
      compressed.labels = sampleData(compressed.labels, step).slice(0, targetLength)
    }
  }
  
  return compressed
}

// 高性能图表创建
const createChart = async () => {
  if (!props.chartData || !canvasRef.value) return
  
  await nextTick()
  
  try {
    // 销毁旧图表
    if (chart.value) {
      chart.value.destroy()
      chart.value = null
    }
    
    const ctx = canvasRef.value.getContext('2d')
    if (!ctx) return
    
    // 压缩数据
    const optimizedData = compressData(props.chartData)
    
    // 优化的默认配置
    const optimizedOptions = {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 0 // 禁用动画提升性能
      },
      elements: {
        point: {
          radius: 0, // 隐藏数据点减少渲染负担
          hoverRadius: 3
        },
        line: {
          tension: 0 // 直线连接，减少计算
        }
      },
      scales: {
        x: {
          type: 'category',
          ticks: {
            maxTicksLimit: 10, // 限制X轴标签数量
            autoSkip: true,
            autoSkipPadding: 10
          }
        },
        y: {
          type: 'linear',
          ticks: {
            maxTicksLimit: 8 // 限制Y轴标签数量
          }
        }
      },
      plugins: {
        legend: {
          display: true
        },
        tooltip: {
          enabled: true,
          mode: 'nearest',
          intersect: false,
          animation: {
            duration: 0
          }
        }
      },
      ...props.options
    }
    
    // 创建图表
    chart.value = new Chart(ctx, {
      type: 'line',
      data: optimizedData,
      options: optimizedOptions
    })
    
    // 缓存最新数据
    dataBuffer.value = optimizedData
    
  } catch (error) {
    console.error('高性能图表创建失败:', error)
  }
}

// 增量更新图表数据
const updateChartIncremental = async () => {
  if (!chart.value || !props.chartData || isUpdating.value) return
  
  isUpdating.value = true
  
  try {
    // 压缩新数据
    const newData = compressData(props.chartData)
    
    // 检查数据是否真的发生了变化
    const hasChanged = JSON.stringify(newData) !== JSON.stringify(dataBuffer.value)
    if (!hasChanged) {
      isUpdating.value = false
      return
    }
    
    // 更新图表数据
    chart.value.data = newData
    
    // 使用最小重绘模式
    chart.value.update('none') // 'none' 模式最快，无动画
    
    // 更新缓存
    dataBuffer.value = newData
    
  } catch (error) {
    console.error('增量更新图表失败:', error)
    // 发生错误时回退到重建模式
    await createChart()
  } finally {
    isUpdating.value = false
  }
}

// 画布尺寸更新
const updateCanvasSize = () => {
  if (!canvasRef.value) return
  
  const container = canvasRef.value.parentElement
  if (container) {
    const rect = container.getBoundingClientRect()
    canvasWidth.value = Math.floor(rect.width)
    canvasHeight.value = Math.floor(rect.height)
  }
}

// Resize处理器
let resizeObserver = null
const handleResize = () => {
  debouncedUpdate(() => {
    updateCanvasSize()
    if (chart.value) {
      chart.value.resize()
    }
  })
}

// 监听数据变化
watch(() => props.chartData, (newData) => {
  if (!newData) return
  
  if (props.updateMode === 'incremental' && chart.value) {
    debouncedUpdate(updateChartIncremental)
  } else {
    debouncedUpdate(createChart)
  }
}, { deep: false }) // 浅层监听，减少性能开销

// 监听配置变化
watch(() => props.options, () => {
  debouncedUpdate(createChart)
}, { deep: false })

// 组件挂载
onMounted(async () => {
  await nextTick()
  updateCanvasSize()
  
  // 设置resize监听
  if (window.ResizeObserver) {
    resizeObserver = new ResizeObserver(handleResize)
    if (canvasRef.value?.parentElement) {
      resizeObserver.observe(canvasRef.value.parentElement)
    }
  } else {
    window.addEventListener('resize', handleResize)
  }
  
  if (hasData.value) {
    await createChart()
  }
})

// 组件卸载 - 完整清理
onUnmounted(() => {
  // 清理定时器
  if (updateTimer) {
    clearTimeout(updateTimer)
    updateTimer = null
  }
  
  // 清理Resize监听
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  } else {
    window.removeEventListener('resize', handleResize)
  }
  
  // 销毁图表
  if (chart.value) {
    chart.value.destroy()
    chart.value = null
  }
  
  // 清理数据缓存
  dataBuffer.value = []
  updateQueue.value = []
  
  isUpdating.value = false
})

// 暴露API给父组件
defineExpose({
  refreshChart: createChart,
  getChart: () => chart.value,
  isUpdating: () => isUpdating.value
})
</script>

<style scoped>
.high-performance-chart-container {
  position: relative;
  width: 100%;
  min-height: 300px;
  overflow: hidden;
}

.no-data-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: rgba(245, 247, 250, 0.8);
  z-index: 10;
}

.no-data-overlay p {
  color: #909399;
  font-size: 14px;
  margin: 0;
}
</style> 