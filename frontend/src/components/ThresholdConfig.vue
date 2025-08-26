<template>
  <div class="threshold-config">
    <div class="config-card">
      <h3>{{ configTitle }}</h3>
      <p class="config-description">
        设置故障诊断阈值，系统将根据这些阈值判断电机运行状态。
      </p>
      
      <el-form label-position="top">
        <el-form-item :label="`预警阈值 (当前: ${(thresholds.warning * 100).toFixed(1)}%)`">
          <el-slider
            v-model="thresholds.warning"
            :min="0"
            :max="1"
            :step="0.01"
            :format-tooltip="formatTooltip"
          />
        </el-form-item>
        
        <el-form-item :label="`故障阈值 (当前: ${(thresholds.fault * 100).toFixed(1)}%)`">
          <el-slider
            v-model="thresholds.fault"
            :min="0"
            :max="1"
            :step="0.01"
            :format-tooltip="formatTooltip"
          />
        </el-form-item>
      </el-form>
      
      <div class="threshold-actions">
        <el-button type="primary" @click="saveThresholds">保存配置</el-button>
        <el-button @click="resetThresholds">恢复默认</el-button>
      </div>
      
      <div class="threshold-legend">
        <div class="legend-item">
          <div class="legend-color normal"></div>
          <div class="legend-text">正常 (0% ~ {{ (thresholds.warning * 100).toFixed(1) }}%)</div>
        </div>
        <div class="legend-item">
          <div class="legend-color warning"></div>
          <div class="legend-text">预警 ({{ (thresholds.warning * 100).toFixed(1) }}% ~ {{ (thresholds.fault * 100).toFixed(1) }}%)</div>
        </div>
        <div class="legend-item">
          <div class="legend-color fault"></div>
          <div class="legend-text">故障 ({{ (thresholds.fault * 100).toFixed(1) }}% ~ 100%)</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  configType: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['update:thresholds'])

// 默认阈值配置
const defaultThresholds = {
  'broken-bar': {
    warning: 0.05,
    fault: 0.1
  },
  'turn-fault': {
    warning: 0.15,
    fault: 0.3
  },
  'bearing': {
    warning: 0.2,
    fault: 0.4
  },
  'eccentricity': {
    warning: 0.1,
    fault: 0.25
  },
  'stator': {
    warning: 0.15,
    fault: 0.35
  }
}

// 配置标题
const configTitle = computed(() => {
  const titles = {
    'broken-bar': '断条故障阈值配置',
    'turn-fault': '匝间短路故障阈值配置',
    'bearing': '轴承故障阈值配置',
    'eccentricity': '偏心故障阈值配置',
    'stator': '定子故障阈值配置'
  }
  return titles[props.configType] || '故障阈值配置'
})

// 阈值配置
const thresholds = reactive({
  warning: defaultThresholds[props.configType]?.warning || 0.15,
  fault: defaultThresholds[props.configType]?.fault || 0.3
})

// 格式化提示
const formatTooltip = (val) => {
  return `${(val * 100).toFixed(1)}%`
}

// 保存阈值配置
const saveThresholds = () => {
  // 验证阈值
  if (thresholds.warning >= thresholds.fault) {
    ElMessage.error('预警阈值必须小于故障阈值')
    return
  }
  
  // 保存到localStorage
  localStorage.setItem(`${props.configType}Thresholds`, JSON.stringify(thresholds))
  
  // 通知父组件
  emit('update:thresholds', thresholds)
  
  ElMessage.success('阈值配置已保存')
}

// 重置为默认值
const resetThresholds = () => {
  const defaults = defaultThresholds[props.configType] || { warning: 0.15, fault: 0.3 }
  thresholds.warning = defaults.warning
  thresholds.fault = defaults.fault
  
  // 保存到localStorage
  localStorage.setItem(`${props.configType}Thresholds`, JSON.stringify(thresholds))
  
  // 通知父组件
  emit('update:thresholds', thresholds)
  
  ElMessage.success('已恢复默认阈值配置')
}

// 监听阈值变化
watch(thresholds, (newVal) => {
  // 确保预警阈值小于故障阈值
  if (newVal.warning >= newVal.fault) {
    if (newVal.warning > newVal.fault) {
      thresholds.fault = Math.min(1, newVal.warning + 0.05)
    } else {
      thresholds.warning = Math.max(0, newVal.fault - 0.05)
    }
  }
  
  // 通知父组件
  emit('update:thresholds', thresholds)
}, { deep: true })

// 组件挂载时加载保存的配置
onMounted(() => {
  const savedConfig = localStorage.getItem(`${props.configType}Thresholds`)
  if (savedConfig) {
    try {
      const parsed = JSON.parse(savedConfig)
      thresholds.warning = parsed.warning
      thresholds.fault = parsed.fault
    } catch (e) {
      console.error('解析保存的阈值配置失败:', e)
    }
  }
})
</script>

<style scoped>
.threshold-config {
  margin-bottom: 20px;
}

.config-card {
  background-color: #f5f7fa;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
}

.config-description {
  color: #606266;
  margin-bottom: 20px;
}

.threshold-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  gap: 10px;
}

.threshold-legend {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #EBEEF5;
}

.legend-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.legend-color {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  margin-right: 10px;
}

.legend-color.normal {
  background-color: #67C23A;
}

.legend-color.warning {
  background-color: #E6A23C;
}

.legend-color.fault {
  background-color: #F56C6C;
}

.legend-text {
  font-size: 14px;
  color: #606266;
}
</style> 