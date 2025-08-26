<template>
  <div class="dashboard-container">
    <h2 class="page-title">系统概览</h2>
    
    <el-row :gutter="20">
      <!-- 系统状态卡片 -->
      <el-col :xs="24" :sm="12" :md="6" :lg="6">
        <el-card class="status-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Monitor /></el-icon>
              <span>系统状态</span>
            </div>
          </template>
          <div class="card-content">
            <div class="status-item">
              <div class="status-label">后端服务</div>
              <el-tag :type="backendStatus.online ? 'success' : 'danger'" size="small">
                {{ backendStatus.online ? '在线' : '离线' }}
              </el-tag>
            </div>
            <div class="status-item">
              <div class="status-label">数据连接</div>
              <el-tag :type="backendStatus.dataConnection ? 'success' : 'warning'" size="small">
                {{ backendStatus.dataConnection ? '正常' : '异常' }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 诊断概览卡片 -->
      <el-col :xs="24" :sm="12" :md="6" :lg="6">
        <el-card class="diagnosis-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Warning /></el-icon>
              <span>故障概览</span>
            </div>
          </template>
          <div class="card-content">
            <div class="count-item">
              <div class="count-number">{{ diagnosticCounts.normal }}</div>
              <div class="count-label">正常</div>
            </div>
            <div class="count-item warning">
              <div class="count-number">{{ diagnosticCounts.warning }}</div>
              <div class="count-label">预警</div>
            </div>
            <div class="count-item fault">
              <div class="count-number">{{ diagnosticCounts.fault }}</div>
              <div class="count-label">故障</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 数据统计卡片 -->
      <el-col :xs="24" :sm="12" :md="6" :lg="6">
        <el-card class="data-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><DataAnalysis /></el-icon>
              <span>数据统计</span>
            </div>
          </template>
          <div class="card-content">
            <div class="data-item">
              <div class="data-label">已分析文件</div>
              <div class="data-value">{{ dataStats.filesAnalyzed }}</div>
            </div>
            <div class="data-item">
              <div class="data-label">已处理数据点</div>
              <div class="data-value">{{ formatNumber(dataStats.dataPoints) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 快速操作卡片 -->
      <el-col :xs="24" :sm="12" :md="6" :lg="6">
        <el-card class="action-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><SetUp /></el-icon>
              <span>快速操作</span>
            </div>
          </template>
          <div class="card-content action-buttons">
            <div class="quick-diagnosis">
              <div class="diagnosis-type-selection">
                <el-select v-model="selectedDiagnosisType" placeholder="选择故障诊断类型" style="width: 100%;">
                  <el-option label="匝间短路诊断" value="turn-to-turn" />
                  <el-option label="绝缘失效检测" value="insulation" />
                  <el-option label="轴承故障诊断" value="bearing" />
                  <el-option label="偏心故障诊断" value="eccentricity" />
                  <el-option label="断条故障诊断" value="broken-bar" />
                </el-select>
              </div>
              
              <div class="upload-analyze-row">
                <el-upload
                  class="quick-upload"
                  action="#"
                  :auto-upload="false"
                  :show-file-list="false"
                  :limit="1"
                  accept=".csv"
                  :on-change="handleQuickFileChange"
                  :on-exceed="handleExceed"
                >
                  <el-button type="primary" :disabled="!selectedDiagnosisType" class="action-button">
                    <el-icon><Upload /></el-icon> 上传数据文件
                  </el-button>
                </el-upload>
                
                <el-button 
                  type="success" 
                  :disabled="!quickFile || !selectedDiagnosisType" 
                  @click="handleQuickAnalyze"
                  :loading="quickAnalyzing"
                  class="action-button"
                >
                  <el-icon><Connection /></el-icon> 快速分析
                </el-button>
              </div>
              
              <div v-if="quickFile" class="file-info">
                <el-tag type="info" closable @close="clearQuickFile">
                  {{ quickFile.name }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 诊断历史图表 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :xs="24" :md="12">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>故障诊断历史</span>
              <el-select v-model="historyTimeRange" size="small">
                <el-option label="近7天" value="7" />
                <el-option label="近30天" value="30" />
                <el-option label="近90天" value="90" />
              </el-select>
            </div>
          </template>
          <div id="history-chart" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <!-- 故障分布图表 -->
      <el-col :xs="24" :md="12">
        <el-card class="chart-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>故障类型分布</span>
              <el-radio-group v-model="faultViewType" size="small">
                <el-radio-button label="count">数量</el-radio-button>
                <el-radio-button label="percent">百分比</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div id="distribution-chart" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 诊断功能快速访问卡片 -->
    <el-row :gutter="20" class="feature-row">
      <el-col :xs="24" :sm="12" :md="12" :lg="8">
        <el-card class="feature-card turn-to-turn-card" shadow="hover" @click="goTo('/diagnosis/turn-to-turn')">
          <div class="feature-icon">
            <el-icon><WarningFilled /></el-icon>
          </div>
          <div class="feature-content">
            <h3>匝间短路诊断</h3>
            <p>基于负序电流分析的定子绕组匝间短路故障诊断</p>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="12" :lg="8">
        <el-card class="feature-card insulation-card" shadow="hover" @click="goTo('/diagnosis/insulation')">
          <div class="feature-icon">
            <el-icon><Lightning /></el-icon>
          </div>
          <div class="feature-content">
            <h3>绝缘失效检测</h3>
            <p>基于多参数综合分析的绝缘老化和失效状态评估</p>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="12" :lg="8">
        <el-card class="feature-card bearing-card" shadow="hover" @click="goTo('/diagnosis/bearing')">
          <div class="feature-icon">
            <el-icon><CirclePlus /></el-icon>
          </div>
          <div class="feature-content">
            <h3>轴承故障诊断</h3>
            <p>基于包络谱分析的轴承内圈、外圈和滚动体故障诊断</p>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="12" :lg="12">
        <el-card class="feature-card eccentricity-card" shadow="hover" @click="goTo('/diagnosis/eccentricity')">
          <div class="feature-icon">
            <el-icon><Position /></el-icon>
          </div>
          <div class="feature-content">
            <h3>偏心故障诊断</h3>
            <p>基于MCSA分析的定子与转子偏心故障诊断，包含静态偏心和动态偏心识别</p>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="12" :lg="12">
        <el-card class="feature-card broken-bar-card" shadow="hover" @click="goTo('/diagnosis/broken-bar')">
          <div class="feature-icon">
            <el-icon><Remove /></el-icon>
          </div>
          <div class="feature-content">
            <h3>断条故障诊断</h3>
            <p>基于MCSA的转子断条故障诊断，分析边带特征频率识别转子导条断裂</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 最近诊断记录 -->
    <el-card class="recent-diagnosis" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>最近诊断记录</span>
          <el-button type="primary" link @click="goTo('/data/files')">查看全部</el-button>
        </div>
      </template>
      <el-table :data="recentDiagnosis" stripe style="width: 100%">
        <el-table-column prop="date" label="日期" width="180" />
        <el-table-column prop="fileName" label="文件名" />
        <el-table-column prop="type" label="故障类型" width="150" />
        <el-table-column prop="score" label="故障评分" width="150">
          <template #default="scope">
            <el-progress
              :percentage="scope.row.score * 100"
              :status="getProgressStatus(scope.row.score)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-button type="primary" link @click="viewDetail(scope.row)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Monitor, 
  Warning, 
  DataAnalysis, 
  SetUp, 
  WarningFilled, 
  Lightning, 
  CirclePlus, 
  Position, 
  Remove,
  Upload,
  Connection
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import axios from 'axios'

const router = useRouter()

// 后端状态
const backendStatus = ref({
  online: true,
  dataConnection: true
})

// 诊断统计
const diagnosticCounts = ref({
  normal: 42,
  warning: 5,
  fault: 2
})

// 数据统计
const dataStats = ref({
  filesAnalyzed: 76,
  dataPoints: 1532487
})

// 图表相关
const historyTimeRange = ref('7')
const faultViewType = ref('count')
const historyChart = ref(null)
const distributionChart = ref(null)
const chartsInitialized = ref(false)

// 最近诊断记录
const recentDiagnosis = ref([
  {
    id: 1,
    date: '2023-11-15 09:32:11',
    fileName: 'motor_data_20231115.csv',
    type: '匝间短路',
    score: 0.15,
    status: 'NORMAL'
  },
  {
    id: 2,
    date: '2023-11-14 15:45:23',
    fileName: 'motor_data_20231114.csv',
    type: '绝缘失效',
    score: 0.52,
    status: 'WARNING'
  },
  {
    id: 3,
    date: '2023-11-13 10:12:08',
    fileName: 'motor_data_20231113.csv',
    type: '轴承故障',
    score: 0.78,
    status: 'FAULT'
  },
  {
    id: 4,
    date: '2023-11-12 14:25:33',
    fileName: 'motor_data_20231112.csv',
    type: '偏心故障',
    score: 0.22,
    status: 'NORMAL'
  },
  {
    id: 5,
    date: '2023-11-11 16:08:42',
    fileName: 'motor_data_20231111.csv',
    type: '断条故障',
    score: 0.61,
    status: 'WARNING'
  }
])

// 格式化大数字
const formatNumber = (num) => {
  return num.toString().replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1,')
}

// 获取状态标签类型
const getStatusType = (status) => {
  switch(status) {
    case 'NORMAL': return 'success'
    case 'WARNING': return 'warning'
    case 'FAULT': return 'danger'
    default: return 'info'
  }
}

// 获取状态文本
const getStatusText = (status) => {
  switch(status) {
    case 'NORMAL': return '正常'
    case 'WARNING': return '预警'
    case 'FAULT': return '故障'
    default: return '未知'
  }
}

// 获取进度条状态
const getProgressStatus = (score) => {
  if (score >= 0.7) return 'exception'
  if (score >= 0.3) return 'warning'
  return 'success'
}

// 初始化历史图表
const initHistoryChart = async () => {
  await nextTick() // 等待DOM更新
  
  const chartDom = document.getElementById('history-chart')
  if (!chartDom) {
    console.error('找不到历史图表DOM元素')
    return false // 返回false表示初始化失败
  }
  
  // 检查DOM元素尺寸
  if (chartDom.offsetHeight < 10 || chartDom.offsetWidth < 10) {
    console.warn('历史图表DOM元素尺寸过小，可能不可见:', chartDom.offsetWidth, chartDom.offsetHeight)
    return false // 返回false表示初始化失败
  }
  
  // 如果已经初始化过，先销毁
  if (historyChart.value) {
    try {
      historyChart.value.dispose()
    } catch (e) {
      console.warn('销毁旧的历史图表实例失败:', e)
    }
  }
  
  try {
    historyChart.value = echarts.init(chartDom)
    
    const option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        }
      },
      legend: {
        data: ['正常', '预警', '故障']
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: [
        {
          type: 'category',
          data: ['11/09', '11/10', '11/11', '11/12', '11/13', '11/14', '11/15']
        }
      ],
      yAxis: [
        {
          type: 'value',
          name: '诊断数量'
        }
      ],
      series: [
        {
          name: '正常',
          type: 'bar',
          stack: 'Total',
          emphasis: {
            focus: 'series'
          },
          itemStyle: { color: '#67C23A' },
          data: [5, 7, 6, 8, 6, 5, 5]
        },
        {
          name: '预警',
          type: 'bar',
          stack: 'Total',
          emphasis: {
            focus: 'series'
          },
          itemStyle: { color: '#E6A23C' },
          data: [1, 0, 1, 0, 1, 1, 1]
        },
        {
          name: '故障',
          type: 'bar',
          stack: 'Total',
          emphasis: {
            focus: 'series'
          },
          itemStyle: { color: '#F56C6C' },
          data: [0, 0, 0, 1, 0, 1, 0]
        }
      ]
    }
    
    historyChart.value.setOption(option)
    console.log('历史图表初始化成功')
    return true // 返回true表示初始化成功
  } catch (error) {
    console.error('初始化历史图表失败:', error)
    return false // 返回false表示初始化失败
  }
}

// 初始化故障分布图表
const initDistributionChart = async () => {
  await nextTick() // 等待DOM更新
  
  const chartDom = document.getElementById('distribution-chart')
  if (!chartDom) {
    console.error('找不到分布图表DOM元素')
    return false // 返回false表示初始化失败
  }
  
  // 检查DOM元素尺寸
  if (chartDom.offsetHeight < 10 || chartDom.offsetWidth < 10) {
    console.warn('分布图表DOM元素尺寸过小，可能不可见:', chartDom.offsetWidth, chartDom.offsetHeight)
    return false // 返回false表示初始化失败
  }
  
  // 如果已经初始化过，先销毁
  if (distributionChart.value) {
    try {
      distributionChart.value.dispose()
    } catch (e) {
      console.warn('销毁旧的分布图表实例失败:', e)
    }
  }
  
  try {
    distributionChart.value = echarts.init(chartDom)
    
    const option = {
      tooltip: {
        trigger: 'item',
        formatter: '{a} <br/>{b}: {c} ({d}%)'
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        data: ['匝间短路', '绝缘失效', '轴承故障', '偏心故障', '断条故障']
      },
      series: [
        {
          name: '故障分布',
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: false,
            position: 'center'
          },
          emphasis: {
            label: {
              show: true,
              fontSize: '16',
              fontWeight: 'bold'
            }
          },
          labelLine: {
            show: false
          },
          data: [
            { value: 32, name: '匝间短路' },
            { value: 24, name: '绝缘失效' },
            { value: 28, name: '轴承故障' },
            { value: 15, name: '偏心故障' },
            { value: 12, name: '断条故障' }
          ]
        }
      ]
    }
    
    distributionChart.value.setOption(option)
    console.log('分布图表初始化成功')
    return true // 返回true表示初始化成功
  } catch (error) {
    console.error('初始化分布图表失败:', error)
    return false // 返回false表示初始化失败
  }
}

// 初始化所有图表
const initCharts = async () => {
  if (chartsInitialized.value) return
  
  console.log('开始初始化图表')
  
  // 增加延迟时间确保DOM已经完全渲染
  setTimeout(async () => {
    try {
      // 再次检查DOM元素是否存在
      const historyChartDom = document.getElementById('history-chart')
      const distributionChartDom = document.getElementById('distribution-chart')
      
      if (!historyChartDom || !distributionChartDom) {
        console.warn('图表DOM元素尚未准备好，将在500ms后重试')
        setTimeout(() => initCharts(), 500)
        return
      }
      
      await initHistoryChart()
      await initDistributionChart()
      chartsInitialized.value = true
      console.log('所有图表初始化完成')
    } catch (error) {
      console.error('图表初始化失败:', error)
      // 如果初始化失败，尝试再次初始化
      setTimeout(() => initCharts(), 1000)
    }
  }, 300) // 增加延迟时间
}

// 页面导航
const goTo = (path) => {
  router.push(path)
}

// 查看详情
const viewDetail = (row) => {
  // 根据故障类型跳转到对应的诊断详情页
  let path
  
  switch(row.type) {
    case '匝间短路':
      path = '/diagnosis/turn-to-turn'
      break
    case '绝缘失效':
      path = '/diagnosis/insulation'
      break
    case '轴承故障':
      path = '/diagnosis/bearing'
      break
    case '偏心故障':
      path = '/diagnosis/eccentricity'
      break
    case '断条故障':
      path = '/diagnosis/broken-bar'
      break
    default:
      path = '/diagnosis/turn-to-turn'
  }
  
  router.push(path)
}

// 快速诊断相关
const selectedDiagnosisType = ref('');
const quickFile = ref(null);
const quickAnalyzing = ref(false);

// 处理文件选择
const handleQuickFileChange = (uploadFile) => {
  quickFile.value = uploadFile.raw;
};

// 处理文件数量超出限制
const handleExceed = () => {
  ElMessage.warning('只能上传一个文件');
};

// 处理快速分析
const handleQuickAnalyze = async () => {
  if (!quickFile.value || !selectedDiagnosisType.value) {
    ElMessage.warning('请选择故障类型和上传文件');
    return;
  }
  
  quickAnalyzing.value = true;
  const formData = new FormData();
  formData.append('file', quickFile.value);
  
  try {
    const apiEndpoint = `http://localhost:8000/diagnosis/${selectedDiagnosisType.value}`;
    const response = await axios.post(apiEndpoint, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
    
    // 获取分析结果
    const analysisResult = response.data;
    
    // 预处理图表和表格数据
    if (analysisResult.time_series) {
      // 确保时间序列数据被正确格式化
      analysisResult.processed_time_series = {
        time: analysisResult.time_series.time,
        values: analysisResult.time_series.values
      };
    }
    
    if (analysisResult.frequency_spectrum) {
      // 确保频谱数据被正确格式化
      analysisResult.processed_frequency_spectrum = {
        frequency: analysisResult.frequency_spectrum.frequency,
        amplitude: analysisResult.frequency_spectrum.amplitude
      };
    }
    
    if (analysisResult.envelope_spectrum) {
      // 确保包络谱数据被正确格式化
      analysisResult.processed_envelope_spectrum = {
        frequency: analysisResult.envelope_spectrum.frequency,
        amplitude: analysisResult.envelope_spectrum.amplitude
      };
    }
    
    // 将处理后的分析结果存储到localStorage
    localStorage.setItem(`${selectedDiagnosisType.value}_analysis_result`, JSON.stringify(analysisResult));
    localStorage.setItem(`${selectedDiagnosisType.value}_analysis_timestamp`, new Date().toISOString());
    
    // 添加到最近诊断记录
    const newRecord = {
      id: Date.now(),
      date: new Date().toLocaleString(),
      fileName: quickFile.value.name,
      type: getTypeName(selectedDiagnosisType.value),
      score: analysisResult.score,
      status: getStatusFromScore(analysisResult.score)
    };
    
    // 更新诊断记录
    const recentRecords = JSON.parse(localStorage.getItem('recentDiagnosis') || '[]');
    recentRecords.unshift(newRecord);
    if (recentRecords.length > 10) {
      recentRecords.pop(); // 保留最新的10条记录
    }
    localStorage.setItem('recentDiagnosis', JSON.stringify(recentRecords));
    
    // 更新诊断统计
    updateDiagnosticStats(analysisResult.status);
    
    // 分析成功后跳转到对应的诊断页面
    ElMessage.success('分析成功，正在跳转到结果页面...');
    
    // 延迟一小段时间确保localStorage设置完成
    setTimeout(() => {
      router.push({
        path: `/diagnosis/${selectedDiagnosisType.value}`,
        query: { 
          quickAnalysis: 'true',
          timestamp: new Date().getTime().toString()
        }
      });
    }, 100);
    
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '分析过程中发生错误，请重试');
    console.error('分析失败:', error);
  } finally {
    quickAnalyzing.value = false;
  }
};

// 获取故障类型名称
const getTypeName = (typeCode) => {
  const typeMap = {
    'turn-to-turn': '匝间短路',
    'insulation': '绝缘失效',
    'bearing': '轴承故障',
    'eccentricity': '偏心故障',
    'broken-bar': '断条故障'
  };
  return typeMap[typeCode] || typeCode;
};

// 根据分数获取状态
const getStatusFromScore = (score) => {
  if (score >= 0.7) return 'FAULT';
  if (score >= 0.3) return 'WARNING';
  return 'NORMAL';
};

// 更新诊断统计
const updateDiagnosticStats = (status) => {
  if (status === 'normal') {
    diagnosticCounts.value.normal++;
  } else if (status === 'warning') {
    diagnosticCounts.value.warning++;
  } else if (status === 'fault') {
    diagnosticCounts.value.fault++;
  }
  
  // 更新已分析文件计数
  dataStats.value.filesAnalyzed++;
  
  // 假设每个文件平均有10000个数据点
  dataStats.value.dataPoints += 10000;
  
  // 保存更新后的统计数据到localStorage
  localStorage.setItem('diagnosticCounts', JSON.stringify(diagnosticCounts.value));
  localStorage.setItem('dataStats', JSON.stringify(dataStats.value));
};

// 清除已选文件
const clearQuickFile = () => {
  quickFile.value = null;
};

// 监听窗口大小变化
const handleResize = () => {
  if (historyChart.value) {
    historyChart.value.resize()
  }
  if (distributionChart.value) {
    distributionChart.value.resize()
  }
}

// 挂载时初始化
onMounted(async () => {
  console.log('DashboardView组件已挂载')
  
  // 加载本地保存的诊断记录
  loadSavedDiagnosisRecords()
  
  // 使用setTimeout确保DOM完全渲染后再初始化图表
  setTimeout(async () => {
    await initCharts()
    // 添加窗口大小变化监听
    window.addEventListener('resize', handleResize)
  }, 500)
})

// 卸载时清理
onUnmounted(() => {
  console.log('DashboardView组件已卸载')
  window.removeEventListener('resize', handleResize)
  
  // 确保图表实例存在再销毁
  if (historyChart.value) {
    try {
      historyChart.value.dispose()
    } catch (e) {
      console.warn('销毁历史图表时出错:', e)
    }
    historyChart.value = null
  }
  
  if (distributionChart.value) {
    try {
      distributionChart.value.dispose()
    } catch (e) {
      console.warn('销毁分布图表时出错:', e)
    }
    distributionChart.value = null
  }
})

// 加载本地保存的诊断记录
const loadSavedDiagnosisRecords = () => {
  const savedRecords = localStorage.getItem('recentDiagnosis')
  if (savedRecords) {
    try {
      recentDiagnosis.value = JSON.parse(savedRecords)
    } catch (error) {
      console.error('解析保存的诊断记录失败:', error)
    }
  }
  
  // 加载诊断统计
  const savedCounts = localStorage.getItem('diagnosticCounts')
  if (savedCounts) {
    try {
      Object.assign(diagnosticCounts.value, JSON.parse(savedCounts))
    } catch (error) {
      console.error('解析保存的诊断统计失败:', error)
    }
  }
  
  // 加载数据统计
  const savedStats = localStorage.getItem('dataStats')
  if (savedStats) {
    try {
      Object.assign(dataStats.value, JSON.parse(savedStats))
    } catch (error) {
      console.error('解析保存的数据统计失败:', error)
    }
  }
}
</script>

<style scoped>
.dashboard-container {
  padding-bottom: 20px;
}

.page-title {
  margin-bottom: 20px;
  color: #303133;
  font-weight: 600;
}

.el-row {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header .el-icon {
  margin-right: 8px;
}

.status-card, .diagnosis-card, .data-card, .action-card {
  height: 200px;
  display: flex;
  flex-direction: column;
}

.status-card .card-content, 
.diagnosis-card .card-content, 
.data-card .card-content, 
.action-card .card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.status-card .card-content {
  justify-content: space-around;
  padding: 0;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.status-item:last-child {
  margin-bottom: 0;
}

.diagnosis-card .card-content {
  justify-content: space-around;
  display: flex;
  flex-direction: row;
}

.count-item {
  text-align: center;
  flex: 1;
}

.count-number {
  font-size: 28px;
  font-weight: 600;
  color: #67C23A;
  margin-bottom: 15px;
}

.count-item.warning .count-number {
  color: #E6A23C;
}

.count-item.fault .count-number {
  color: #F56C6C;
}

.count-label {
  font-size: 16px;
  color: #606266;
}

.data-card .card-content {
  justify-content: space-around;
}

.data-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}

.data-item:last-child {
  margin-bottom: 0;
}

.data-label {
  font-size: 16px;
}

.data-value {
  font-weight: 600;
  font-size: 20px;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  justify-content: center;
  flex: 1;
  padding: 10px 0;
}

.quick-diagnosis {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
}

.diagnosis-type-selection {
  margin-bottom: 10px;
}

.upload-analyze-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  margin-bottom: 10px;
}

.quick-upload {
  flex: 1;
  display: flex;
}

.quick-upload .el-upload {
  display: block;
  width: 100%;
}

.quick-upload .el-button {
  width: 100%;
}

.action-button {
  flex: 1;
  height: 40px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.file-info {
  margin-top: 5px;
  display: flex;
}

.quick-upload .el-upload-list {
  text-align: left;
  margin-top: 10px;
}

.quick-upload .el-upload-list .el-upload-list__item {
  margin-bottom: 10px;
}

.quick-upload .el-upload-list .el-upload-list__item .el-icon--upload {
  color: #409EFF;
}

.quick-upload .el-upload-list .el-upload-list__item .el-icon--upload:hover {
  color: #66b1ff;
}

.quick-upload .el-upload-list .el-upload-list__item .el-icon--delete {
  color: #F56C6C;
}

.quick-upload .el-upload-list .el-upload-list__item .el-icon--delete:hover {
  color: #f78989;
}

.chart-row {
  margin-top: 20px;
}

.chart-card {
  height: 450px;
  display: flex;
  flex-direction: column;
}

.chart-card .el-card__body {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chart-container {
  flex: 1;
  min-height: 380px;
}

.recent-diagnosis {
  margin-top: 20px;
}

.feature-row {
  margin-top: 20px;
  margin-bottom: 20px;
}

.feature-card {
  height: 120px;
  display: flex;
  cursor: pointer;
  transition: all 0.3s;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

/* 确保第一行的特征卡片高度一致 */
.turn-to-turn-card, .insulation-card, .bearing-card {
  height: 120px;
}

/* 确保第二行的特征卡片高度一致 */
.eccentricity-card, .broken-bar-card {
  height: 120px;
}

.feature-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  width: 80px;
  color: #fff;
  border-radius: 4px;
  margin-right: 15px;
}

.turn-to-turn-card .feature-icon {
  background-color: #409EFF;
}

.insulation-card .feature-icon {
  background-color: #E6A23C;
}

.bearing-card .feature-icon {
  background-color: #67C23A;
}

.eccentricity-card .feature-icon {
  background-color: #F56C6C;
}

.broken-bar-card .feature-icon {
  background-color: #909399;
}

.feature-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.feature-content h3 {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #303133;
}

.feature-content p {
  margin: 0;
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

/* 手机端适配 */
@media (max-width: 768px) {
  .action-card {
    height: auto !important;
    min-height: 320px;
  }
  
  .quick-diagnosis {
    gap: 15px;
  }
  
  .chart-container {
    min-height: 300px;
  }
  
  .status-card, .diagnosis-card, .data-card, .action-card {
    height: auto;
    min-height: 200px;
  }
  
  .chart-card {
    height: auto;
    min-height: 350px;
  }
}
</style> 