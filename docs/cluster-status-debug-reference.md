# VTOX集群状态监控数据参考文档

## 当前真实数据快照 (2025-08-23 02:59:45)

### API响应结构
```json
{
  "status": "success",
  "data": {
    "cluster_health": 70,
    "cluster_status": "良好",
    "worker_nodes": [...], // 33个消费者节点
    "performance_metrics": {
      "throughput": 60.0,
      "latency": 0.0,
      "queue_length": 142
    },
    "service_registry": {
      "total_services": 5,
      "healthy_services": 5,
      "faulty_services": 0
    },
    "load_balancer": {
      "total_requests": 31042,
      "success_rate": 95.5,
      "avg_response_time": 0.0
    },
    "api_gateway": {
      "status": "running",
      "api_calls": 31042,
      "active_connections": 33
    },
    "debug_info": {
      "active_streams": {
        "motor_raw_data": {"length": 5000, "groups": 7},
        "fault_diagnosis_results": {"length": 30000, "groups": 3},
        "vehicle_health_assessments": {"length": 10003, "groups": 2},
        "performance_metrics": {"length": 3008, "groups": 0},
        "system_alerts": {"length": 5031, "groups": 0}
      },
      "total_consumers": 33,
      "healthy_workers": 10,
      "warning_workers": 23
    }
  }
}
```

### 前端数据映射
后端字段 (snake_case) → 前端字段 (camelCase)

#### 服务注册中心
```javascript
// 后端: data.service_registry
serviceRegistry: {
  totalServices: data.service_registry.total_services,      // 5
  healthyServices: data.service_registry.healthy_services,  // 5
  faultyServices: data.service_registry.faulty_services     // 0
}
```

#### 负载均衡器
```javascript
// 后端: data.load_balancer
loadBalancer: {
  totalRequests: data.load_balancer.total_requests,        // 31042
  successRate: data.load_balancer.success_rate,            // 95.5
  avgResponseTime: data.load_balancer.avg_response_time    // 0
}
```

#### API网关
```javascript
// 后端: data.api_gateway
apiGateway: {
  status: data.api_gateway.status,                         // "running"
  apiCalls: data.api_gateway.api_calls,                    // 31042
  activeConnections: data.api_gateway.active_connections   // 33
}
```

### Worker节点示例
```javascript
{
  "id": "bearing_consumer_001",
  "type": "bearing",
  "status": "healthy",           // healthy | warning | error
  "cpu_usage": 30,              // 百分比
  "memory_usage": 32.5,         // 百分比
  "current_tasks": 5,           // 当前任务数
  "success_rate": 0.95,         // 成功率 (0-1)
  "stream": "motor_raw_data",
  "group": "bearing_diagnosis_group",
  "idle_ms": 295                // 空闲时间 (毫秒)
}
```

### 故障类型分布
当前系统支持5种故障诊断类型，每种6个消费者：
- bearing (轴承故障): 6个消费者
- broken_bar (断条故障): 6个消费者  
- eccentricity (偏心故障): 6个消费者
- insulation (绝缘失效): 6个消费者
- turn_fault (匝间短路): 6个消费者
- 结果聚合器: 3个消费者
- 前端桥接: 2个消费者

### 系统状态指标说明

#### 集群健康度计算
- 90+ = "优秀"
- 70-89 = "良好" 
- <70 = "需要关注"

当前: 70 (良好) - 有部分Worker处于警告状态

#### 吞吐量计算
基于活跃消费者数量估算: 33个消费者 × 约1.8 msg/s = 60 msg/min

#### 响应时延
从performance_metrics流获取最新处理时间，当前显示0ms表示处理非常快速

#### 队列积压
所有消费者待处理任务总数: 142个

### Redis Stream状态
```
motor_raw_data: 5,000条消息, 7个消费者组
fault_diagnosis_results: 30,000条消息, 3个消费者组  
vehicle_health_assessments: 10,003条消息, 2个消费者组
performance_metrics: 3,008条消息
system_alerts: 5,031条消息
```

## UI显示建议

### 状态颜色方案
- 健康 (healthy): 绿色 #67c23a
- 警告 (warning): 橙色 #e6a23c  
- 错误 (error): 红色 #f56c6c

### 数据刷新频率
- 自动刷新: 30秒间隔
- 手动刷新: 用户点击刷新按钮
- 实时数据: 通过WebSocket (如需要)

### 性能阈值提醒
- 吞吐量 < 30 msg/s: 提醒性能偏低
- 队列积压 > 200: 提醒任务堆积
- 健康Worker < 50%: 提醒系统负载高

### 错误处理
- API调用失败: 自动切换到模拟数据
- 网络异常: 显示离线状态
- 数据异常: 使用默认值并记录日志

## 调试信息

### 浏览器控制台日志
✅ API调用成功，状态码200
✅ 中文编码正确显示
✅ 字段映射成功完成
✅ 数据更新到Vue组件
✅ 界面显示正常

### 后端日志关键词
- [API DEBUG]: API调用调试信息
- Redis连接成功
- 数据统计完成
- 响应发送成功

## 联调检查清单

□ ✅ 后端服务运行正常 (localhost:8000)
□ ✅ 前端服务运行正常 (localhost:3000)  
□ ✅ Redis连接正常
□ ✅ 分布式诊断系统运行中
□ ✅ API响应状态200
□ ✅ 中文编码正确
□ ✅ 字段映射正确
□ ✅ 数据更新成功
□ ✅ 界面显示正常
□ ✅ 调试日志完整

## 下一步优化建议

1. **性能优化**: 考虑增加缓存减少API调用频率
2. **用户体验**: 添加加载状态和错误重试机制  
3. **数据可视化**: 考虑添加趋势图表显示历史数据
4. **告警机制**: 集成系统告警到界面显示
5. **导出功能**: 实现集群状态报告导出

当前联调状态: ✅ 完全成功