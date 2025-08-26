<template>
  <div ref="chartRef" style="width: 100%; height: 400px;"></div>
</template>

<script setup>
import { defineProps, ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  features: {
    type: Object,
    required: true
  },
  featureScores: {
    type: Object,
    default: () => ({})
  },
  thresholds: {
    type: Object,
    default: () => ({})
  },
  chartType: {
    type: String,
    default: 'turn-to-turn'  // 'turn-to-turn' 或 'insulation'
  }
})

// 图表DOM引用
const chartRef = ref(null)
let chart = null

// 特征配置
const featureConfig = {
  'turn-to-turn': [
    { name: '负序电流', key: 'I2_avg', max: 2, unit: 'A', desc: '负序电流平均值' },
    { name: '负/正序比值', key: 'I2_I1_ratio', max: 1.5, unit: '', desc: '负序/正序电流比值' },
    { name: '电流不平衡度', key: 'unbalance_avg', max: 30, unit: '%', desc: '电流不平衡度平均值(%)' },
    { name: 'ΔI_q峭度', key: 'kurtosis_delta_iq', max: 10, unit: '', desc: 'ΔI_q滑动窗口峭度' },
    { name: '效率残差', key: 'delta_eta_avg', max: 0.5, unit: '', invert: true, desc: '效率残差平均值' }
  ],
  'insulation': [
    { name: '绕组温度比率', key: 'temp_ratio', max: 1.5, unit: '', desc: '绕组温度比率' },
    { name: '温升速率', key: 'temp_rise_rate', max: 5, unit: '°C/min', desc: '温升速率' },
    { name: '温度残差', key: 'thermal_residual', max: 20, unit: '°C', desc: '温度残差' },
    { name: '效率残差', key: 'efficiency_residual', max: 0.05, unit: '', invert: true, desc: '效率残差' },
    { name: '电流残差趋势', key: 'current_residual_trend', max: 0.02, unit: '', desc: '电流残差趋势' },
    { name: '热老化累积', key: 'thermal_aging', max: 500, unit: '', desc: '热老化累积' }
  ]
}

// 判断故障状态
const getFaultStatus = (value, threshold, isInverted = false) => {
  if (isInverted) {
    if (value < threshold) return '正常'
    else return '故障'
  } else {
    if (value > threshold) return '故障'
    else return '正常'
  }
}

// 初始化图表
const initChart = () => {
  if (!chartRef.value) return
  
  // 销毁已有图表
  if (chart) {
    chart.dispose()
  }
  
  // 创建新图表
  chart = echarts.init(chartRef.value)
  updateChart()
}

// 更新图表数据
const updateChart = () => {
  if (!chart) return
  
  const config = featureConfig[props.chartType] || featureConfig['turn-to-turn']
  
  // 准备雷达图数据
  const indicator = config.map(item => {
    // 使用配置的最大值，确保能显示所有数据
    return {
      name: item.name + (item.unit ? ` (${item.unit})` : ''),
      max: item.max,
      min: 0,
      precision: 2
    }
  })
  
  // 准备特征值数据
  const featureData = config.map(item => {
    // 对于需要反转的值（如效率残差，负值表示异常），取绝对值
    if (item.invert && props.features[item.key] < 0) {
      return Math.min(Math.abs(props.features[item.key]), item.max)
    }
    return Math.min(props.features[item.key] || 0, item.max)
  })
  
  // 准备阈值数据（基于特征评分）
  const scoreData = config.map(item => {
    const score = props.featureScores[item.key] || 0
    return item.max * score  // 根据评分缩放到最大值
  })
  
  // 根据图表类型设置样式
  const isInsulation = props.chartType === 'insulation'
  const lineWidth = isInsulation ? 3 : 2
  const symbolSize = isInsulation ? 8 : 6
  
  // 设置图表选项
  const option = {
    title: {
      text: props.chartType === 'insulation' ? '绝缘状态特征参数' : '匝间短路特征参数',
      left: 'center'
    },
    tooltip: {
      show: true,
      confine: true,
      trigger: 'item',
      formatter: function(params) {
        // 获取所有特征数据
        let result = '<div style="font-weight:bold;margin-bottom:5px;">特征参数详情</div>';
        
        config.forEach((item, idx) => {
          const value = props.features[item.key] || 0;
          const threshold = props.thresholds[item.key] || 0;
          
          // 正确获取异常评分数据
          let score, scoreText;
          if (typeof props.featureScores[item.key] === 'number') {
            score = props.featureScores[item.key];
            scoreText = (score * 100).toFixed(1) + '%';
          } else {
            // 如果没有评分数据，尝试计算一个基本评分
            if (item.invert) {
              score = value < threshold ? 0 : Math.min((value / threshold) - 1, 1);
            } else {
              score = value > threshold ? Math.min(value / threshold, 1) : 0;
            }
            scoreText = (score * 100).toFixed(1) + '%';
          }
          
          const status = getFaultStatus(value, threshold, item.invert);
          const color = status === '故障' ? 'red' : 'green';
          
          result += `<div style="margin: 5px 0;">
            <span style="font-weight:bold;">${item.desc}:</span> ${value}${item.unit}<br/>
            <span style="margin-left:15px;">阈值: ${threshold}${item.unit}</span><br/>
            <span style="margin-left:15px;">异常评分: ${scoreText}</span><br/>
            <span style="margin-left:15px;">状态: <span style="color:${color};font-weight:bold;">${status}</span></span>
          </div>`;
        });
        
        return result;
      }
    },
    legend: {
      data: isInsulation ? ['特征值'] : ['特征值', '异常评分'],
      bottom: 0
    },
    radar: {
      indicator: indicator,
      shape: 'circle',
      splitNumber: 4,
      axisName: {
        color: '#333',
        fontSize: 12
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(255, 255, 255, 0.8)', 'rgba(240, 240, 240, 0.8)']
        }
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(0, 0, 0, 0.2)'
        }
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(0, 0, 0, 0.2)'
        }
      }
    },
    series: [
      {
        name: '特征分析',
        type: 'radar',
        data: isInsulation ? 
          [
            {
              value: featureData,
              name: '特征值',
              symbol: 'circle',
              symbolSize: symbolSize,
              lineStyle: {
                width: lineWidth,
                color: '#409EFF'
              },
              areaStyle: {
                color: 'rgba(64, 158, 255, 0.2)'
              }
            }
          ] : 
          [
            {
              value: scoreData,
              name: '异常评分',
              symbol: 'circle',
              symbolSize: symbolSize,
              lineStyle: {
                width: lineWidth,
                color: '#F56C6C'
              },
              areaStyle: {
                color: 'rgba(245, 108, 108, 0.2)'
              },
              z: 1
            },
            {
              value: featureData,
              name: '特征值',
              symbol: 'circle',
              symbolSize: symbolSize,
              lineStyle: {
                width: lineWidth,
                color: '#409EFF'
              },
              areaStyle: {
                color: 'rgba(64, 158, 255, 0.2)'
              },
              z: 2
            }
          ]
      }
    ]
  }
  
  // 应用选项
  chart.setOption(option)
}

// 监听特征变化
watch(() => props.features, updateChart, { deep: true })
watch(() => props.featureScores, updateChart, { deep: true })
watch(() => props.thresholds, updateChart, { deep: true })
watch(() => props.chartType, updateChart)

// 监听窗口大小变化
window.addEventListener('resize', () => {
  if (chart) {
    chart.resize()
  }
})

// 组件挂载时初始化图表
onMounted(initChart)
</script>

<style scoped>
.radar-chart-container {
  margin: 20px 0;
}

.radar-chart-container h3 {
  font-size: 16px;
  margin-bottom: 20px;
  text-align: center;
  color: #606266;
}

.chart {
  width: 100%;
  height: 450px;
  margin-bottom: 10px;
}

@media (max-width: 768px) {
  .chart {
    height: 350px;
  }
}
</style> 