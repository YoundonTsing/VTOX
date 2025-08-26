<template>
  <div class="home-container">
    <!-- 配置面板 -->
    <div class="card">
      <div class="card-header">
        <h2>匝间短路诊断系统</h2>
        <el-switch
          v-model="showAdvancedSettings"
          active-text="高级设置"
          inactive-text="基本设置"
        />
      </div>
      
      <!-- 阈值配置面板 -->
      <threshold-config 
        v-if="showAdvancedSettings"
        @update:thresholds="updateThresholds"
      />
      
      <!-- 文件上传区域 -->
      <div class="upload-section">
        <h3>电机数据分析</h3>
        <p>上传电机运行数据CSV文件，系统将分析是否存在匝间短路故障。</p>
        
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
              请上传CSV格式的电机数据文件
            </div>
          </template>
        </el-upload>
        
        <div class="upload-actions" v-if="file">
          <p>已选择文件: {{ file.name }}</p>
          <el-button type="primary" @click="handleAnalyze" :loading="loading">
            {{ loading ? '分析中...' : '开始分析' }}
          </el-button>
        </div>
        
        <!-- 示例文件下载 -->
        <div class="sample-file">
          <el-divider content-position="left">示例数据</el-divider>
          <div class="sample-actions">
            <span>下载示例数据文件：</span>
            <el-button size="small" @click="downloadSampleFile">正常运行样本</el-button>
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
              <div class="threshold-marker warning" :style="{ left: `${thresholds.warning * 100}%` }">
                <div class="marker-line"></div>
                <div class="marker-label">预警阈值</div>
              </div>
              <div class="threshold-marker fault" :style="{ left: `${thresholds.fault * 100}%` }">
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
        />
      </div>
    </div>
    
    <!-- 无结果提示 -->
    <div v-else-if="analyzed && !result" class="card no-results">
      <el-empty description="分析未完成或出现错误">
        <el-button @click="reset">重新尝试</el-button>
      </el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import api from '@/api'

// 导入自定义组件
import ThresholdConfig from '@/components/ThresholdConfig.vue'
import FeatureRadarChart from '@/components/FeatureRadarChart.vue'
import TimeSeriesChart from '@/components/TimeSeriesChart.vue'

// 状态变量
const file = ref(null)
const loading = ref(false)
const result = ref(null)
const featureTableData = ref([])
const showAdvancedSettings = ref(false)
const showAllFeatures = ref(false)
const analyzed = ref(false)

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

// 时序数据（模拟数据，实际应从CSV文件中解析）
const timeSeriesData = ref([])
const timeSeriesTimestamps = ref([])

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
  
  try {
    // 调用API分析文件
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
    ElMessage.error(typeof error === 'string' ? error : '分析过程中发生错误')
    console.error('分析错误:', error)
    analyzed.value = true
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
}

// 下载示例文件
const downloadSampleFile = (type = 'normal') => {
  let csvContent = 'timestamp,Ia,Ib,Ic,Vdc,Torque,Speed,Iq_actual,Iq_ref,I2_ref,Eta_ref,Id_actual\n'
  
  // 根据不同类型生成示例数据
  const now = new Date()
  const samples = 100
  
  // 基础参数
  const baseParams = {
    normal: {
      I2: 0.02,
      unbalance: 2.0,
      kurtosis: 1.5,
      eta: 0.92
    },
    warning: {
      I2: 0.06,
      unbalance: 6.5,
      kurtosis: 3.2,
      eta: 0.89
    },
    fault: {
      I2: 0.12,
      unbalance: 9.5,
      kurtosis: 4.5,
      eta: 0.85
    }
  }
  
  const params = baseParams[type]
  
  for (let i = 0; i < samples; i++) {
    // 时间戳：每行递增1秒
    const timestamp = new Date(now.getTime() - (samples - i) * 1000).toISOString()
    
    // 基础电流值
    const baseIa = 10.0 + Math.random() * 0.5
    
    // 根据类型生成三相电流
    let ia, ib, ic
    
    if (type === 'normal') {
      // 正常：三相平衡
      ia = baseIa
      ib = baseIa * (1 + (Math.random() - 0.5) * 0.02)
      ic = baseIa * (1 + (Math.random() - 0.5) * 0.02)
    } else if (type === 'warning') {
      // 预警：轻微不平衡
      ia = baseIa
      ib = baseIa * (1 - 0.05 - Math.random() * 0.02)
      ic = baseIa * (1 + 0.03 + Math.random() * 0.02)
    } else {
      // 故障：明显不平衡
      ia = baseIa
      ib = baseIa * (1 - 0.12 - Math.random() * 0.03)
      ic = baseIa * (1 + 0.05 + Math.random() * 0.03)
    }
    
    // 其他参数
    const vdc = 380 + Math.random() * 5
    const torque = 150 + Math.random() * 10
    const speed = 3000 + Math.random() * 50
    const iqActual = 5.0 + Math.random() * 0.3
    const iqRef = 5.0
    const i2Ref = 0.02
    const etaRef = 0.93
    const idActual = 0.5 + Math.random() * 0.2
    
    // 添加到CSV内容
    csvContent += `${timestamp},${ia.toFixed(2)},${ib.toFixed(2)},${ic.toFixed(2)},${vdc.toFixed(2)},${torque.toFixed(2)},${speed.toFixed(2)},${iqActual.toFixed(2)},${iqRef.toFixed(2)},${i2Ref.toFixed(4)},${etaRef.toFixed(4)},${idActual.toFixed(2)}\n`
  }
  
  // 创建并下载CSV文件
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `电机数据示例_${type}_${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(link.href)
  
  ElMessage.success(`已下载${type === 'normal' ? '正常' : type === 'warning' ? '预警' : '故障'}运行示例数据`)
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
</script>

<style scoped>
.home-container {
  max-width: 1200px;
  margin: 0 auto;
}

.card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.card-header h2, .card-header h3 {
  margin: 0;
}

.upload-section {
  margin-top: 20px;
}

.upload-actions {
  margin-top: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sample-file {
  margin-top: 20px;
}

.sample-actions {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
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
  width: 100%;
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

.threshold-marker.warning .marker-line {
  background-color: #E6A23C;
}

.threshold-marker.fault .marker-line {
  background-color: #F56C6C;
}

.feature-section {
  margin: 30px 0;
}

.action-buttons {
  margin-top: 30px;
  display: flex;
  justify-content: center;
  gap: 20px;
}

.no-results {
  padding: 40px;
  text-align: center;
}
</style> 