<template>
  <div class="throughput-config">
    <div class="header">
      <h1>🔧 吞吐量配置管理</h1>
      <p>动态调整吞吐量计算参数，优化递减速度和性能表现</p>
    </div>

    <el-row :gutter="20">
      <!-- 当前配置显示 -->
      <el-col :span="8">
        <el-card shadow="hover" class="config-card">
          <template #header>
            <div class="card-header">
              <span>📊 当前配置</span>
              <el-button size="small" @click="refreshConfig">刷新</el-button>
            </div>
          </template>
          
          <div v-if="currentConfig" class="config-display">
            <div class="config-item">
              <label>时间窗口：</label>
              <span>{{ currentConfig.freshness_window_minutes }}分钟</span>
            </div>
            <div class="config-item">
              <label>最小新鲜度因子：</label>
              <span>{{ currentConfig.min_freshness_factor }}</span>
            </div>
            <div class="config-item">
              <label>递减曲线：</label>
              <span>{{ getCurveTypeName(currentConfig.decay_curve_type) }}</span>
            </div>
            <div class="config-item">
              <label>递减陡峭程度：</label>
              <span>{{ currentConfig.decay_steepness }}</span>
            </div>
            <div class="config-item">
              <label>自动刷新：</label>
              <el-tag :type="currentConfig.auto_refresh_enabled ? 'success' : 'danger'">
                {{ currentConfig.auto_refresh_enabled ? '启用' : '禁用' }}
              </el-tag>
            </div>
            <div class="config-item">
              <label>基础乘数：</label>
              <span>{{ currentConfig.base_throughput_multiplier }}</span>
            </div>
          </div>
          
          <div v-else class="loading">
            <el-skeleton :rows="6" animated />
          </div>
        </el-card>
      </el-col>

      <!-- 配置调整 -->
      <el-col :span="8">
        <el-card shadow="hover" class="config-card">
          <template #header>
            <span>⚙️ 配置调整</span>
          </template>
          
          <el-form :model="updateForm" label-width="120px" size="small">
            <el-form-item label="时间窗口">
              <el-slider
                v-model="updateForm.freshness_window_minutes"
                :min="10"
                :max="180"
                :step="5"
                show-input
              />
              <div class="form-help">数据新鲜度判断的时间范围</div>
            </el-form-item>

            <el-form-item label="最小新鲜度因子">
              <el-slider
                v-model="updateForm.min_freshness_factor"
                :min="0.1"
                :max="0.8"
                :step="0.1"
                show-input
              />
              <div class="form-help">最低保留的新鲜度值</div>
            </el-form-item>

            <el-form-item label="递减曲线类型">
              <el-select v-model="updateForm.decay_curve_type" style="width: 100%">
                <el-option label="线性递减" value="linear" />
                <el-option label="对数递减 (推荐)" value="logarithmic" />
                <el-option label="指数递减" value="exponential" />
                <el-option label="平方根递减" value="sqrt" />
              </el-select>
              <div class="form-help">不同曲线影响递减的平滑程度</div>
            </el-form-item>

            <el-form-item label="递减陡峭程度">
              <el-slider
                v-model="updateForm.decay_steepness"
                :min="0.1"
                :max="2.0"
                :step="0.1"
                show-input
              />
              <div class="form-help">数值越小递减越平缓</div>
            </el-form-item>

            <el-form-item label="自动刷新">
              <el-switch v-model="updateForm.auto_refresh_enabled" />
              <div class="form-help">自动添加新数据防止过期</div>
            </el-form-item>

            <el-form-item label="基础乘数">
              <el-slider
                v-model="updateForm.base_throughput_multiplier"
                :min="2.0"
                :max="15.0"
                :step="0.5"
                show-input
              />
              <div class="form-help">基础吞吐量的倍数系数</div>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" @click="updateConfig" :loading="updating">
                应用配置
              </el-button>
              <el-button @click="resetConfig" :loading="resetting">
                重置默认
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 曲线预览 -->
      <el-col :span="8">
        <el-card shadow="hover" class="config-card">
          <template #header>
            <div class="card-header">
              <span>📈 曲线预览</span>
              <el-button size="small" @click="previewCurve">更新预览</el-button>
            </div>
          </template>
          
          <div class="preview-container">
            <div ref="chartContainer" class="chart-container"></div>
            
            <div class="preview-controls">
              <el-form-item label="预览年龄" size="small">
                <el-input-number
                  v-model="previewAge"
                  :min="0"
                  :max="180"
                  @change="previewCurve"
                />
                <span class="unit">分钟</span>
              </el-form-item>
              
              <div v-if="previewData" class="preview-result">
                <div class="result-item">
                  <strong>当前新鲜度因子：</strong>
                  <span class="factor-value">{{ previewData.current_factor }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 配置预设 -->
    <el-row :gutter="20" class="presets-section">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <span>🎯 配置预设</span>
          </template>
          
          <div class="presets-grid">
            <div
              v-for="preset in presets"
              :key="preset.key"
              class="preset-card"
              @click="applyPreset(preset.key)"
            >
              <div class="preset-icon">{{ preset.icon }}</div>
              <div class="preset-title">{{ preset.name }}</div>
              <div class="preset-desc">{{ preset.description }}</div>
              <div class="preset-params">
                <span>窗口: {{ preset.window }}分钟</span>
                <span>曲线: {{ getCurveTypeName(preset.curve) }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 实时测试 -->
    <el-row :gutter="20" class="test-section">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>🧪 实时测试</span>
          </template>
          
          <div class="test-controls">
            <el-button type="primary" @click="startTest" :loading="testing">
              开始测试
            </el-button>
            <el-button @click="manualRefresh" :loading="refreshing">
              手动刷新数据
            </el-button>
          </div>
          
          <div v-if="testResults.length > 0" class="test-results">
            <h4>测试结果：</h4>
            <div class="result-list">
              <div
                v-for="(result, index) in testResults"
                :key="index"
                class="result-item"
              >
                <span class="result-time">第{{ index + 1 }}次：</span>
                <span class="result-value">{{ result.throughput }} msg/s</span>
                <span v-if="index > 0" class="result-change">
                  ({{ getChangeText(result.throughput, testResults[index-1].throughput) }})
                </span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>📊 性能监控</span>
          </template>
          
          <div class="performance-monitor">
            <div class="metric-item">
              <label>当前吞吐量：</label>
              <span class="metric-value">{{ currentThroughput }} msg/s</span>
            </div>
            <div class="metric-item">
              <label>响应延迟：</label>
              <span class="metric-value">{{ currentLatency }} ms</span>
            </div>
            <div class="metric-item">
              <label>队列长度：</label>
              <span class="metric-value">{{ currentQueueLength }}</span>
            </div>
            
            <el-button @click="refreshMetrics" size="small" class="refresh-btn">
              刷新指标
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as echarts from 'echarts'

export default {
  name: 'ThroughputConfig',
  setup() {
    // 响应式数据
    const currentConfig = ref(null)
    const updating = ref(false)
    const resetting = ref(false)
    const testing = ref(false)
    const refreshing = ref(false)
    const previewAge = ref(15)
    const previewData = ref(null)
    const chartContainer = ref(null)
    const chart = ref(null)
    const testResults = ref([])
    const currentThroughput = ref(0)
    const currentLatency = ref(0)
    const currentQueueLength = ref(0)

    // 表单数据
    const updateForm = reactive({
      freshness_window_minutes: 60,
      min_freshness_factor: 0.3,
      decay_curve_type: 'logarithmic',
      decay_steepness: 0.5,
      auto_refresh_enabled: true,
      base_throughput_multiplier: 8.0
    })

    // 配置预设
    const presets = [
      {
        key: 'stable',
        name: '稳定模式',
        description: '递减缓慢，适合长期稳定运行',
        icon: '🏛️',
        window: 90,
        curve: 'logarithmic'
      },
      {
        key: 'responsive',
        name: '响应模式',
        description: '快速响应数据变化，适合实时监控',
        icon: '⚡',
        window: 45,
        curve: 'exponential'
      },
      {
        key: 'conservative',
        name: '保守模式',
        description: '递减极慢，数据保持时间长',
        icon: '🛡️',
        window: 120,
        curve: 'logarithmic'
      },
      {
        key: 'performance',
        name: '性能模式',
        description: '高吞吐量，适合高负载场景',
        icon: '🚀',
        window: 60,
        curve: 'linear'
      }
    ]

    // API 调用方法
    const api = {
      async getCurrentConfig() {
        const response = await fetch('/api/v1/config/throughput')
        return response.json()
      },

      async updateConfig(data) {
        const response = await fetch('/api/v1/config/throughput', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        })
        return response.json()
      },

      async resetConfig() {
        const response = await fetch('/api/v1/config/throughput/reset', {
          method: 'POST'
        })
        return response.json()
      },

      async previewCurve(params) {
        const query = new URLSearchParams(params)
        const response = await fetch(`/api/v1/config/throughput/preview?${query}`)
        return response.json()
      },

      async manualRefresh() {
        const response = await fetch('/api/v1/config/throughput/refresh', {
          method: 'POST'
        })
        return response.json()
      },

      async getClusterStatus() {
        const response = await fetch('/api/v1/cluster/status')
        return response.json()
      }
    }

    // 方法
    const refreshConfig = async () => {
      try {
        const result = await api.getCurrentConfig()
        currentConfig.value = result
        
        // 更新表单数据
        Object.assign(updateForm, result)
        
        ElMessage.success('配置已刷新')
      } catch (error) {
        ElMessage.error('获取配置失败')
        console.error(error)
      }
    }

    const updateConfig = async () => {
      try {
        updating.value = true
        
        const result = await api.updateConfig(updateForm)
        
        if (result.status === 'success') {
          ElMessage.success(result.message)
          await refreshConfig()
          await previewCurve()
        } else {
          ElMessage.error(result.message || '更新失败')
        }
      } catch (error) {
        ElMessage.error('更新配置失败')
        console.error(error)
      } finally {
        updating.value = false
      }
    }

    const resetConfig = async () => {
      try {
        await ElMessageBox.confirm('确定要重置为默认配置吗？', '确认重置', {
          type: 'warning'
        })
        
        resetting.value = true
        
        const result = await api.resetConfig()
        
        if (result.status === 'success') {
          ElMessage.success('配置已重置')
          await refreshConfig()
          await previewCurve()
        }
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('重置配置失败')
          console.error(error)
        }
      } finally {
        resetting.value = false
      }
    }

    const previewCurve = async () => {
      try {
        const params = {
          age_minutes: previewAge.value,
          curve_type: updateForm.decay_curve_type,
          steepness: updateForm.decay_steepness,
          window_minutes: updateForm.freshness_window_minutes,
          min_factor: updateForm.min_freshness_factor
        }
        
        const result = await api.previewCurve(params)
        
        if (result.status === 'success') {
          previewData.value = result.data
          renderChart(result.data.curve_preview)
        }
      } catch (error) {
        ElMessage.error('预览曲线失败')
        console.error(error)
      }
    }

    const renderChart = (curveData) => {
      if (!chart.value || !curveData) return

      const option = {
        title: {
          text: '新鲜度因子曲线',
          textStyle: { fontSize: 14 }
        },
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            const point = params[0]
            return `年龄: ${point.axisValue}分钟<br/>新鲜度因子: ${point.value}`
          }
        },
        xAxis: {
          type: 'category',
          data: curveData.map(item => item.age_minutes),
          name: '数据年龄 (分钟)'
        },
        yAxis: {
          type: 'value',
          name: '新鲜度因子',
          min: 0,
          max: 1
        },
        series: [{
          data: curveData.map(item => item.freshness_factor),
          type: 'line',
          smooth: true,
          lineStyle: { color: '#409EFF' },
          areaStyle: { 
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#409EFF' },
              { offset: 1, color: 'rgba(64, 158, 255, 0.1)' }
            ])
          }
        }]
      }

      chart.value.setOption(option)
    }

    const applyPreset = async (presetKey) => {
      try {
        const presetConfigs = {
          stable: {
            freshness_window_minutes: 90,
            min_freshness_factor: 0.4,
            decay_curve_type: 'logarithmic',
            decay_steepness: 0.3,
            auto_refresh_enabled: true,
            base_throughput_multiplier: 8.0
          },
          responsive: {
            freshness_window_minutes: 45,
            min_freshness_factor: 0.2,
            decay_curve_type: 'exponential',
            decay_steepness: 0.7,
            auto_refresh_enabled: true,
            base_throughput_multiplier: 9.0
          },
          conservative: {
            freshness_window_minutes: 120,
            min_freshness_factor: 0.5,
            decay_curve_type: 'logarithmic',
            decay_steepness: 0.2,
            auto_refresh_enabled: true,
            base_throughput_multiplier: 7.0
          },
          performance: {
            freshness_window_minutes: 60,
            min_freshness_factor: 0.3,
            decay_curve_type: 'linear',
            decay_steepness: 0.5,
            auto_refresh_enabled: true,
            base_throughput_multiplier: 12.0
          }
        }

        const config = presetConfigs[presetKey]
        if (config) {
          Object.assign(updateForm, config)
          await updateConfig()
          ElMessage.success(`已应用${presets.find(p => p.key === presetKey)?.name}预设`)
        }
      } catch (error) {
        ElMessage.error('应用预设失败')
        console.error(error)
      }
    }

    const startTest = async () => {
      testing.value = true
      testResults.value = []
      
      try {
        for (let i = 0; i < 5; i++) {
          const result = await api.getClusterStatus()
          if (result.status === 'success') {
            const metrics = result.data.performance_metrics
            testResults.value.push({
              index: i + 1,
              throughput: metrics.throughput,
              latency: metrics.latency,
              timestamp: new Date().toLocaleTimeString()
            })
          }
          
          if (i < 4) {
            await new Promise(resolve => setTimeout(resolve, 3000))
          }
        }
        
        ElMessage.success('测试完成')
      } catch (error) {
        ElMessage.error('测试失败')
        console.error(error)
      } finally {
        testing.value = false
      }
    }

    const manualRefresh = async () => {
      try {
        refreshing.value = true
        const result = await api.manualRefresh()
        
        if (result.status === 'success') {
          ElMessage.success('数据刷新成功')
          await refreshMetrics()
        }
      } catch (error) {
        ElMessage.error('数据刷新失败')
        console.error(error)
      } finally {
        refreshing.value = false
      }
    }

    const refreshMetrics = async () => {
      try {
        const result = await api.getClusterStatus()
        if (result.status === 'success') {
          const metrics = result.data.performance_metrics
          currentThroughput.value = metrics.throughput
          currentLatency.value = metrics.latency
          currentQueueLength.value = metrics.queue_length
        }
      } catch (error) {
        console.error('刷新指标失败:', error)
      }
    }

    // 工具方法
    const getCurveTypeName = (type) => {
      const names = {
        linear: '线性',
        logarithmic: '对数',
        exponential: '指数',
        sqrt: '平方根'
      }
      return names[type] || type
    }

    const getChangeText = (current, previous) => {
      const change = current - previous
      const percent = ((change / previous) * 100).toFixed(1)
      return change >= 0 ? `+${change.toFixed(1)} (+${percent}%)` : `${change.toFixed(1)} (${percent}%)`
    }

    // 生命周期
    onMounted(async () => {
      await refreshConfig()
      await refreshMetrics()
      
      nextTick(() => {
        if (chartContainer.value) {
          chart.value = echarts.init(chartContainer.value)
          previewCurve()
        }
      })
    })

    return {
      currentConfig,
      updateForm,
      updating,
      resetting,
      testing,
      refreshing,
      previewAge,
      previewData,
      chartContainer,
      testResults,
      currentThroughput,
      currentLatency,
      currentQueueLength,
      presets,
      refreshConfig,
      updateConfig,
      resetConfig,
      previewCurve,
      applyPreset,
      startTest,
      manualRefresh,
      refreshMetrics,
      getCurveTypeName,
      getChangeText
    }
  }
}
</script>

<style scoped>
.throughput-config {
  padding: 20px;
  background: #f5f5f5;
  min-height: 100vh;
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h1 {
  color: #409EFF;
  margin-bottom: 10px;
}

.config-card {
  margin-bottom: 20px;
  height: 500px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.config-display {
  height: 400px;
  overflow-y: auto;
}

.config-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
}

.config-item label {
  font-weight: bold;
  color: #666;
}

.form-help {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.chart-container {
  height: 250px;
  width: 100%;
}

.preview-controls {
  margin-top: 20px;
}

.preview-result {
  margin-top: 10px;
  padding: 10px;
  background: #f0f9ff;
  border-radius: 4px;
}

.factor-value {
  font-weight: bold;
  color: #409EFF;
}

.presets-section {
  margin-top: 20px;
}

.presets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
}

.preset-card {
  padding: 20px;
  background: #fff;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
}

.preset-card:hover {
  border-color: #409EFF;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.preset-icon {
  font-size: 32px;
  margin-bottom: 10px;
}

.preset-title {
  font-weight: bold;
  color: #303133;
  margin-bottom: 8px;
}

.preset-desc {
  color: #666;
  font-size: 12px;
  margin-bottom: 10px;
}

.preset-params {
  display: flex;
  justify-content: space-around;
  font-size: 11px;
  color: #999;
}

.test-section {
  margin-top: 20px;
}

.test-controls {
  margin-bottom: 20px;
}

.test-results {
  max-height: 200px;
  overflow-y: auto;
}

.result-list {
  space-y: 8px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
  margin-bottom: 8px;
}

.result-time {
  font-weight: bold;
  color: #666;
}

.result-value {
  color: #409EFF;
  font-weight: bold;
}

.result-change {
  font-size: 12px;
  color: #999;
}

.performance-monitor {
  space-y: 15px;
}

.metric-item {
  display: flex;
  justify-content: space-between;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 4px;
  margin-bottom: 10px;
}

.metric-value {
  font-weight: bold;
  color: #409EFF;
}

.refresh-btn {
  width: 100%;
  margin-top: 15px;
}

.unit {
  margin-left: 8px;
  color: #999;
  font-size: 12px;
}

.loading {
  height: 400px;
  padding: 20px;
}
</style>