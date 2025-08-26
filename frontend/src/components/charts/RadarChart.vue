<template>
  <div class="chart-container">
    <canvas :id="chartId" :height="height"></canvas>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import Chart from 'chart.js/auto'

const props = defineProps({
  chartData: {
    type: Object,
    required: true
  },
  chartId: {
    type: String,
    default: 'radar-chart'
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
  const canvas = document.getElementById(props.chartId)
  if (!canvas) return

  // 销毁旧图表（如果存在）
  if (chart.value) {
    chart.value.destroy()
  }

  const ctx = canvas.getContext('2d')
  
  // 合并默认选项和传入的选项
  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        angleLines: {
          display: true
        },
        suggestedMin: 0,
        ticks: {
          stepSize: 0.5
        }
      }
    },
    plugins: {
      legend: {
        position: 'bottom'
      }
    }
  }
  
  const chartOptions = Object.assign({}, defaultOptions, props.options)
  
  // 创建新图表
  chart.value = new Chart(ctx, {
    type: 'radar',
    data: props.chartData,
    options: chartOptions
  })
}

// 监听数据变化，更新图表
watch(() => props.chartData, (newData) => {
  if (chart.value) {
    chart.value.data = newData
    chart.value.update()
  } else {
    createChart()
  }
}, { deep: true })

// 组件挂载时创建图表
onMounted(() => {
  if (props.chartData && props.chartData.datasets) {
    createChart()
  }
})

// 组件卸载前销毁图表
onBeforeUnmount(() => {
  if (chart.value) {
    chart.value.destroy()
  }
})
</script>

<style scoped>
.chart-container {
  position: relative;
  width: 100%;
}
</style> 