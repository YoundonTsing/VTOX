<template>
  <div class="diagnosis-container">
    <div class="page-header">
      <h2 class="page-title">断条故障诊断</h2>
      <el-button type="primary" @click="showConfig = !showConfig">
        {{ showConfig ? '隐藏配置' : '阈值配置' }}
      </el-button>
    </div>

    <!-- 阈值配置面板 -->
    <el-collapse-transition>
      <div v-if="showConfig">
        <threshold-config config-type="broken-bar" @update:thresholds="updateThresholds" />
      </div>
    </el-collapse-transition>

    <!-- 文件上传区域 -->
    <div class="card upload-card">
      <h3>断条故障分析</h3>
      <p class="upload-description">
        上传电机三相电流数据CSV文件，系统将基于MCSA（电机电流特征分析）方法检测转子导条断裂故障。
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
            请上传CSV格式的电机电流数据文件，支持常见的电机监测仪器格式
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
            <el-button size="small" @click="downloadSampleFile('normal')">正常电机样本</el-button>
            <el-button size="small" @click="downloadSampleFile('broken_bar')">断条故障样本</el-button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 分析结果 -->
    <div v-if="result" class="results-container">
      <!-- 故障评分卡片 -->
      <div class="card">
        <h2>断条故障诊断结果</h2>
        
        <!-- 故障评分和状态 -->
        <div class="result-header">
          <div class="status-box" :class="getStatusClass(result.status)">
            <h3>状态: {{ getStatusText(result.status) }}</h3>
            <p>故障评分: {{ (result.score * 100).toFixed(1) }}%</p>
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
        
        <!-- 断条故障特征指标 -->
        <div class="broken-bar-features">
          <h3>特征指标分析</h3>
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="feature-card" :class="{ 'feature-warning': result.features?.sideband_ratio > thresholds.warning }">
                <div class="feature-title">边带幅值比</div>
                <div class="feature-value">{{ (result.features?.sideband_ratio * 100).toFixed(2) }}%</div>
                <div class="feature-desc">断条特征频率边带与基频幅值比</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="feature-card" :class="{ 'feature-warning': result.features?.normalized_fault_index > thresholds.warning }">
                <div class="feature-title">归一化故障指数</div>
                <div class="feature-value">{{ (result.features?.normalized_fault_index * 100).toFixed(2) }}%</div>
                <div class="feature-desc">边带幅值总和与基频幅值比</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="feature-card" :class="{ 'feature-warning': result.features?.broken_bar_count > 0 }">
                <div class="feature-title">估计断条数量</div>
                <div class="feature-value">{{ result.features?.broken_bar_count || 0 }}</div>
                <div class="feature-desc">根据边带比例估计的断条数</div>
              </div>
            </el-col>
          </el-row>
        </div>
        
        <!-- 时域/频域图表 -->
        <el-tabs type="border-card">
          <el-tab-pane label="电流波形">
            <line-chart
              :chart-data="timeSeriesData"
              chart-id="current-time-chart"
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
          <el-tab-pane label="边带放大视图">
            <line-chart
              :chart-data="sidebandZoomData"
              chart-id="sideband-zoom-chart"
              :height="150"
              :options="sidebandOptions"
            />
          </el-tab-pane>
        </el-tabs>
        
        <!-- 转子槽频率指标 -->
        <div class="card sub-card" v-if="result.features?.slot_harmonics">
          <h3>转子槽谐波分析</h3>
          <p>转子槽谐波分析可辅助判断断条故障严重程度和位置。</p>
          
          <el-table :data="slotHarmonicsData" stripe style="width: 100%">
            <el-table-column prop="name" label="谐波名称" min-width="180" />
            <el-table-column prop="frequency" label="频率 (Hz)" width="120" />
            <el-table-column prop="amplitude" label="幅值比" width="120" />
            <el-table-column prop="phase" label="相位 (°)" width="120" />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="scope">
                <el-tag :type="scope.row.status === 'normal' ? 'success' : (scope.row.status === 'warning' ? 'warning' : 'danger')">
                  {{ scope.row.status === 'normal' ? '正常' : (scope.row.status === 'warning' ? '预警' : '异常') }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
        
        <!-- 断条特征频率分析 -->
        <div class="card sub-card">
          <h3>断条特征频率分析</h3>
          <div class="feature-freq-info">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="供电频率 (fs)">
                {{ result.features?.power_supply_freq.toFixed(2) }} Hz
              </el-descriptions-item>
              <el-descriptions-item label="转子转速">
                {{ result.features?.rotor_speed.toFixed(2) }} RPM
              </el-descriptions-item>
              <el-descriptions-item label="转差率 (s)">
                {{ (result.features?.slip * 100).toFixed(4) }}%
              </el-descriptions-item>
              <el-descriptions-item label="特征频率振荡">
                {{ (2 * result.features?.slip * result.features?.power_supply_freq).toFixed(4) }} Hz
              </el-descriptions-item>
              <el-descriptions-item label="左侧边带频率">
                {{ result.features?.left_sideband_freq.toFixed(2) }} Hz
              </el-descriptions-item>
              <el-descriptions-item label="右侧边带频率">
                {{ result.features?.right_sideband_freq.toFixed(2) }} Hz
              </el-descriptions-item>
            </el-descriptions>
          </div>
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
          <li><strong>三相电流</strong>：Ia、Ib、Ic或其他表示三相电流的列名</li>
          <li><strong>转速</strong>（可选）：电机转速值，单位为RPM</li>
          <li><strong>负载</strong>（可选）：电机负载百分比</li>
        </ul>
        
        <h3>示例数据格式</h3>
        <pre>
时间,Ia,Ib,Ic,转速,负载
0.000,3.423,3.756,-7.289,1500,80
0.001,4.125,2.958,-7.192,1500,80
...
        </pre>
        
        <h3>数据采集要求</h3>
        <ul>
          <li>采样率：建议至少10kHz</li>
          <li>持续时间：至少包含10个电源周期的连续数据</li>
          <li>分辨率：建议16位或以上ADC</li>
          <li>电机状态：正常负载运行（建议30%以上额定负载）</li>
        </ul>
        
        <h3>断条故障MCSA诊断原理</h3>
        <p>转子断条故障会在频谱中产生特征边带分量，其频率为：</p>
        <div class="formula">f<sub>bb</sub> = f<sub>s</sub> ± 2sf<sub>s</sub></div>
        <p>其中 f<sub>s</sub> 是电源频率，s 是转差率。这些边带的幅值与基波幅值的比例是判断断条故障的关键指标。</p>
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
import { ref, reactive, computed, onMounted, onBeforeMount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { UploadFilled, Warning } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import ThresholdConfig from '@/components/ThresholdConfig.vue'
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
  warning: 0.05,  // 预警阈值 - 断条特征比值通常较小
  fault: 0.1      // 故障阈值
})

// 图表数据
const timeSeriesData = ref(null)
const frequencySpectrumData = ref(null)
const sidebandZoomData = ref(null)
const slotHarmonicsData = ref([])

// 图表配置
const timeChartOptions = {
  responsive: true,
  scales: {
    x: {
      title: {
        display: true,
        text: '时间 (s)'
      },
      grid: {
        display: true,
        drawBorder: true,
        color: 'rgba(200, 200, 200, 0.3)',
        lineWidth: 0.5
      }
    },
    y: {
      title: {
        display: true,
        text: '电流 (A)'
      },
      grid: {
        display: true,
        drawBorder: true,
        color: 'rgba(200, 200, 200, 0.3)',
        lineWidth: 0.5
      }
    }
  },
  plugins: {
    title: {
      display: true,
      text: '电流波形'
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
      },
      grid: {
        display: true,
        drawBorder: true,
        color: 'rgba(200, 200, 200, 0.3)',
        lineWidth: 0.5
      }
    },
    y: {
      title: {
        display: true,
        text: '幅值'
      },
      type: 'logarithmic',
      grid: {
        display: true,
        drawBorder: true,
        color: 'rgba(200, 200, 200, 0.3)',
        lineWidth: 0.5
      }
    }
  },
  plugins: {
    title: {
      display: true,
      text: '电流频谱分析'
    },
    tooltip: {
      callbacks: {
        label: function(context) {
          let label = context.dataset.label || '';
          if (label) {
            label += ': ';
          }
          if (context.parsed.y !== null) {
            label += context.parsed.y.toExponential(2);
          }
          return label;
        }
      }
    }
  }
}

const sidebandOptions = reactive({
  responsive: true,
  scales: {
    x: {
      title: {
        display: true,
        text: '频率 (Hz)'
      },
      grid: {
        display: true,
        drawBorder: true,
        color: 'rgba(200, 200, 200, 0.3)',
        lineWidth: 0.5
      }
    },
    y: {
      title: {
        display: true,
        text: '幅值'
      },
      type: 'logarithmic',
      grid: {
        display: true,
        drawBorder: true,
        color: 'rgba(200, 200, 200, 0.3)',
        lineWidth: 0.5
      }
    }
  },
  plugins: {
    title: {
      display: true,
      text: '断条特征边带分析'
    }
  }
})

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
    const response = await axios.post('http://localhost:8000/diagnosis/broken-bar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    
    result.value = response.data
    
    // 处理图表数据
    processChartData(response.data)
    
    // 处理转子槽谐波数据
    if (response.data.features?.slot_harmonics) {
      processSlotHarmonicsData(response.data.features.slot_harmonics)
    }
    
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
          label: '电流信号',
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
    
    // 生成边带放大视图数据
    generateSidebandZoomData(data)
  }
}

// 生成边带放大视图数据
const generateSidebandZoomData = (data) => {
  if (!data.features || !data.frequency_spectrum) return
  
  const fs = data.features.power_supply_freq
  const leftSidebandFreq = data.features.left_sideband_freq
  const rightSidebandFreq = data.features.right_sideband_freq
  
  // 确定显示范围 (fs ± 5Hz)
  const minFreq = Math.max(0, leftSidebandFreq - 2)
  const maxFreq = rightSidebandFreq + 2
  
  // 从频谱中提取对应的数据
  const freqs = data.frequency_spectrum.frequency
  const amps = data.frequency_spectrum.amplitude
  const zoomFreqs = []
  const zoomAmps = []
  
  for (let i = 0; i < freqs.length; i++) {
    if (freqs[i] >= minFreq && freqs[i] <= maxFreq) {
      zoomFreqs.push(freqs[i])
      zoomAmps.push(amps[i])
    }
  }
  
  // 检查是否有足够的数据点
  if (zoomFreqs.length === 0) {
    console.warn('边带放大视图没有数据点')
    return
  }
  
  // 找到最接近电源频率的点
  let fsIndex = -1
  let minDiff = Number.MAX_VALUE
  for (let i = 0; i < zoomFreqs.length; i++) {
    const diff = Math.abs(zoomFreqs[i] - fs)
    if (diff < minDiff) {
      minDiff = diff
      fsIndex = i
    }
  }
  
  // 找到最大幅值，用于设置标记点高度
  const maxAmp = Math.max(...zoomAmps)
  
  // 准备三个频率点的数据数组
  const fsPts = new Array(zoomFreqs.length).fill(null)
  const leftPts = new Array(zoomFreqs.length).fill(null)
  const rightPts = new Array(zoomFreqs.length).fill(null)
  
  // 只在最接近的点处设置值
  if (fsIndex >= 0) {
    fsPts[fsIndex] = maxAmp
  }
  
  // 左边带和右边带
  for (let i = 0; i < zoomFreqs.length; i++) {
    if (Math.abs(zoomFreqs[i] - leftSidebandFreq) < 0.5) {
      leftPts[i] = maxAmp * 0.8
    }
    if (Math.abs(zoomFreqs[i] - rightSidebandFreq) < 0.5) {
      rightPts[i] = maxAmp * 0.8
    }
  }
  
  // 边带放大视图数据
  sidebandZoomData.value = {
    labels: zoomFreqs,
    datasets: [
      {
        label: '频谱',
        data: zoomAmps,
        borderColor: '#E6A23C',
        backgroundColor: 'rgba(230, 162, 60, 0.1)',
        borderWidth: 1,
        pointRadius: 0
      },
      // 添加三个特殊点作为边带标记
      {
        label: '电源频率',
        data: fsPts,
        borderColor: 'rgba(255, 99, 132, 0.8)',
        backgroundColor: 'rgba(255, 99, 132, 0.8)',
        borderWidth: 0,
        pointRadius: 5,
        pointStyle: 'triangle'
      },
      {
        label: '左边带',
        data: leftPts,
        borderColor: 'rgba(75, 192, 192, 0.8)',
        backgroundColor: 'rgba(75, 192, 192, 0.8)',
        borderWidth: 0,
        pointRadius: 5,
        pointStyle: 'circle'
      },
      {
        label: '右边带',
        data: rightPts,
        borderColor: 'rgba(75, 192, 192, 0.8)',
        backgroundColor: 'rgba(75, 192, 192, 0.8)',
        borderWidth: 0,
        pointRadius: 5,
        pointStyle: 'circle'
      }
    ]
  }
  
  console.log('边带放大视图数据已生成', {
    freqRange: [minFreq, maxFreq],
    dataPoints: zoomFreqs.length,
    keyFrequencies: {
      fs: fs,
      fsDisplayed: fsIndex >= 0,
      leftSideband: leftSidebandFreq,
      rightSideband: rightSidebandFreq
    }
  })
}

// 处理转子槽谐波数据
const processSlotHarmonicsData = (slotHarmonics) => {
  if (!slotHarmonics) return
  
  slotHarmonicsData.value = Object.keys(slotHarmonics).map(key => {
    const harmonic = slotHarmonics[key]
    // 调整预警阈值，只有幅值超过0.03才判断为异常
    const status = harmonic.amplitude > 0.03 ? 'warning' : 'normal'
    
    return {
      name: formatHarmonicName(key),
      frequency: harmonic.frequency.toFixed(2),
      amplitude: harmonic.amplitude.toFixed(4),
      phase: harmonic.phase?.toFixed(2) || '-',
      status: status
    }
  })
  
  // 检查是否所有转子槽谐波都正常，但故障评分很高
  const allNormal = slotHarmonicsData.value.every(item => item.status === 'normal')
  const highScore = result.value && result.value.score > 0.7
  
  if (allNormal && highScore) {
    console.warn('所有转子槽谐波正常但故障评分很高，可能需要调整诊断逻辑')
  }
}

// 格式化谐波名称
const formatHarmonicName = (name) => {
  const mapping = {
    'principal_slot_harmonic': '主槽谐波',
    'upper_sideband': '上边带谐波',
    'lower_sideband': '下边带谐波',
    'first_slot_harmonic': '一阶槽谐波',
    'second_slot_harmonic': '二阶槽谐波'
  }
  
  return mapping[name] || name
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
  window.open(`http://localhost:8000/samples/broken-bar/${type}`, '_blank')
}

// 检查是否来自快速分析页面
const checkQuickAnalysis = () => {
  if (route.query.quickAnalysis === 'true') {
    // 从localStorage中获取分析结果
    const savedResult = localStorage.getItem('broken-bar_analysis_result')
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
        
        // 处理转子槽谐波数据
        if (result.value.features?.slot_harmonics) {
          processSlotHarmonicsData(result.value.features.slot_harmonics)
        }
        
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
  const savedThresholds = localStorage.getItem('brokenBarThresholds')
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

.sub-card {
  margin-top: 20px;
  border: 1px solid #EBEEF5;
  box-shadow: none;
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

.broken-bar-features {
  margin: 30px 0;
}

.feature-card {
  padding: 15px;
  border-radius: 8px;
  border: 1px solid #EBEEF5;
  text-align: center;
  transition: all 0.3s;
  height: 100%;
}

.feature-warning {
  border-color: #E6A23C;
  background-color: rgba(230, 162, 60, 0.1);
}

.feature-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 10px;
}

.feature-value {
  font-size: 24px;
  color: #409EFF;
  margin-bottom: 10px;
}

.feature-warning .feature-value {
  color: #E6A23C;
}

.feature-desc {
  font-size: 12px;
  color: #909399;
}

.feature-freq-info {
  margin: 15px 0;
}

.chart-wrapper {
  height: 150px;
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

.formula {
  font-size: 18px;
  margin: 15px 0;
  font-family: 'Times New Roman', serif;
  text-align: center;
}
</style> 