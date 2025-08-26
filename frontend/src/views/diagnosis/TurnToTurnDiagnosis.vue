<template>
  <div class="diagnosis-container">
    <div class="page-header">
      <h2 class="page-title">匝间短路诊断</h2>
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
      <h3>电机数据分析</h3>
      <p class="upload-description">
        上传电机运行数据CSV文件，系统将分析是否存在匝间短路故障。
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
            请上传CSV格式的电机数据文件，支持传感器原始数据格式
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
            <el-button size="small" @click="downloadSampleFile('normal')">正常运行样本</el-button>
            <el-button size="small" @click="downloadSampleFile('warning')">预警样本</el-button>
            <el-button size="small" @click="downloadSampleFile('fault')">故障样本</el-button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 分析结果 -->
    <div v-if="result" class="results-container">
      <!-- 故障评分卡片 -->
      <div class="card">
        <h2>匝间短路诊断结果</h2>
        
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
        
        <!-- 特征参数雷达图 -->
        <feature-radar-chart 
          :features="result.features" 
          :thresholds="featureThresholds" 
        />
        
        <!-- 操作按钮 -->
        <div class="action-buttons">
          <el-button type="primary" @click="downloadReport">下载诊断报告</el-button>
          <el-button @click="reset">重新检测</el-button>
        </div>
      </div>
      
      <!-- 特征参数详情卡片 -->
      <div class="card">
        <div class="card-header">
          <h3>特征参数详情</h3>
          <el-button type="primary" link @click="showAllFeatures = !showAllFeatures">
            {{ showAllFeatures ? '显示主要特征' : '显示全部特征' }}
          </el-button>
        </div>
        
        <el-table :data="filteredFeatureTableData" stripe border>
          <el-table-column prop="name" label="参数名称" width="180" />
          <el-table-column prop="value" label="数值" width="120" />
          <el-table-column prop="description" label="描述" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag :type="getFeatureStatusType(scope.row)">
                {{ getFeatureStatusText(scope.row) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <!-- 时序图卡片 -->
      <div v-if="timeSeriesData.length > 0" class="card">
        <time-series-chart 
          :data="timeSeriesData" 
          :timestamps="timeSeriesTimestamps" 
          :chart-id="'turn-to-turn-chart'"
          :chart-type="'turn-to-turn'"
        />
      </div>
    </div>
    
    <!-- 无结果提示 -->
    <div v-else-if="analyzed && !result" class="card no-results">
      <el-empty description="分析未完成或出现错误">
        <template #description>
          <div class="error-message">
            <h4>处理文件时遇到问题</h4>
            <p v-if="errorMessage">{{ errorMessage }}</p>
            <p v-else>分析未完成或出现错误</p>
            
            <div class="error-suggestion">
              <p>建议尝试以下解决方案：</p>
              <ul>
                <li>检查您的CSV文件格式是否正确</li>
                <li>确保文件包含电机三相电流数据</li>
                <li>尝试下载并上传我们的示例文件测试系统</li>
              </ul>
            </div>
          </div>
        </template>
        <div class="error-actions">
          <el-button type="primary" @click="reset">重新尝试</el-button>
          <el-button @click="showDataFormatHelp = true">查看支持的数据格式</el-button>
          <el-button @click="downloadSampleFile('normal')">下载示例文件</el-button>
        </div>
      </el-empty>
    </div>
    
    <!-- 数据格式帮助对话框 -->
    <el-dialog
      v-model="showDataFormatHelp"
      title="数据格式说明"
      width="80%"
      destroy-on-close
    >
      <data-format-helper />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import api from '@/api'
import axios from 'axios' // 导入axios

// 导入自定义组件
import ThresholdConfig from '@/components/ThresholdConfig.vue'
import FeatureRadarChart from '@/components/FeatureRadarChart.vue'
import TimeSeriesChart from '@/components/TimeSeriesChart.vue'
import DataFormatHelper from '@/components/DataFormatHelper.vue'

// 状态变量
const file = ref(null)
const loading = ref(false)
const result = ref(null)
const featureTableData = ref([])
const showAllFeatures = ref(false)
const analyzed = ref(false)
const showConfig = ref(false)
const showDataFormatHelp = ref(false)
const errorMessage = ref('')
const timeSeriesData = ref([])
const timeSeriesTimestamps = ref([])

// 诊断阈值设置
const thresholds = ref({
  warning: 0.3,
  fault: 0.7
})

// 特征阈值设置
const featureThresholds = ref({
  I2_avg: 0.05,            // 负序电流平均值阈值
  I2_I1_ratio: 0.02,       // 负序/正序比值阈值
  unbalance_avg: 5.0,      // 电流不平衡度阈值(%)
  kurtosis_delta_iq: 3.0,  // ΔI_q峭度阈值
  delta_eta_avg: -0.03     // 效率残差平均值阈值
})

// 响应式状态
const route = useRoute()

// 更新阈值配置
const updateThresholds = (newConfig) => {
  if (newConfig.thresholds) {
    thresholds.value = { ...newConfig.thresholds }
  }
  
  if (newConfig.featureThresholds) {
    featureThresholds.value = { ...newConfig.featureThresholds }
  }
  
  // 如果已有结果，重新计算特征状态
  if (result.value) {
    prepareFeatureTableData()
  }
}

// 处理文件选择
const handleFileChange = (uploadFile) => {
  file.value = uploadFile.raw
}

// 处理超过文件限制
const handleExceed = () => {
  ElMessage.warning('只能上传一个文件')
}

// 处理文件分析
const handleAnalyze = async () => {
  if (!file.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  
  if (!file.value.name.endsWith('.csv')) {
    ElMessage.error('只支持CSV格式文件')
    return
  }
  
  loading.value = true
  analyzed.value = false
  errorMessage.value = ''
  
  try {
    // 调用API分析文件
    ElMessage.info('正在分析文件，这可能需要一些时间...')
    const response = await api.analyzeFile(file.value)
    result.value = response
    
    // 应用当前阈值重新判断状态
    result.value.status = calculateStatus(result.value.score)
    
    // 构建特征参数表格数据
    prepareFeatureTableData()
    
    // 模拟生成时序数据（实际项目中应从CSV文件解析）
    generateMockTimeSeriesData()
    
    ElMessage.success('分析完成')
    analyzed.value = true
  } catch (error) {
    // 显示详细的错误信息
    errorMessage.value = typeof error === 'string' ? error : '分析过程中发生未知错误'
    ElMessage.error(errorMessage.value)
    console.error('分析错误:', error)
    analyzed.value = true
    result.value = null
  } finally {
    loading.value = false
  }
}

// 根据当前阈值计算状态
const calculateStatus = (score) => {
  if (score >= thresholds.value.fault) {
    return 'FAULT'
  } else if (score >= thresholds.value.warning) {
    return 'WARNING'
  } else {
    return 'NORMAL'
  }
}

// 准备特征表格数据
const prepareFeatureTableData = () => {
  if (!result.value || !result.value.features) return
  
  // 定义特征参数描述映射
  const featureDescriptions = {
    I2_avg: '负序电流平均值',
    I2_max: '负序电流最大值',
    I2_I1_ratio: '负序/正序电流比值',
    unbalance_avg: '电流不平衡度平均值(%)',
    unbalance_max: '电流不平衡度最大值(%)',
    delta_I2_avg: '负序电流残差平均值',
    delta_I2_std: '负序电流残差标准差',
    kurtosis_delta_iq: 'ΔI_q滑动窗口峭度',
    delta_Iq_std: 'ΔI_q标准差',
    delta_eta_avg: '效率残差平均值',
    delta_eta_std: '效率残差标准差'
  }

  // 主要特征参数列表（用于精简视图）
  const mainFeatures = ['I2_avg', 'I2_I1_ratio', 'unbalance_avg', 'kurtosis_delta_iq', 'delta_eta_avg']
  
  // 构建表格数据
  featureTableData.value = Object.entries(result.value.features).map(([key, value]) => {
    // 计算特征状态
    let status = 'normal'
    
    // 检查是否超过阈值
    if (featureThresholds.value[key] !== undefined) {
      const threshold = featureThresholds.value[key]
      // 负值特征（如效率残差）判断方向相反
      if (key === 'delta_eta_avg') {
        if (value < threshold) status = 'warning'
        if (value < threshold * 1.5) status = 'fault'
      } else {
        if (value > threshold) status = 'warning'
        if (value > threshold * 1.5) status = 'fault'
      }
    }
    
    return {
      name: key,
      value: typeof value === 'number' ? value.toFixed(4) : value,
      description: featureDescriptions[key] || key,
      status,
      isMainFeature: mainFeatures.includes(key)
    }
  })
}

// 过滤特征表格数据（根据是否显示全部特征）
const filteredFeatureTableData = computed(() => {
  if (showAllFeatures.value) {
    return featureTableData.value
  } else {
    return featureTableData.value.filter(item => item.isMainFeature)
  }
})

// 获取状态对应的CSS类
const getStatusClass = (status) => {
  if (!status) return ''
  
  switch (status.toLowerCase()) {
    case 'normal': return 'status-normal'
    case 'warning': return 'status-warning'
    case 'fault': return 'status-fault'
    default: return ''
  }
}

// 获取状态对应的中文文本
const getStatusText = (status) => {
  if (!status) return '未知'
  
  switch (status.toLowerCase()) {
    case 'normal': return '正常'
    case 'warning': return '预警'
    case 'fault': return '故障'
    default: return '未知'
  }
}

// 获取特征状态对应的标签类型
const getFeatureStatusType = (feature) => {
  switch (feature.status) {
    case 'normal': return 'success'
    case 'warning': return 'warning'
    case 'fault': return 'danger'
    default: return 'info'
  }
}

// 获取特征状态对应的中文文本
const getFeatureStatusText = (feature) => {
  switch (feature.status) {
    case 'normal': return '正常'
    case 'warning': return '异常'
    case 'fault': return '故障'
    default: return '未知'
  }
}

// 下载诊断报告
const downloadReport = () => {
  if (!result.value) return
  
  // 生成报告内容
  const reportContent = generateReportContent()
  
  // 创建Blob对象
  const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' })
  
  // 创建下载链接
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `匝间短路诊断报告_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, '_')}.txt`
  link.click()
  
  // 释放URL对象
  URL.revokeObjectURL(link.href)
}

// 生成报告内容
const generateReportContent = () => {
  const r = result.value
  let content = '电机匝间短路诊断报告\n'
  content += '====================\n\n'
  content += `诊断时间: ${new Date().toLocaleString()}\n`
  content += `故障概率: ${(r.score * 100).toFixed(2)}%\n`
  content += `状态: ${getStatusText(r.status)}\n\n`
  content += '特征参数值:\n'
  content += '-----------------\n'
  
  // 添加特征参数
  for (const item of featureTableData.value) {
    content += `${item.description} (${item.name}): ${item.value} - ${getFeatureStatusText(item)}\n`
  }
  
  // 添加诊断建议
  content += '\n诊断建议:\n'
  content += '-----------------\n'
  
  if (r.status === 'NORMAL') {
    content += '电机运行正常，无需特别处理。建议按照维护计划定期检查电机状态。\n'
  } else if (r.status === 'WARNING') {
    content += '电机出现匝间短路早期预警信号，建议：\n'
    content += '1. 增加监测频率，特别关注负序电流和电流不平衡度变化趋势\n'
    content += '2. 在下次停机时安排绕组绝缘测试\n'
    content += '3. 准备备件，以防故障恶化\n'
  } else if (r.status === 'FAULT') {
    content += '电机存在匝间短路故障，建议：\n'
    content += '1. 尽快安排电机停机检修\n'
    content += '2. 对故障相绕组进行详细检测\n'
    content += '3. 评估故障原因，排除系统级故障隐患\n'
    content += '4. 更换或修复受损绕组\n'
  }
  
  return content
}

// 重置状态
const reset = () => {
  file.value = null
  result.value = null
  featureTableData.value = []
  timeSeriesData.value = []
  timeSeriesTimestamps.value = []
  analyzed.value = false
  errorMessage.value = ''
}

// 下载示例文件
const downloadSampleFile = async (type = 'normal') => {
  try {
    // 使用axios直接下载文件
    const response = await axios.get(`http://localhost:8000/samples/${type}`, {
      responseType: 'blob', // 重要：设置响应类型为blob
    });
    
    // 从响应头中获取文件名
    const contentDisposition = response.headers['content-disposition'];
    let filename = `${type}_sample.csv`;
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="(.+)"/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1];
      }
    }
    
    // 创建一个blob URL
    const blob = new Blob([response.data], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    
    // 创建一个隐藏的链接元素
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    
    // 点击链接下载文件
    link.click();
    
    // 清理
    window.URL.revokeObjectURL(url);
    document.body.removeChild(link);
    
    ElMessage.success(`已下载${type === 'normal' ? '正常' : type === 'warning' ? '预警' : '故障'}运行示例数据`);
  } catch (error) {
    console.error('下载示例文件失败:', error);
    ElMessage.error('下载示例文件失败，请稍后重试');
  }
}

// 生成模拟时序数据（实际应从CSV文件解析）
const generateMockTimeSeriesData = () => {
  // 清空现有数据
  timeSeriesData.value = []
  timeSeriesTimestamps.value = []
  
  // 数据点数量
  const pointCount = 50
  const now = new Date()
  
  // 模拟特征随时间的变化
  for (let i = 0; i < pointCount; i++) {
    // 基础参数随时间微小变化
    const timestamp = new Date(now.getTime() - (pointCount - i) * 60000) // 每分钟一个点
    timeSeriesTimestamps.value.push(timestamp)
    
    // 计算特征值，根据结果状态设置趋势
    const trendFactor = result.value.status === 'FAULT' ? 0.02 : 
                       result.value.status === 'WARNING' ? 0.01 : 0
    
    const point = {
      // 负序电流随时间微增
      I2_avg: result.value.features.I2_avg * (0.9 + 0.1 * i / pointCount + Math.random() * 0.02),
      
      // 负序/正序比值
      I2_I1_ratio: result.value.features.I2_I1_ratio * (0.9 + 0.1 * i / pointCount + Math.random() * 0.02),
      
      // 不平衡度
      unbalance_avg: result.value.features.unbalance_avg * (0.9 + 0.1 * i / pointCount + Math.random() * 0.05),
      
      // ΔI_q峭度
      kurtosis_delta_iq: result.value.features.kurtosis_delta_iq * (0.9 + trendFactor * i + Math.random() * 0.1),
      
      // 效率残差
      delta_eta_avg: result.value.features.delta_eta_avg * (1 - trendFactor * i)
    }
    
    timeSeriesData.value.push(point)
  }
}

// 检查是否来自快速分析页面
const checkQuickAnalysis = () => {
  if (route.query.quickAnalysis === 'true') {
    // 从localStorage中获取分析结果
    const savedResult = localStorage.getItem('turn-to-turn_analysis_result')
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
  const savedThresholds = localStorage.getItem('turnToTurnThresholds')
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

:deep(.el-upload-dragger) {
  width: 100%;
}

@media (max-width: 576px) {
  :deep(.el-upload__text) {
    font-size: 14px;
  }
  
  :deep(.el-icon--upload) {
    font-size: 48px !important;
  }
}

.selected-file {
  margin: 0;
  color: #606266;
}

.upload-actions {
  margin-top: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

@media (max-width: 576px) {
  .upload-actions {
    flex-direction: column;
    align-items: flex-start;
  }
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 10px;
}

.card-header h3 {
  margin: 0;
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

.status-box h3 {
  margin-top: 0;
}

.status-box p {
  margin: 0;
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

.threshold-marker.threshold-marker-warning .marker-line {
  background-color: #E6A23C;
}

.threshold-marker.threshold-marker-fault .marker-line {
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-header h3 {
  margin: 0;
}

.action-buttons {
  margin-top: 20px;
  display: flex;
  justify-content: center;
  gap: 20px;
}

.no-results {
  padding: 40px 20px;
  text-align: center;
}

.error-message {
  color: #F56C6C;
  margin-bottom: 10px;
}

.error-suggestion {
  margin-top: 20px;
  padding: 10px;
  background-color: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 4px;
  color: #e6a23c;
}

.error-suggestion ul {
  padding-left: 20px;
  margin: 10px 0;
}

.error-suggestion li {
  margin-bottom: 5px;
}

.error-actions {
  margin-top: 20px;
  display: flex;
  justify-content: center;
  gap: 10px;
}

/* 响应式表格调整 */
:deep(.el-table) {
  width: 100% !important;
  overflow-x: auto;
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