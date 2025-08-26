import axios from 'axios'

// API基础URL
const baseURL = 'http://localhost:8000'

// 创建axios实例
const api = axios.create({
  baseURL,
  timeout: 30000, // 30秒超时
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    console.log('API请求:', config.url)
    
    // 自动添加认证token
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  error => {
    console.error('API请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API请求错误:', error)
    
    // 获取详细的错误信息
    let errorMessage = '服务器内部错误，请稍后重试'
    
    if (error.response) {
      // 服务器返回了错误状态码
      const status = error.response.status
      const detail = error.response.data?.detail || '未知错误'
      
      switch (status) {
        case 400:
          errorMessage = `请求错误: ${detail}`
          break
        case 401:
          // 未授权，清除本地token并跳转到登录页
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          localStorage.removeItem('user_info')
          
          // 检查是否在浏览器环境中且不是已经在登录页
          if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
          
          errorMessage = `认证失败: ${detail}`
          break
        case 404:
          errorMessage = `资源不存在: ${detail}`
          break
        case 422:
          errorMessage = `数据处理错误: ${detail}`
          break
        case 500:
          errorMessage = `服务器错误: ${detail}`
          break
        default:
          errorMessage = `错误(${status}): ${detail}`
          break
      }
    } else if (error.request) {
      // 请求已发出，但没有收到响应
      errorMessage = '无法连接到服务器，请检查网络连接'
    } else {
      // 请求配置错误
      errorMessage = error.message
    }
    
    return Promise.reject(errorMessage)
  }
)

// API方法
export default {
  // 分析匝间短路故障
  analyzeFile(file) {
    const formData = new FormData()
    formData.append('file', file)
    
    return api.post('/diagnosis/turn-to-turn', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  // 健康检查
  healthCheck() {
    return api.get('/health')
  },

  // AI 聊天相关 API
  
  // 发送聊天消息
  sendChatMessage(message, conversationHistory = [], modelProvider = 'local') {
    return api.post('/ai/chat', {
      message,
      conversation_history: conversationHistory,
      model_provider: modelProvider
    })
  },

  // 获取可用的 AI 模型
  getAvailableModels() {
    return api.get('/ai/models')
  },

  // AI 服务健康检查
  checkAIHealth() {
    return api.get('/ai/health')
  },

  // ==========================================
  // Redis Stream 分布式诊断 API
  // ==========================================

  // 初始化分布式诊断系统
  initializeDistributedDiagnosis(redisUrl = 'redis://localhost:6379') {
    return api.post('/api/v1/diagnosis-stream/initialize', { redis_url: redisUrl })
  },

  // 启动分布式诊断系统
  startDistributedDiagnosis(config = {}) {
    const defaultConfig = {
      consumers_per_fault: 2,
      enable_aggregation: true,
      enable_monitoring: true
    }
    const finalConfig = { ...defaultConfig, ...config }
    
    // 使用URL参数传递配置
    const params = new URLSearchParams()
    params.append('consumers_per_fault', finalConfig.consumers_per_fault)
    params.append('enable_aggregation', finalConfig.enable_aggregation)
    params.append('enable_monitoring', finalConfig.enable_monitoring)
    
    return api.post(`/api/v1/diagnosis-stream/start?${params}`)
  },

  // 停止分布式诊断系统
  stopDistributedDiagnosis() {
    return api.post('/api/v1/diagnosis-stream/system/stop')
  },

  // 发布车辆数据到分布式系统
  publishVehicleData(vehicleId, sensorData, location = null, metadata = {}) {
    return api.post(`/api/v1/diagnosis-stream/vehicles/${vehicleId}/data`, {
      sensor_data: sensorData,
      location,
      additional_metadata: metadata
    })
  },

  // 获取车辆健康状态
  getVehicleHealth(vehicleId) {
    return api.get(`/api/v1/diagnosis-stream/vehicles/${vehicleId}/health`)
  },

  // 获取车辆诊断历史
  getVehicleDiagnosisHistory(vehicleId, faultType = null, hours = 24) {
    const params = new URLSearchParams()
    if (faultType) params.append('fault_type', faultType)
    params.append('hours', hours)
    return api.get(`/api/v1/diagnosis-stream/vehicles/${vehicleId}/diagnosis-history?${params}`)
  },

  // 获取关键警报
  getCriticalAlerts(limit = 10) {
    return api.get(`/api/v1/diagnosis-stream/alerts/critical?limit=${limit}`)
  },

  // 获取系统性能指标
  getSystemPerformance() {
    return api.get('/api/v1/diagnosis-stream/system/performance')
  },

  // 获取系统状态
  getSystemStatus() {
    return api.get('/api/v1/diagnosis-stream/system/status')
  },

  // 获取支持的故障类型
  getSupportedFaultTypes() {
    return api.get('/api/v1/diagnosis-stream/fault-types')
  },

  // 扩展消费者
  scaleConsumers(faultType, newCount) {
    return api.post('/api/v1/diagnosis-stream/system/scale', {
      fault_type: faultType,
      new_count: newCount
    })
  },

  // 模拟车辆数据（用于演示）
  simulateVehicleData(vehicleId, faultType = null, severity = 0.5) {
    return api.post('/api/v1/diagnosis-stream/demo/simulate-vehicle-data', {
      vehicle_id: vehicleId,
      fault_type: faultType,
      severity
    })
  },

  // ==========================================
  // 车队管理 API (MultiVehicleSimulator)
  // ==========================================

  // 初始化车队
  initializeFleet(fleetSize = 3, apiBaseUrl = 'http://localhost:8000') {
    const params = new URLSearchParams()
    params.append('fleet_size', fleetSize)
    params.append('api_base_url', apiBaseUrl)
    return api.post(`/api/v1/vehicle-fleet/initialize?${params}`)
  },

  // 启动车队模拟
  startFleetSimulation(config = {}) {
    const defaultConfig = {
      duration_seconds: null,
      test_mode: false
    }
    const finalConfig = { ...defaultConfig, ...config }
    
    const params = new URLSearchParams()
    if (finalConfig.duration_seconds) {
      params.append('duration_seconds', finalConfig.duration_seconds)
    }
    params.append('test_mode', finalConfig.test_mode)
    
    return api.post(`/api/v1/vehicle-fleet/start?${params}`)
  },

  // 停止车队模拟
  stopFleetSimulation() {
    return api.post('/api/v1/vehicle-fleet/stop')
  },

  // 获取车队状态
  getFleetStatus() {
    return api.get('/api/v1/vehicle-fleet/status')
  },

  // 获取车队统计
  getFleetStats() {
    return api.get('/api/v1/vehicle-fleet/stats')
  },

  // 获取车队日志
  getFleetLogs(lines = 50) {
    return api.get(`/api/v1/vehicle-fleet/logs?lines=${lines}`)
  },

  // ==========================================
  // WebSocket桥接器控制 API
  // ==========================================

  // 开始桥接器数据处理
  startStreamBridge() {
    return api.post('/api/v1/diagnosis-stream/bridge/control?action=start')
  },

  // 停止桥接器数据处理
  stopStreamBridge() {
    return api.post('/api/v1/diagnosis-stream/bridge/control?action=stop')
  },

  // 获取桥接器状态
  getStreamBridgeStatus() {
    return api.get('/api/v1/diagnosis-stream/bridge/status')
  },

  // 启动桥接器
  startStreamBridge() {
    return api.post('/api/v1/diagnosis-stream/bridge/control?action=start')
  },

  // 重启桥接器
  restartStreamBridge() {
    return api.post('/api/v1/diagnosis-stream/bridge/restart')
  },

  // ==========================================
  // Redis Stream缓存优化 API
  // ==========================================

  // 启用缓存优化
  enableCacheOptimization() {
    return api.post('/api/v1/diagnosis-stream/bridge/optimization/enable')
  },

  // 禁用缓存优化
  disableCacheOptimization() {
    return api.post('/api/v1/diagnosis-stream/bridge/optimization/disable')
  },

  // 获取缓存优化统计
  getCacheOptimizationStats() {
    return api.get('/api/v1/diagnosis-stream/bridge/optimization/stats')
  },

  // ==========================================
  // 集群控制 API
  // ==========================================

  // 启动集群（后台任务）
  startCluster(workers = null, mode = null) {
    const params = new URLSearchParams()
    if (workers !== null) params.append('workers', workers)
    if (mode) params.append('mode', mode)
    const url = params.toString() ? `/api/v1/cluster/start?${params}` : '/api/v1/cluster/start'
    return api.post(url)
  },

  // 停止集群（后台任务）
  stopCluster() {
    return api.post('/api/v1/cluster/stop')
  },

  // 获取集群状态
  getClusterStatus() {
    return api.get('/api/v1/cluster/status')
  }
} 