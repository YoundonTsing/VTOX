# VTOX分布式集群集成说明

## 概述

VTOX系统已成功集成分布式微服务集群功能到main.py中。现在通过单一的uvicorn命令即可启动完整的分布式电机故障诊断系统。

## 一键启动

### 方式1: 使用启动脚本（推荐）
```batch
# 在vtox项目根目录运行
start_distributed_system.bat
```

### 方式2: 手动命令
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 系统架构

启动后系统将包含：

### 🖥️ 主要服务
- **FastAPI后端** (端口8000) - 主API服务
- **集群协调器** (端口8001) - 任务分配和协调
- **Worker节点** (端口8002-8004) - 故障诊断处理
- **Redis Stream桥接器** - 实时数据流处理
- **自动数据刷新服务** - 性能数据维护

### 🔧 Worker节点分工
- **Worker 1** (8002): 匝间短路、绝缘故障诊断
- **Worker 2** (8003): 轴承、偏心故障诊断  
- **Worker 3** (8004): 断条故障诊断

## 环境变量配置

系统支持通过环境变量灵活配置：

```bash
# 集群模式 (development/testing/production)
set VTOX_CLUSTER_MODE=development

# Worker节点数量
set VTOX_CLUSTER_WORKERS=3

# 是否启用集群 (true/false)
set VTOX_CLUSTER_ENABLED=true
```

### 部署模式说明

#### 开发模式 (development)
- 3个Worker节点
- localhost绑定
- 10秒监控间隔
- 适合开发调试

#### 测试模式 (testing)  
- 2个Worker节点
- 5秒监控间隔
- 适合功能测试

#### 生产模式 (production)
- 6个Worker节点
- 0.0.0.0绑定
- 15秒监控间隔
- 适合生产部署

## 系统访问

### 🌐 Web界面
- **API文档**: http://localhost:8000/docs
- **系统状态**: http://localhost:8000
- **集群状态**: http://localhost:8000/api/v1/cluster/status

### 📊 状态监控
```bash
# 检查系统状态
curl http://localhost:8000/

# 检查集群详细状态  
curl http://localhost:8000/api/v1/cluster/status

# 检查吞吐量计算
curl http://localhost:8000/api/v1/cluster/status | jq '.data.performance_metrics.throughput'
```

## 验证测试

运行集成测试验证系统状态：
```bash
python test_cluster_integration.py
```

测试包括：
- ✅ API根路径和集群信息
- ✅ Redis服务和集群组件
- ✅ 吞吐量计算修复验证

## 重要改进

### 🚀 吞吐量计算修复
系统已修复吞吐量计算问题：
- **修复前**: 基于performance_metrics记录数，严重低估（1.6 msg/s）
- **修复后**: 基于motor_raw_data实际流量，准确反映50台车并发数据

### 📈 三级递减策略
1. **方法1**: Performance Metrics流计算（最优先，基于实际流量）
2. **方法2**: Stream活跃度计算（次优先）
3. **方法3**: 消费者动态估算（保底方案）

## 故障排除

### 常见问题

#### 1. 集群启动失败
```bash
# 检查Redis服务
redis-cli ping

# 检查端口占用
netstat -an | findstr ":800"

# 查看启动日志
```

#### 2. Worker节点连接失败
- 确保防火墙允许8001-8004端口
- 检查Redis连接配置
- 验证集群模块导入路径

#### 3. 吞吐量显示异常
- 确认数据模拟器正在运行
- 检查motor_raw_data流是否有数据
- 验证performance_metrics自动刷新

### 日志查看
```bash
# 主要日志在控制台输出
# 集群日志在cluster.log文件

# 检查Redis Stream状态
redis-cli XLEN motor_raw_data
redis-cli XINFO GROUPS motor_raw_data
```

## 性能优化建议

### 🔧 开发环境
- 使用默认配置（3个Worker）
- 启用详细日志输出
- 监控间隔10秒

### 🏭 生产环境
```bash
# 设置生产模式
set VTOX_CLUSTER_MODE=production
set VTOX_CLUSTER_WORKERS=6

# 启动
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 📊 扩展配置
- 根据CPU核心数调整Worker数量
- 根据内存容量配置队列大小
- 根据网络带宽调整监控间隔

## 注意事项

1. **资源要求**: 集群模式需要更多内存和CPU资源
2. **端口管理**: 确保8000-8007端口可用
3. **Redis依赖**: 集群功能强依赖Redis服务
4. **数据一致性**: 多Worker环境下注意数据同步
5. **监控告警**: 生产环境建议配置监控告警

## 下一步扩展

- [ ] 支持多机部署
- [ ] 添加负载均衡
- [ ] 集成监控面板
- [ ] 支持动态扩缩容
- [ ] 添加故障自动恢复