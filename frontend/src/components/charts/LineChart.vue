<template>
  <div class="chart-container" :style="{ height: `${height}px` }">
    <canvas :id="chartId"></canvas>
    <div v-if="!chartData" class="no-data">
      <p>暂无数据</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import Chart from 'chart.js/auto'

const props = defineProps({
  chartData: {
    type: Object,
    required: false
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
  }
})

const chart = ref(null)

// 创建图表
const createChart = () => {
  if (!props.chartData) return
  
  const ctx = document.getElementById(props.chartId)
  if (!ctx) return

  // 销毁已存在的图表实例
  if (chart.value) {
    chart.value.destroy()
  }
  
  // 创建新图表
  chart.value = new Chart(ctx, {
    type: 'line',
    data: props.chartData,
    options: props.options
  })
}

// 更新图表数据
const updateChart = () => {
  if (!chart.value || !props.chartData) return
  
  try {
    // 不要直接更新图表，而是销毁并重新创建
    chart.value.destroy()
    const ctx = document.getElementById(props.chartId)
    if (!ctx) return
    
    chart.value = new Chart(ctx, {
      type: 'line',
      data: props.chartData,
      options: props.options
    })
  } catch (error) {
    console.error('图表更新失败:', error)
  }
}

// 监听数据变化
watch(() => props.chartData, (newVal) => {
  if (newVal) {
  if (chart.value) {
      updateChart()
  } else {
    createChart()
    }
  }
}, { deep: true })

// 监听选项变化
watch(() => props.options, (newVal) => {
  if (chart.value && props.chartData) {
    try {
      // 不要直接更新图表，而是销毁并重新创建
      chart.value.destroy()
      const ctx = document.getElementById(props.chartId)
      if (!ctx) return
      
      chart.value = new Chart(ctx, {
        type: 'line',
        data: props.chartData,
        options: newVal
      })
    } catch (error) {
      console.error('图表更新选项失败:', error)
    }
  }
}, { deep: true })

// 组件挂载时创建图表
onMounted(() => {
  if (props.chartData) {
    createChart()
  }
})

// 组件卸载时销毁图表
onUnmounted(() => {
  if (chart.value) {
    chart.value.destroy()
  }
})
</script>

<style scoped>
.chart-container {
  position: relative;
  width: 100%;
  min-height: 400px;
}

.no-data {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: rgba(245, 247, 250, 0.6);
}

.no-data p {
  color: #909399;
  font-size: 14px;
}
</style> 