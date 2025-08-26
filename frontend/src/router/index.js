import { createRouter, createWebHistory } from 'vue-router'

// 主页面
import DashboardView from '@/views/DashboardView.vue'

// 认证模块
import Login from '@/views/auth/Login.vue' // 导入登录组件

// 匝间短路诊断模块
import TurnToTurnDiagnosis from '@/views/diagnosis/TurnToTurnDiagnosis.vue'

// 绝缘失效检测模块
import InsulationDiagnosis from '@/views/diagnosis/InsulationDiagnosis.vue'

// 其他故障诊断模块（可根据需要实现）
const BearingDiagnosis = () => import('@/views/diagnosis/BearingDiagnosis.vue')
const EccentricityDiagnosis = () => import('@/views/diagnosis/EccentricityDiagnosis.vue')
const BrokenBarDiagnosis = () => import('@/views/diagnosis/BrokenBarDiagnosis.vue')

// 监测模块（可根据需要实现）
const RealTimeMonitor = () => import('@/views/monitor/RealTimeMonitor.vue')
const TrendAnalysis = () => import('@/views/monitor/TrendAnalysis.vue')
const AlarmManagement = () => import('@/views/monitor/AlarmManagement.vue')

// 系统监控模块
const CacheStatusPanel = () => import('@/components/CacheStatusPanel.vue')

// 数据管理模块（可根据需要实现）
// const DataFiles = () => import('@/views/data/DataFiles.vue')
// const DataImport = () => import('@/views/data/DataImport.vue')
// const DataExport = () => import('@/views/data/DataExport.vue')

// 设置模块（可根据需要实现）
const ThresholdSettings = () => import('@/views/settings/ThresholdSettings.vue')
const ParameterSettings = () => import('@/views/settings/ParameterSettings.vue')
const UserSettings = () => import('@/views/settings/UserSettings.vue')

// 统计分析模块
const FaultHistory = () => import('@/views/statistics/FaultHistory.vue')

// AI助手模块
const AgentBoard = () => import('@/views/agent/AgentBoard.vue')

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { title: '登录', public: true } // 标记为公共路由
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: DashboardView, // 使用直接导入的组件，而不是懒加载
    meta: {
      title: '系统概览',
      requiresAuth: true // 需要认证
    }
  },
  {
    path: '/',
    redirect: '/dashboard' // 将根路径重定向到/dashboard
  },
  {
    path: '/statistics/fault-history',
    name: 'FaultHistory',
    component: FaultHistory,
    meta: { title: '故障历史记录', requiresAuth: true } // 需要认证
  },
  
  // 故障诊断模块路由
  {
    path: '/diagnosis/turn-to-turn',
    name: 'TurnToTurnDiagnosis',
    component: TurnToTurnDiagnosis,
    meta: { title: '匝间短路诊断', requiresAuth: true } // 需要认证
  },
  {
    path: '/diagnosis/bearing',
    name: 'BearingDiagnosis',
    component: BearingDiagnosis,
    meta: { title: '轴承故障诊断', requiresAuth: true } // 需要认证
  },
  {
    path: '/diagnosis/eccentricity',
    name: 'EccentricityDiagnosis',
    component: EccentricityDiagnosis,
    meta: { title: '偏心故障诊断', requiresAuth: true } // 需要认证
  },
  {
    path: '/diagnosis/broken-bar',
    name: 'BrokenBarDiagnosis',
    component: BrokenBarDiagnosis,
    meta: { title: '断条故障诊断', requiresAuth: true } // 需要认证
  },
  {
    path: '/diagnosis/insulation',
    name: 'InsulationDiagnosis',
    component: InsulationDiagnosis,
    meta: { title: '绝缘失效诊断', requiresAuth: true } // 需要认证
  },
  {
    path: '/diagnosis/turn-fault',
    name: 'TurnFaultDiagnosis',
    component: () => import('@/views/diagnosis/TurnFaultDiagnosis.vue'),
    meta: {
      title: '匝间短路故障诊断',
      requiresAuth: true // 需要认证
    }
  },
  
  // 监测模块路由
  {
    path: '/monitor/realtime',
    name: 'RealTimeMonitor',
    component: () => import('@/views/monitor/RealTimeMonitor.vue'),
    props: (route) => ({ faultType: route.query.faultType }),
    meta: { title: '实时监测', requiresAuth: true } // 需要认证
  },
  {
    path: '/monitor/trend',
    name: 'TrendAnalysis',
    component: TrendAnalysis,
    meta: { title: '趋势分析', requiresAuth: true } // 需要认证
  },
  {
    path: '/monitor/alarm',
    name: 'AlarmManagement',
    component: AlarmManagement,
    meta: { title: '告警管理', requiresAuth: true } // 需要认证
  },
  {
    path: '/monitor/fleet-distributed',
    name: 'FleetDistributedMonitor',
    component: () => import('@/views/monitor/FleetDistributedMonitor.vue'),
    meta: {
      title: '车队分布式监控',
      requiresAuth: false // ✅ 启用JWT认证保护
    }
  },
  {
    path: '/monitor/cache-status',
    name: 'CacheStatusPanel',
    component: CacheStatusPanel,
    meta: {
      title: '缓存状态监控',
      requiresAuth: true // 需要认证
    }
  },
  {
    path: '/monitor/cluster-status',
    name: 'ClusterStatusMonitor',
    component: () => import('@/views/monitor/ClusterStatusView.vue'),
    meta: {
      title: '集群状态监控',
      requiresAuth: true // 需要认证
    }
  },
  {
    path: '/config/throughput',
    name: 'ThroughputConfig',
    component: () => import('@/views/ThroughputConfig.vue'),
    meta: {
      title: '吞吐量配置管理',
      requiresAuth: true // 需要认证
    }
  },
  {
    path: '/diagnosis/vehicle/:vehicleId',
    name: 'VehicleDetail',
    component: () => import('@/views/diagnosis/VehicleDetailView.vue'),
    props: true,
    meta: {
      title: '车辆详情',
      requiresAuth: true // ✅ 启用JWT认证保护
    }
  },
  
  // 设置模块路由
  {
    path: '/settings/threshold',
    name: 'ThresholdSettings',
    component: ThresholdSettings,
    meta: { title: '阈值设置', requiresAuth: true } // 需要认证
  },
  {
    path: '/settings/parameters',
    name: 'ParameterSettings',
    component: ParameterSettings,
    meta: { title: '参数配置', requiresAuth: true } // 需要认证
  },
  {
    path: '/settings/user',
    name: 'UserSettings',
    component: UserSettings,
    meta: { title: '用户管理', requiresAuth: true } // 需要认证
  },
  
  // AI助手模块路由
  {
    path: '/agent',
    name: 'AgentBoard',
    component: AgentBoard,
    meta: { title: 'AI智能助手', requiresAuth: true } // 需要认证
  },
  
  // 404页面
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: {
      title: '页面未找到',
      public: true // 404页面通常是公开的
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由前置守卫，用于认证和设置页面标题
router.beforeEach((to, from, next) => {
  const isAuthenticated = localStorage.getItem('access_token')
  const requiresAuth = to.meta.requiresAuth
  const isPublic = to.meta.public

  // 设置页面标题
  if (to.meta.title) {
    document.title = `电机故障诊断系统 - ${to.meta.title}`
  } else {
    document.title = `电机故障诊断系统`
  }

  // 特殊处理根路径和dashboard路径
  if (to.path === '/' && isAuthenticated) {
    // 如果已登录访问根路径，直接重定向到dashboard并强制刷新
    return next({ 
      path: '/dashboard', 
      query: { 
        t: Date.now(),
        refresh: 'true' 
      } 
    })
  }

  if (requiresAuth && !isAuthenticated) {
    // 如果需要认证但未登录，则重定向到登录页
    next({ name: 'Login' })
  } else if (isAuthenticated && isPublic) {
    // 如果已登录且访问公开页面（如登录页），则重定向到系统概览页面
    next({ 
      path: '/dashboard', 
      query: { 
        t: Date.now(),
        refresh: 'true' 
      } 
    })
  } else {
    // 其他情况正常导航
    next()
  }
})

export default router 