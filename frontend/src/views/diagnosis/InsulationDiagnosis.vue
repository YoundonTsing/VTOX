<template>
  <div class="diagnosis-container">
    <div class="page-header">
      <h2 class="page-title">绝缘失效检测</h2>
      <el-button type="primary" @click="showConfig = !showConfig">
        {{ showConfig ? '隐藏配置' : '阈值配置' }}
      </el-button>
    </div>

    <!-- 阈值配置面板 -->
    <el-collapse-transition>
      <div v-if="showConfig">
        <threshold-config @update:thresholds="updateThresholds" :config-type="'insulation'" />
      </div>
    </el-collapse-transition>

    <!-- 文件上传区域 -->
    <div class="card upload-card">
      <h3>绝缘状态分析</h3>
      <p class="upload-description">
        上传电机运行数据CSV文件，系统将分析电机绝缘状态是否存在劣化或失效。
        <el-button type="primary" link @click="showDataFormatHelp = true">
          支持的数据格式
        </el-button>
      </p>
      
      <el-upload
        class="upload-area"
        drag
        action="#"
        :auto-upload="false"
        :show-file-list="true"
        :limit="1"
        accept=".csv"
        :on-change="handleFileChange"
        :on-exceed="handleExceed"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽文件至此处或 <em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">
            请上传CSV格式的电机数据文件，需包含温度、电流、电压等参数
          </div>
        </template>
      </el-upload>
      
      <div class="upload-actions" v-if="file">
        <p class="selected-file">已选择文件: {{ file.name }}</p>
        <el-button type="primary" @click="handleAnalyze" :loading="loading">
          {{ loading ? '分析中...' : '开始分析' }}
        </el-button>
      </div>
      
      <!-- 示例文件下载 -->
      <div class="sample-file">
        <el-divider content-position="left">示例数据</el-divider>
        <div class="sample-actions">
          <span class="sample-text">下载示例数据文件：</span>
          <div class="sample-buttons">
            <el-button size="small" @click="downloadSampleFile('normal')">正常绝缘样本</el-button>
            <el-button size="small" @click="downloadSampleFile('degrading')">绝缘劣化样本</el-button>
            <el-button size="small" @click="downloadSampleFile('critical')">绝缘危险样本</el-button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 分析结果 -->
    <div v-if="result" class="results-container">
      <!-- 绝缘状态评分卡片 -->
      <div class="card">
        <h2>绝缘状态诊断结果</h2>
        
        <!-- 绝缘状态评分和状态 -->
        <div class="result-header">
          <div class="status-box" :class="getStatusClass(result.status)">
            <h3>状态: {{ getStatusText(result.status) }}</h3>
            <p>绝缘劣化度: {{ (result.score * 100).toFixed(1) }}%</p>
          </div>
          
          <!-- 绝缘状态仪表盘 -->
          <div class="gauge-container">
            <div class="gauge">
              <div class="gauge-fill" :style="{ width: `${result.score * 100}%` }"></div>
              <div class="gauge-text">{{ (result.score * 100).toFixed(1) }}%</div>
            </div>
            <div class="threshold-markers">
              <div class="threshold-marker threshold-marker-warning" :style="{ left: `${thresholds.degrading * 100}%` }">
                <div class="marker-line"></div>
                <div class="marker-label">劣化阈值</div>
              </div>
              <div class="threshold-marker threshold-marker-fault" :style="{ left: `${thresholds.critical * 100}%` }">
                <div class="marker-line"></div>
                <div class="marker-label">危险阈值</div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 特征参数雷达图 -->
        <div class="feature-radar">
          <h3>绝缘状态特征参数</h3>
          <feature-radar-chart 
            :features="result.features" 
            :feature-scores="result.feature_scores"
            :chart-type="'insulation'"
          />
        </div>
      </div>
      
      <!-- 温度相关特征卡片 -->
      <div class="card">
        <h3>温度特征分析</h3>
        <div class="feature-grid">
          <div class="feature-item" :class="getFeatureClass(result.feature_scores.temp_ratio)">
            <div class="feature-header">
              <span class="feature-name">绕组温度比率</span>
              <span class="feature-score">{{ getFeatureStatusText(result.feature_scores.temp_ratio) }}</span>
            </div>
            <div class="feature-value">{{ result.features.temp_ratio.toFixed(2) }}</div>
            <div class="feature-desc">绕组温度与额定温度的比值，超过1.1表示异常</div>
          </div>
          
          <div class="feature-item" :class="getFeatureClass(result.feature_scores.temp_rise_rate)">
            <div class="feature-header">
              <span class="feature-name">温升速率</span>
              <span class="feature-score">{{ getFeatureStatusText(result.feature_scores.temp_rise_rate) }}</span>
            </div>
            <div class="feature-value">{{ result.features.temp_rise_rate.toFixed(2) }} °C/min</div>
            <div class="feature-desc">绕组温度上升速率，正常值应低于2°C/min</div>
          </div>
          
          <div class="feature-item" :class="getFeatureClass(result.feature_scores.thermal_residual)">
            <div class="feature-header">
              <span class="feature-name">温度模型残差</span>
              <span class="feature-score">{{ getFeatureStatusText(result.feature_scores.thermal_residual) }}</span>
            </div>
            <div class="feature-value">{{ result.features.thermal_residual.toFixed(2) }} °C</div>
            <div class="feature-desc">实测温度与模型预测温度的差值</div>
          </div>
        </div>
        
        <!-- 温度趋势图 -->
        <time-series-chart 
          v-if="featureTimeSeriesData.length > 0"
          :data="featureTimeSeriesData" 
          :timestamps="timeSeriesTimestamps"
          :chart-type="'temperature'"
          :chart-id="'temperature-chart'"
        />
      </div>
      
      <!-- 效率和电流相关特征卡片 -->
      <div class="card">
        <h3>效率与电流特征分析</h3>
        <div class="feature-grid">
          <div class="feature-item" :class="getFeatureClass(result.feature_scores.efficiency_residual)">
            <div class="feature-header">
              <span class="feature-name">效率残差</span>
              <span class="feature-score">{{ getFeatureStatusText(result.feature_scores.efficiency_residual) }}</span>
            </div>
            <div class="feature-value">{{ (result.features.efficiency_residual * 100).toFixed(2) }}%</div>
            <div class="feature-desc">实际效率与参考效率的差值，负值表示效率下降</div>
          </div>
          
          <div class="feature-item" :class="getFeatureClass(result.feature_scores.current_residual_trend)">
            <div class="feature-header">
              <span class="feature-name">电流残差趋势</span>
              <span class="feature-score">{{ getFeatureStatusText(result.feature_scores.current_residual_trend) }}</span>
            </div>
            <div class="feature-value">{{ result.features.current_residual_trend.toFixed(4) }}</div>
            <div class="feature-desc">电流残差的长期变化趋势，反映绝缘状态变化</div>
          </div>
          
          <div class="feature-item" :class="getFeatureClass(result.feature_scores.thermal_aging)">
            <div class="feature-header">
              <span class="feature-name">热老化累积</span>
              <span class="feature-score">{{ getFeatureStatusText(result.feature_scores.thermal_aging) }}</span>
            </div>
            <div class="feature-value">{{ result.features.thermal_aging.toFixed(1) }}</div>
            <div class="feature-desc">绝缘热老化累积量，反映长期温度对绝缘的影响</div>
          </div>
        </div>
        
        <!-- 特征参数时序变化图 -->
        <time-series-chart 
          v-if="featureTimeSeriesData.length > 0"
          :data="featureTimeSeriesData" 
          :timestamps="timeSeriesTimestamps"
          :chart-type="'efficiency'"
          :chart-id="'efficiency-chart'"
        />
      </div>
    </div>
    
    <!-- 数据格式帮助对话框 -->
    <el-dialog
      v-model="showDataFormatHelp"
      title="支持的数据格式"
      width="70%"
    >
      <data-format-helper format-type="insulation" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import axios from 'axios'

// 导入组件
import ThresholdConfig from '@/components/ThresholdConfig.vue'
import FeatureRadarChart from '@/components/FeatureRadarChart.vue'
import TimeSeriesChart from '@/components/TimeSeriesChart.vue'
import DataFormatHelper from '@/components/DataFormatHelper.vue'

// 状态变量
const file = ref(null)
const loading = ref(false)
const result = ref(null)
const showConfig = ref(false)
const showDataFormatHelp = ref(false)

// 阈值设置
const thresholds = reactive({
  degrading: 0.3,  // 绝缘劣化阈值
  critical: 0.7    // 绝缘危险阈值
})

// 时间序列数据
const timeSeriesData = reactive({
  temperature: [],
  efficiency: []
})

// 特征时序数据和时间戳
const featureTimeSeriesData = ref([])
const timeSeriesTimestamps = ref([])

// 响应式状态
const route = useRoute()

// 文件上传处理
const handleFileChange = (uploadFile) => {
  file.value = uploadFile.raw
}

const handleExceed = () => {
  ElMessage.warning('只能上传一个文件')
}

// 更新阈值
const updateThresholds = (newThresholds) => {
  Object.assign(thresholds, newThresholds)
}

// 开始分析
const handleAnalyze = async () => {
  if (!file.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  loading.value = true
  
  try {
    const formData = new FormData()
    formData.append('file', file.value)
    
    const response = await axios.post('/api/diagnosis/insulation', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    
    result.value = response.data
    
    // 生成时间序列数据（实际应用中可能从后端获取）
    generateTimeSeriesData()
    
    ElMessage.success('分析完成')
  } catch (error) {
    console.error('分析失败:', error)
    ElMessage.error(error.response?.data?.detail || '分析失败，请检查文件格式')
  } finally {
    loading.value = false
  }
}

// 下载示例文件
const downloadSampleFile = async (type) => {
  try {
    const response = await axios.get(`/api/samples/insulation/${type}`, {
      responseType: 'blob'
    })
    
    // 获取文件名
    const contentDisposition = response.headers['content-disposition']
    let filename = `insulation_${type}_sample.csv`
    
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="(.+?)"/)
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1]
      }
    }
    
    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    
  } catch (error) {
    console.error('下载示例文件失败:', error)
    ElMessage.error('下载示例文件失败')
  }
}

// 生成模拟时间序列数据（实际应用中应从后端获取）
const generateTimeSeriesData = () => {
  // 清空现有数据
  timeSeriesData.temperature = []
  timeSeriesData.efficiency = []
  featureTimeSeriesData.value = []
  timeSeriesTimestamps.value = []
  
  // 生成时间点
  const now = new Date()
  const points = 100
  
  // 为特征时序图准备时间戳
  for (let i = 0; i < points; i++) {
    const time = new Date(now.getTime() - (points - i) * 60000) // 每分钟一个点
    timeSeriesTimestamps.value.push(time)
  }
  
  // 生成温度数据
  for (let i = 0; i < points; i++) {
    const time = new Date(now.getTime() - (points - i) * 60000) // 每分钟一个点
    const baseTemp = 60 + Math.random() * 5
    
    // 根据状态调整温度趋势
    let temp = baseTemp
    if (result.value.status === 'DEGRADING') {
      temp += i * 0.05 // 缓慢上升
    } else if (result.value.status === 'CRITICAL') {
      temp += i * 0.1 // 快速上升
    }
    
    timeSeriesData.temperature.push({
      time: time.toISOString(),
      value: temp
    })
  }
  
  // 生成效率数据
  for (let i = 0; i < points; i++) {
    const time = new Date(now.getTime() - (points - i) * 60000)
    const baseEff = 0.92 - Math.random() * 0.02
    
    // 根据状态调整效率趋势
    let eff = baseEff
    if (result.value.status === 'DEGRADING') {
      eff -= i * 0.0002 // 缓慢下降
    } else if (result.value.status === 'CRITICAL') {
      eff -= i * 0.0005 // 快速下降
    }
    
    timeSeriesData.efficiency.push({
      time: time.toISOString(),
      value: eff
    })
  }
  
  // 生成特征时序数据
  generateFeatureTimeSeriesData(points, now)
}

// 生成特征时序数据
const generateFeatureTimeSeriesData = (points, now) => {
  // 基于当前特征值生成时序数据
  const features = result.value.features
  const status = result.value.status
  
  // 准备特征时序数据点
  for (let i = 0; i < points; i++) {
    // 计算变化因子，根据状态调整趋势
    const trendFactor = status === 'CRITICAL' ? 0.02 : 
                       status === 'DEGRADING' ? 0.01 : 0
    
    // 创建一个数据点
    const dataPoint = {
      // 绕组温度比率
      temp_ratio: features.temp_ratio * (0.9 + 0.1 * i / points + Math.random() * 0.02),
      
      // 温升速率
      temp_rise_rate: features.temp_rise_rate * (0.9 + 0.1 * i / points + Math.random() * 0.05),
      
      // 温度残差
      thermal_residual: features.thermal_residual * (0.9 + trendFactor * i + Math.random() * 0.1),
      
      // 效率残差
      efficiency_residual: features.efficiency_residual * (1 - trendFactor * i),
      
      // 电流残差趋势
      current_residual_trend: features.current_residual_trend * (0.9 + trendFactor * i + Math.random() * 0.05),
      
      // 热老化累积
      thermal_aging: features.thermal_aging * (0.95 + 0.05 * i / points + Math.random() * 0.02)
    }
    
    featureTimeSeriesData.value.push(dataPoint)
  }
}

// 获取状态对应的CSS类
const getStatusClass = (status) => {
  switch (status) {
    case 'HEALTHY': return 'status-normal'
    case 'DEGRADING': return 'status-warning'
    case 'WARNING': return 'status-warning'
    case 'CRITICAL': return 'status-fault'
    default: return ''
  }
}

// 获取状态文本
const getStatusText = (status) => {
  switch (status) {
    case 'HEALTHY': return '绝缘状态良好'
    case 'DEGRADING': return '绝缘开始劣化'
    case 'WARNING': return '绝缘劣化警告'
    case 'CRITICAL': return '绝缘状态危险'
    default: return '未知状态'
  }
}

// 获取特征状态对应的CSS类
const getFeatureClass = (score) => {
  if (score < 0.3) return 'feature-normal'
  if (score < 0.7) return 'feature-warning'
  return 'feature-fault'
}

// 获取特征状态文本
const getFeatureStatusText = (score) => {
  if (score < 0.3) return '正常'
  if (score < 0.7) return '警告'
  return '异常'
}

// 检查是否来自快速分析页面
const checkQuickAnalysis = () => {
  if (route.query.quickAnalysis === 'true') {
    // 从localStorage中获取分析结果
    const savedResult = localStorage.getItem('insulation_analysis_result')
    if (savedResult) {
      try {
        result.value = JSON.parse(savedResult)
        
        // 如果有预处理的图表数据，优先使用
        if (result.value.processed_time_series) {
          result.value.time_series = result.value.processed_time_series
        }
        
        if (result.value.processed_frequency_spectrum) {
          result.value.frequency_spectrum = result.value.processed_frequency_spectrum
        }
        
        // 处理图表数据
        processChartData(result.value)
        
        ElMessage.success('已加载最新分析结果')
        
        // 滚动到结果区域
        setTimeout(() => {
          const resultsContainer = document.querySelector('.results-container')
          if (resultsContainer) {
            resultsContainer.scrollIntoView({ behavior: 'smooth' })
          }
        }, 300)
      } catch (error) {
        console.error('解析保存的分析结果失败:', error)
        ElMessage.error('加载分析结果失败，请重新上传文件分析')
      }
    }
  }
}

// 监听路由变化，处理快速分析结果
watch(() => route.query, (newQuery) => {
  if (newQuery.quickAnalysis === 'true' && newQuery.timestamp) {
    checkQuickAnalysis()
  }
}, { immediate: true })

onMounted(() => {
  // 加载默认阈值配置
  const savedThresholds = localStorage.getItem('insulationThresholds')
  if (savedThresholds) {
    Object.assign(thresholds, JSON.parse(savedThresholds))
  }
  
  // 检查是否是从快速分析页面跳转过来的
  checkQuickAnalysis()
})
</script>

<style scoped>
.diagnosis-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  color: #303133;
}

.card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  padding: 20px;
  margin-bottom: 20px;
}

.upload-card {
  margin-top: 20px;
}

.upload-description {
  margin-bottom: 20px;
  color: #606266;
}

.upload-area {
  width: 100%;
}

.upload-actions {
  margin-top: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.selected-file {
  margin: 0;
  color: #606266;
}

.sample-file {
  margin-top: 20px;
}

.sample-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.sample-text {
  color: #606266;
}

.sample-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.results-container {
  margin-top: 30px;
}

.result-header {
  margin-bottom: 30px;
}

.status-box {
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.status-normal {
  background-color: rgba(103, 194, 58, 0.2);
  border-left: 4px solid #67C23A;
}

.status-warning {
  background-color: rgba(230, 162, 60, 0.2);
  border-left: 4px solid #E6A23C;
}

.status-fault {
  background-color: rgba(245, 108, 108, 0.2);
  border-left: 4px solid #F56C6C;
}

.status-box h3 {
  margin-top: 0;
}

.status-box p {
  margin: 0;
}

.gauge-container {
  position: relative;
  margin: 30px 0;
}

.gauge {
  height: 30px;
  background-color: #f5f5f5;
  border-radius: 15px;
  overflow: hidden;
  position: relative;
}

.gauge-fill {
  height: 100%;
  background: linear-gradient(90deg, #67C23A, #E6A23C, #F56C6C);
  transition: width 0.5s ease;
}

.gauge-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #333;
  font-weight: bold;
}

.threshold-markers {
  position: relative;
  height: 20px;
  width: 100%;
}

.threshold-marker {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
}

.threshold-marker .marker-line {
  height: 15px;
  width: 2px;
  background-color: #333;
}

.threshold-marker .marker-label {
  font-size: 12px;
  white-space: nowrap;
  transform: translateX(-50%);
  margin-top: 5px;
}

@media (max-width: 576px) {
  .threshold-marker .marker-label {
    font-size: 10px;
  }
}

.threshold-marker-warning .marker-line {
  background-color: #E6A23C;
}

.threshold-marker-fault .marker-line {
  background-color: #F56C6C;
}

.feature-radar {
  margin-top: 30px;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.feature-item {
  padding: 15px;
  border-radius: 8px;
}

.feature-normal {
  background-color: rgba(103, 194, 58, 0.1);
}

.feature-warning {
  background-color: rgba(230, 162, 60, 0.1);
}

.feature-fault {
  background-color: rgba(245, 108, 108, 0.1);
}

.feature-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 10px;
}

.feature-name {
  font-weight: bold;
}

.feature-score {
  font-size: 14px;
}

.feature-value {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 10px;
}

.feature-desc {
  font-size: 14px;
  color: #606266;
}

@media (max-width: 768px) {
  .result-header {
    flex-direction: column;
  }
  
  .gauge-container {
    width: 100%;
  }
  
  .feature-grid {
    grid-template-columns: 1fr;
  }
}
</style> 