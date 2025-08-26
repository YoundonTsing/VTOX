// 前端环境配置 - 支持单体/集群模式切换
// frontend/src/config/environment.js

/**
 * 环境配置管理
 * 支持开发/测试/生产环境的自动适配
 */

// 自动检测部署模式
const detectDeploymentMode = () => {
  const hostname = window.location.hostname
  const port = window.location.port
  
  // 根据访问地址自动判断部署模式
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'development'
  } else if (hostname.includes('test') || hostname.includes('staging')) {
    return 'testing'
  } else {
    return 'production'
  }
}

// 基础配置
const baseConfig = {
  // API网关地址 (所有模式下都是相同的，保证兼容性)
  apiBaseUrl: process.env.NODE_ENV === 'production' 
    ? 'https://api.vtox.example.com' 
    : 'http://localhost:8000',
    
  // WebSocket地址 (保持不变，由API Gateway处理)
  websocketUrl: process.env.NODE_ENV === 'production'
    ? 'wss://api.vtox.example.com/ws/frontend'
    : 'ws://localhost:8000/ws/frontend',
    
  // 超时配置
  timeout: 10000,
  
  // 重连配置
  reconnectAttempts: 5,
  reconnectInterval: 2000
}

// 环境特定配置
const environmentConfigs = {
  development: {
    ...baseConfig,
    
    // 开发环境特定配置
    debug: true,
    logLevel: 'debug',
    
    // 集群监控 (可选功能)
    clusterMonitoring: {
      enabled: true,
      refreshInterval: 5000,
      showWorkerDetails: true
    },
    
    // 性能优化配置
    performance: {
      batchSize: 50,
      updateInterval: 100,
      maxCacheSize: 1000
    }
  },
  
  testing: {
    ...baseConfig,
    
    // 测试环境配置
    debug: false,
    logLevel: 'info',
    
    clusterMonitoring: {
      enabled: true,
      refreshInterval: 10000,
      showWorkerDetails: false
    },
    
    performance: {
      batchSize: 80,
      updateInterval: 50,
      maxCacheSize: 2000
    }
  },
  
  production: {
    ...baseConfig,
    
    // 生产环境配置
    debug: false,
    logLevel: 'error',
    
    clusterMonitoring: {
      enabled: false,  // 生产环境可选择禁用详细监控
      refreshInterval: 30000,
      showWorkerDetails: false
    },
    
    performance: {
      batchSize: 100,
      updateInterval: 20,
      maxCacheSize: 5000
    }
  }
}

// 获取当前环境配置
const getCurrentConfig = () => {
  const mode = detectDeploymentMode()
  const config = environmentConfigs[mode] || environmentConfigs.development
  
  return {
    ...config,
    deploymentMode: mode,
    buildTime: new Date().toISOString(),
    version: '1.0.0'
  }
}

// 导出配置
export const config = getCurrentConfig()

// API工具函数 (保持向后兼容)
export const apiUtils = {
  // 构建API URL (保持原有逻辑)
  buildUrl: (path) => {
    return `${config.apiBaseUrl}${path.startsWith('/') ? path : '/' + path}`
  },
  
  // WebSocket URL (保持原有逻辑)
  getWebSocketUrl: () => {
    return config.websocketUrl
  },
  
  // 集群状态API (新增，可选使用)
  getClusterStatusUrl: () => {
    return `${config.apiBaseUrl}/api/v1/diagnosis-stream/system/status`
  },
  
  // 性能监控API (新增，可选使用)
  getPerformanceUrl: () => {
    return `${config.apiBaseUrl}/api/v1/diagnosis-stream/system/performance`
  }
}

// 特性检测 (检测后端是否支持集群功能)
export const featureDetection = {
  // 检测是否为集群部署
  async detectClusterMode() {
    try {
      const response = await fetch(apiUtils.getClusterStatusUrl(), {
        method: 'GET',
        timeout: 3000
      })
      
      if (response.ok) {
        const data = await response.json()
        return data.data && data.data.system_status !== undefined
      }
    } catch (error) {
      console.log('集群模式检测失败，使用单体模式')
    }
    
    return false
  },
  
  // 检测支持的功能
  async detectFeatures() {
    const features = {
      clusterMode: false,
      distributedDiagnosis: false,
      performanceMonitoring: false,
      adaptiveScaling: false
    }
    
    try {
      // 检测集群模式
      features.clusterMode = await this.detectClusterMode()
      
      if (features.clusterMode) {
        // 如果支持集群，检测其他高级功能
        features.distributedDiagnosis = true
        features.performanceMonitoring = true
        
        // 检测自适应扩展功能
        try {
          const adaptiveResponse = await fetch(
            `${config.apiBaseUrl}/api/v1/diagnosis-stream/adaptive/stats`,
            { timeout: 2000 }
          )
          features.adaptiveScaling = adaptiveResponse.ok
        } catch (e) {
          features.adaptiveScaling = false
        }
      }
    } catch (error) {
      console.log('功能检测失败，使用基础功能')
    }
    
    return features
  }
}

// 兼容性保证
export default {
  config,
  apiUtils,
  featureDetection,
  
  // 向后兼容的配置项
  API_BASE_URL: config.apiBaseUrl,
  WEBSOCKET_URL: config.websocketUrl,
  DEPLOYMENT_MODE: config.deploymentMode
}

// 调试信息
if (config.debug) {
  console.log('🔧 VTOX前端配置:', {
    deploymentMode: config.deploymentMode,
    apiBaseUrl: config.apiBaseUrl,
    websocketUrl: config.websocketUrl,
    clusterMonitoring: config.clusterMonitoring.enabled
  })
}