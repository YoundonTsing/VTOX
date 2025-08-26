<template>
  <div class="diagnosis-container">
    <div class="page-header">
      <h2 class="page-title">轴承故障诊断</h2>
      <el-button type="primary" @click="showConfig = !showConfig">
        {{ showConfig ? '隐藏配置' : '阈值配置' }}
      </el-button>
    </div>

    <!-- 阈值配置面板 -->
    <el-collapse-transition>
      <div v-if="showConfig">
        <threshold-config @update:thresholds="updateThresholds" />
      </div>
    </el-collapse-transition>

    <!-- 文件上传区域 -->
    <div class="card upload-card">
      <h3>轴承数据分析</h3>
      <p class="upload-description">
        上传轴承振动数据CSV文件，系统将分析轴承是否存在内圈故障、外圈故障或滚动体故障。
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
            请上传CSV格式的轴承振动数据文件，支持传感器原始数据格式
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
            <el-button size="small" @click="downloadSampleFile('normal')">正常轴承样本</el-button>
            <el-button size="small" @click="downloadSampleFile('inner_race')">内圈故障样本</el-button>
            <el-button size="small" @click="downloadSampleFile('outer_race')">外圈故障样本</el-button>
            <el-button size="small" @click="downloadSampleFile('ball')">滚动体故障样本</el-button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 分析结果 -->
    <div v-if="result" class="results-container">
      <!-- 故障评分卡片 -->
      <div class="card">
        <h2>轴承故障诊断结果</h2>
        
        <!-- 故障评分和状态 -->
        <div class="result-header">
          <div class="status-box" :class="getStatusClass(result.status)">
            <h3>状态: {{ getStatusText(result.status) }}</h3>
            <p>故障概率: {{ (result.score * 100).toFixed(1) }}%</p>
          </div>
          
          <!-- 故障评分仪表盘 -->
          <div class="gauge-container">
            <div class="gauge">
              <div class="gauge-fill" :style="{ width: `${result.score * 100}%` }"></div>
              <div class="gauge-text">{{ (result.score * 100).toFixed(1) }}%</div>
            </div>
            <div class="threshold-markers">
              <div class="threshold-marker threshold-marker-warning" :style="{ left: `${thresholds.warning * 100}%` }">
                <div class="marker-line"></div>
                <div class="marker-label">预警阈值</div>
              </div>
              <div class="threshold-marker threshold-marker-fault" :style="{ left: `${thresholds.fault * 100}%` }">
                <div class="marker-line"></div>
                <div class="marker-label">故障阈值</div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 故障类型分析 -->
        <div class="fault-types">
          <h3>轴承故障类型分析</h3>
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="fault-type-card" :class="{ 'active': result.fault_type === 'inner_race' }">
                <div class="fault-icon">
                  <el-icon><warning /></el-icon>
                </div>
                <h4>内圈故障</h4>
                <p class="fault-prob">概率: {{ (result.fault_probabilities?.inner_race * 100 || 0).toFixed(1) }}%</p>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="fault-type-card" :class="{ 'active': result.fault_type === 'outer_race' }">
                <div class="fault-icon">
                  <el-icon><warning /></el-icon>
                </div>
                <h4>外圈故障</h4>
                <p class="fault-prob">概率: {{ (result.fault_probabilities?.outer_race * 100 || 0).toFixed(1) }}%</p>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="fault-type-card" :class="{ 'active': result.fault_type === 'ball' }">
                <div class="fault-icon">
                  <el-icon><warning /></el-icon>
                </div>
                <h4>滚动体故障</h4>
                <p class="fault-prob">概率: {{ (result.fault_probabilities?.ball * 100 || 0).toFixed(1) }}%</p>
              </div>
            </el-col>
          </el-row>
        </div>
        
        <!-- 特征参数雷达图 -->
        <div class="radar-chart-container">
          <h3>特征参数分析</h3>
          <div class="chart-wrapper">
            <radar-chart :chart-data="radarChartData" />
          </div>
        </div>
        
        <!-- 时域/频域图表 -->
        <el-tabs type="border-card">
          <el-tab-pane label="时域波形">
            <line-chart
              :chart-data="timeSeriesData"
              chart-id="time-series-chart"
              :height="150"
              :options="timeChartOptions"
            />
          </el-tab-pane>
          <el-tab-pane label="频谱分析">
            <line-chart
              :chart-data="frequencySpectrumData"
              chart-id="frequency-spectrum-chart"
              :height="150"
              :options="freqChartOptions"
            />
          </el-tab-pane>
          <el-tab-pane label="包络谱分析">
            <line-chart
              :chart-data="envelopeSpectrumData"
              chart-id="envelope-spectrum-chart"
              :height="150"
              :options="envelopeChartOptions"
            />
          </el-tab-pane>
        </el-tabs>
        
        <!-- 详细特征值列表 -->
        <div class="features-table">
          <h3>特征参数详细信息</h3>
          <el-table :data="featureTableData" stripe style="width: 100%">
            <el-table-column prop="name" label="特征名称" min-width="200" />
            <el-table-column prop="value" label="数值" width="120" />
            <el-table-column prop="normal_range" label="正常范围" width="150" />
            <el-table-column prop="description" label="描述" min-width="250" />
            <el-table-column label="状态" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.status === 'normal' ? 'success' : (scope.row.status === 'warning' ? 'warning' : 'danger')">
                  {{ scope.row.status === 'normal' ? '正常' : (scope.row.status === 'warning' ? '预警' : '异常') }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
        
        <!-- 诊断建议 -->
        <div class="diagnosis-suggestions">
          <h3>诊断结论与建议</h3>
          <div class="suggestion-content">
            <p v-html="result.diagnosis_conclusion"></p>
            <ul>
              <li v-for="(suggestion, index) in result.suggestions" :key="index">
                {{ suggestion }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 数据格式帮助对话框 -->
    <el-dialog
      v-model="showDataFormatHelp"
      title="支持的数据格式"
      width="60%"
      align-center
    >
      <div class="data-format-help">
        <h3>CSV文件要求</h3>
        <p>上传的CSV文件需要包含以下列：</p>
        <ul>
          <li><strong>时间戳</strong>：采样时间，可以是相对时间或绝对时间</li>
          <li><strong>振动数据</strong>：至少包含一列振动数据，例如加速度值</li>
          <li><strong>转速</strong>（可选）：电机转速值，单位为RPM</li>
          <li><strong>负载</strong>（可选）：电机负载百分比</li>
        </ul>
        
        <h3>示例数据格式</h3>
        <pre>
时间,加速度X,加速度Y,加速度Z,转速,负载
0.000,0.123,0.456,0.789,1500,80
0.001,0.124,0.457,0.790,1500,80
...
        </pre>
        
        <h3>数据采集要求</h3>
        <ul>
          <li>采样率：至少10kHz</li>
          <li>持续时间：至少1秒的连续数据</li>
          <li>传感器位置：靠近轴承安装位置</li>
        </ul>
      </div>
    </el-dialog>
    
    <!-- 诊断失败提示 -->
    <el-dialog
      v-model="showErrorDialog"
      title="诊断失败"
      width="30%"
      align-center
    >
      <span>{{ errorMessage }}</span>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showErrorDialog = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { UploadFilled, Warning } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import ThresholdConfig from '@/components/ThresholdConfig.vue'
import RadarChart from '@/components/charts/RadarChart.vue'
import LineChart from '@/components/charts/LineChart.vue'

// 响应式状态
const route = useRoute()
const file = ref(null)
const loading = ref(false)
const result = ref(null)
const showConfig = ref(false)
const showDataFormatHelp = ref(false)
const showErrorDialog = ref(false)
const errorMessage = ref('')

// 阈值配置
const thresholds = reactive({
  warning: 0.5,  // 预警阈值
  fault: 0.75    // 故障阈值
})

// 图表数据
const timeSeriesData = ref(null)
const frequencySpectrumData = ref(null)
const envelopeSpectrumData = ref(null)
const radarChartData = ref(null)
const featureTableData = ref([])

// 图表配置
const timeChartOptions = {
  responsive: true,
  scales: {
    x: {
      title: {
        display: true,
        text: '时间 (s)'
      }
    },
    y: {
      title: {
        display: true,
        text: '振幅'
      }
    }
  },
  plugins: {
    title: {
      display: true,
      text: '时域波形'
    }
  }
}

const freqChartOptions = {
  responsive: true,
  scales: {
    x: {
      title: {
        display: true,
        text: '频率 (Hz)'
      }
    },
    y: {
      title: {
        display: true,
        text: '幅值'
      },
      type: 'logarithmic'
    }
  },
  plugins: {
    title: {
      display: true,
      text: '频谱分析'
    }
  }
}

const envelopeChartOptions = {
  responsive: true,
  scales: {
    x: {
      title: {
        display: true,
        text: '频率 (Hz)'
      }
    },
    y: {
      title: {
        display: true,
        text: '幅值'
      },
      type: 'logarithmic'
    }
  },
  plugins: {
    title: {
      display: true,
      text: '包络谱分析'
    }
  }
}

// 文件处理方法
const handleFileChange = (uploadFile) => {
  file.value = uploadFile.raw
}

const handleExceed = () => {
  ElMessage.warning('只能上传一个文件')
}

// 开始分析
const handleAnalyze = async () => {
  if (!file.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  loading.value = true
  const formData = new FormData()
  formData.append('file', file.value)
  
  try {
    const response = await axios.post('http://localhost:8000/diagnosis/bearing', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    
    result.value = response.data
    
    // 处理图表数据
    processChartData(response.data)
    
    // 处理特征表格数据
    processFeatureTableData(response.data.features)
    
    loading.value = false
  } catch (error) {
    loading.value = false
    console.error('分析失败:', error)
    errorMessage.value = error.response?.data?.detail || '分析过程中发生未知错误'
    showErrorDialog.value = true
  }
}

// 处理图表数据
const processChartData = (data) => {
  // 时域波形数据
  if (data.time_series) {
    timeSeriesData.value = {
      labels: data.time_series.time,
      datasets: [
        {
          label: '振动信号',
          data: data.time_series.values,
          borderColor: '#409EFF',
          backgroundColor: 'rgba(64, 158, 255, 0.1)',
          borderWidth: 1,
          pointRadius: 0
        }
      ]
    }
  }
  
  // 频域数据
  if (data.frequency_spectrum) {
    frequencySpectrumData.value = {
      labels: data.frequency_spectrum.frequency,
      datasets: [
        {
          label: '频谱',
          data: data.frequency_spectrum.amplitude,
          borderColor: '#67C23A',
          backgroundColor: 'rgba(103, 194, 58, 0.1)',
          borderWidth: 1,
          pointRadius: 0
        }
      ]
    }
  }
  
  // 包络谱数据
  if (data.envelope_spectrum) {
    envelopeSpectrumData.value = {
      labels: data.envelope_spectrum.frequency,
      datasets: [
        {
          label: '包络谱',
          data: data.envelope_spectrum.amplitude,
          borderColor: '#E6A23C',
          backgroundColor: 'rgba(230, 162, 60, 0.1)',
          borderWidth: 1,
          pointRadius: 0
        }
      ]
    }
  }
  
  // 雷达图数据
  if (data.features) {
    const features = Object.keys(data.features).filter(key => 
      typeof data.features[key] === 'number' && 
      !['inner_race_prob', 'outer_race_prob', 'ball_prob', 'normal_prob'].includes(key)
    ).slice(0, 6)  // 取前6个特征
    
    radarChartData.value = {
      labels: features.map(f => formatFeatureName(f)),
      datasets: [
        {
          label: '当前值',
          data: features.map(f => data.features[f]),
          backgroundColor: 'rgba(64, 158, 255, 0.2)',
          borderColor: '#409EFF',
          pointBackgroundColor: '#409EFF'
        },
        {
          label: '正常范围',
          data: features.map(() => 0.5),  // 示例正常范围值
          backgroundColor: 'rgba(103, 194, 58, 0.2)',
          borderColor: '#67C23A',
          pointBackgroundColor: '#67C23A'
        }
      ]
    }
  }
}

// 处理特征表格数据
const processFeatureTableData = (features) => {
  if (!features) return
  
  featureTableData.value = Object.keys(features)
    .filter(key => typeof features[key] === 'number')
    .map(key => {
      // 示例特征状态判断逻辑，实际项目中应根据具体阈值判断
      let status = 'normal'
      if (key.includes('kurtosis') && features[key] > 4) status = 'warning'
      if (key.includes('rms') && features[key] > 1.5) status = 'fault'
      
      return {
        name: formatFeatureName(key),
        value: features[key].toFixed(4),
        normal_range: getNormalRange(key),
        description: getFeatureDescription(key),
        status: status
      }
    })
}

// 格式化特征名称
const formatFeatureName = (name) => {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase())
}

// 获取特征的正常范围（示例）
const getNormalRange = (feature) => {
  const ranges = {
    rms: '< 1.0',
    kurtosis: '< 3.0',
    crest_factor: '2.0 - 6.0',
    skewness: '-0.5 - 0.5',
    peak_to_peak: '< 5.0',
    variance: '< 2.0'
  }
  
  for (const key in ranges) {
    if (feature.includes(key)) return ranges[key]
  }
  
  return '0.0 - 1.0'
}

// 获取特征描述（示例）
const getFeatureDescription = (feature) => {
  const descriptions = {
    rms: '均方根值，表示振动信号的能量水平',
    kurtosis: '峭度，描述信号分布的尖峰程度',
    crest_factor: '峰值因子，表示信号峰值与均方根的比值',
    skewness: '偏度，描述信号分布的不对称性',
    peak_to_peak: '峰峰值，表示信号最大值与最小值之差',
    variance: '方差，表示信号波动程度',
    inner_race_prob: '内圈故障概率',
    outer_race_prob: '外圈故障概率',
    ball_prob: '滚动体故障概率',
    normal_prob: '正常状态概率'
  }
  
  for (const key in descriptions) {
    if (feature.includes(key)) return descriptions[key]
  }
  
  return '特征参数'
}

// 更新阈值
const updateThresholds = (newThresholds) => {
  Object.assign(thresholds, newThresholds)
}

// 获取状态类名
const getStatusClass = (status) => {
  switch (status) {
    case 'normal': return 'status-normal'
    case 'warning': return 'status-warning'
    case 'fault': return 'status-fault'
    default: return ''
  }
}

// 获取状态文本
const getStatusText = (status) => {
  switch (status) {
    case 'normal': return '正常'
    case 'warning': return '预警'
    case 'fault': return '故障'
    default: return '未知'
  }
}

// 下载示例文件
const downloadSampleFile = (type) => {
  window.open(`http://localhost:8000/samples/bearing/${type}`, '_blank')
}

// 检查是否来自快速分析页面
const checkQuickAnalysis = () => {
  if (route.query.quickAnalysis === 'true') {
    // 从localStorage中获取分析结果
    const savedResult = localStorage.getItem('bearing_analysis_result')
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
        
        if (result.value.processed_envelope_spectrum) {
          result.value.envelope_spectrum = result.value.processed_envelope_spectrum
        }
        
        // 处理图表数据
        processChartData(result.value)
        
        // 处理特征表格数据
        processFeatureTableData(result.value.features)
        
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
  const savedThresholds = localStorage.getItem('bearingThresholds')
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
  font-size: 24px;
  color: #303133;
  margin: 0;
}

.card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  padding: 20px;
  margin-bottom: 20px;
}

.upload-card {
  padding-bottom: 30px;
}

.upload-description {
  margin: 15px 0;
  color: #606266;
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
  flex-wrap: wrap;
  gap: 10px;
}

.results-container {
  margin-top: 30px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 20px;
}

.status-box {
  padding: 20px;
  border-radius: 8px;
  color: #fff;
  min-width: 200px;
}

.status-normal {
  background-color: #67C23A;
}

.status-warning {
  background-color: #E6A23C;
}

.status-fault {
  background-color: #F56C6C;
}

.gauge-container {
  flex: 1;
  min-width: 300px;
  position: relative;
  padding: 0 10px;
}

.gauge {
  height: 30px;
  background-color: #f5f7fa;
  border-radius: 15px;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gauge-fill {
  height: 100%;
  background: linear-gradient(to right, #67C23A, #E6A23C, #F56C6C);
  border-radius: 15px;
  transition: width 0.5s;
  position: absolute;
  left: 0;
  top: 0;
  z-index: 1;
}

.gauge-text {
  position: relative;
  z-index: 2;
  color: #303133;
  font-weight: bold;
  text-align: center;
  width: 100%;
}

.threshold-markers {
  position: relative;
  height: 30px;
}

.threshold-marker {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
}

.marker-line {
  width: 2px;
  height: 10px;
  background-color: #303133;
}

.marker-label {
  font-size: 12px;
  white-space: nowrap;
  color: #606266;
}

.threshold-marker-warning .marker-line {
  background-color: #E6A23C;
}

.threshold-marker-fault .marker-line {
  background-color: #F56C6C;
}

.fault-types {
  margin: 30px 0;
}

.fault-type-card {
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #EBEEF5;
  text-align: center;
  transition: all 0.3s;
}

.fault-type-card.active {
  border-color: #F56C6C;
  box-shadow: 0 0 10px rgba(245, 108, 108, 0.3);
}

.fault-icon {
  font-size: 30px;
  color: #909399;
  margin-bottom: 10px;
}

.fault-type-card.active .fault-icon {
  color: #F56C6C;
}

.fault-prob {
  margin-top: 5px;
  color: #606266;
}

.radar-chart-container {
  margin: 30px 0;
}

.chart-wrapper {
  height: 300px;
}

.features-table {
  margin: 30px 0;
}

.diagnosis-suggestions {
  margin-top: 30px;
}

.suggestion-content {
  padding: 15px;
  border-left: 4px solid #409EFF;
  background-color: #f5f7fa;
  border-radius: 0 4px 4px 0;
}

.data-format-help pre {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
}
</style> 