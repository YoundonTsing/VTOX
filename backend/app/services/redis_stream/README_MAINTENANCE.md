# Redis Stream 维护功能使用指南

## 🎯 功能概述

Redis Stream维护功能是一个**非侵入式**的内存管理解决方案，专门解决Redis Stream无限增长导致的内存问题。

### ✅ 核心特性

- **XTRIM定期清理**：自动裁剪Stream长度，防止内存溢出
- **分级维护策略**：不同类型Stream使用不同的清理策略
- **非侵入式设计**：不影响现有业务逻辑
- **安全保守**：采用保守的清理策略，确保重要数据不丢失
- **可配置监控**：提供详细的维护统计和配置接口

## 🚀 快速启用

### 1. 自动启用（推荐）

系统启动时会自动初始化维护功能，但不会立即启动：

```python
# 在 StreamManager 初始化时自动启用
from backend.app.services.redis_stream import stream_manager

# 初始化时会自动准备维护功能
await stream_manager.initialize(enable_maintenance=True)

# 启动诊断系统时会自动启动维护
await stream_manager.start_diagnosis_system({
    "enable_stream_maintenance": True  # 默认为True
})
```

### 2. 手动控制

```python
# 手动启动维护
success = await stream_manager.start_stream_maintenance()

# 停止维护
await stream_manager.stop_stream_maintenance()

# 获取维护统计
stats = await stream_manager.get_maintenance_stats()
```

### 3. API接口控制

```bash
# 启动维护
curl -X POST "http://localhost:8000/api/v1/diagnosis-stream/maintenance/start" \
     -H "Authorization: Bearer YOUR_TOKEN"

# 获取统计
curl "http://localhost:8000/api/v1/diagnosis-stream/maintenance/stats" \
     -H "Authorization: Bearer YOUR_TOKEN"

# 手动裁剪特定Stream
curl -X POST "http://localhost:8000/api/v1/diagnosis-stream/maintenance/trim/motor_raw_data?max_length=3000" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

## ⚙️ 配置说明

### 默认配置

```python
maintenance_config = StreamMaintenanceConfig(
    enabled=True,
    maintenance_interval=600,  # 10分钟间隔
    default_max_length=8000,   # 默认最大长度
    stream_limits={
        "motor_raw_data": 5000,           # 原始数据
        "fault_diagnosis_results": 10000, # 诊断结果  
        "vehicle_health_assessments": 8000, # 健康评估
        "performance_metrics": 3000,       # 性能指标
        "system_alerts": 15000            # 系统告警
    },
    approximate_trim=True,      # 近似裁剪，性能更好
    max_operations_per_cycle=5, # 单次操作数限制
    operation_delay=0.2        # 操作间延迟
)
```

### 配置原则

1. **分级策略**：
   - 系统告警 (15000) - 最重要，保留最多
   - 诊断结果 (10000) - 重要业务数据
   - 健康评估 (8000) - 中等重要性
   - 原始数据 (5000) - 高频但可清理
   - 性能指标 (3000) - 可较激进清理

2. **保守设置**：
   - 10分钟维护间隔，不影响业务
   - 单次最多5个操作，避免系统压力
   - 操作间0.2秒延迟，更加安全

## 📊 监控和统计

### 统计信息

```json
{
  "enabled": true,
  "running": true,
  "stats": {
    "total_cycles": 24,
    "total_trimmed": 12,
    "total_messages_removed": 15420,
    "last_maintenance": "2025-01-20T10:30:00",
    "error_count": 0
  },
  "stream_stats": {
    "motor_raw_data": {
      "trim_count": 5,
      "messages_removed": 8500,
      "last_trimmed": "2025-01-20T10:30:00"
    }
  },
  "recent_errors": []
}
```

### 关键指标

- **total_cycles**: 总维护周期数
- **total_trimmed**: 总裁剪次数  
- **total_messages_removed**: 总删除消息数
- **stream_stats**: 各Stream的详细统计

## 🔧 高级用法

### 动态配置更新

```python
# 更新配置
config_updates = {
    "maintenance_interval": 300,  # 改为5分钟
    "stream_limits": {
        "motor_raw_data": 3000    # 更激进的清理
    }
}
await stream_manager.update_maintenance_config(config_updates)
```

### 手动维护

```python
# 手动裁剪特定Stream
result = await stream_manager.manual_trim_stream("motor_raw_data", 2000)
print(f"裁剪结果: {result}")
```

### Stream信息查看

```python
# 获取所有Stream信息
info = await stream_manager.get_stream_info()
for stream_name, stream_data in info["streams"].items():
    print(f"{stream_name}: 长度={stream_data['length']}")
```

## ⚠️ 注意事项

### 安全考虑

1. **数据丢失风险**：裁剪会永久删除旧数据，请确认业务可接受
2. **消费者组影响**：裁剪不会影响消费者组的pending消息
3. **性能影响**：维护期间可能对Redis造成短暂压力

### 最佳实践

1. **渐进式启用**：先在测试环境验证配置
2. **监控观察**：密切关注维护统计和错误日志
3. **配置调优**：根据实际业务情况调整Stream限制
4. **备份重要数据**：对关键Stream考虑额外备份

## 🛠️ 故障排除

### 常见问题

1. **维护功能未启动**
   ```bash
   # 检查初始化状态
   curl "http://localhost:8000/api/v1/diagnosis-stream/maintenance/stats"
   
   # 手动启动
   curl -X POST "http://localhost:8000/api/v1/diagnosis-stream/maintenance/start"
   ```

2. **Redis连接问题**
   ```python
   # 检查Redis连接
   stats = await stream_manager.get_maintenance_stats()
   if "error" in stats:
       print(f"维护功能异常: {stats['error']}")
   ```

3. **配置不生效**
   ```python
   # 重新初始化
   await stream_manager.stop_stream_maintenance()
   await stream_manager.start_stream_maintenance()
   ```

### 日志监控

关注以下日志关键字：
- `Stream维护` - 维护功能相关
- `XTRIM` - 裁剪操作
- `maintenance` - 维护统计

## 📈 性能影响评估

### 资源消耗

- **CPU**: 每10分钟约1-2秒的轻微占用
- **内存**: 维护功能本身占用<1MB
- **网络**: 每次维护约几KB的Redis通信
- **Redis**: 每个XTRIM操作约1-10ms

### 业务影响

- **数据写入**: 无影响
- **数据读取**: 维护期间可能有微秒级延迟
- **消费者组**: 无影响
- **系统稳定性**: 显著改善（避免内存溢出）

## 🔄 升级和迁移

### 现有系统集成

维护功能采用**完全非侵入式**设计：

1. **无需修改现有代码**
2. **无需重启服务**（可选）
3. **无需数据迁移**
4. **可随时启用/禁用**

### 回滚方案

如需禁用维护功能：

```python
# 方案1：停止维护但保留功能
await stream_manager.stop_stream_maintenance()

# 方案2：初始化时禁用
await stream_manager.initialize(enable_maintenance=False)

# 方案3：配置禁用
await stream_manager.update_maintenance_config({"enabled": False})
```

---

**🎯 总结**：Redis Stream维护功能提供了一个安全、可靠的内存管理解决方案，通过定期XTRIM清理有效防止内存无限增长，同时保持系统的高可用性和业务连续性。 