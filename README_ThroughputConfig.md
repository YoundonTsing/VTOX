# 吞吐量配置管理系统

## 🎯 概述

本系统提供了完整的吞吐量递减优化解决方案，通过可视化界面动态调整吞吐量计算参数，有效减少递减速度，提升系统性能表现。

## ✨ 核心功能

### 1. 可配置的新鲜度因子
- **时间窗口调整**: 从30分钟扩展到10-180分钟可配置范围
- **最小新鲜度因子**: 从0.1提升到0.1-0.8可配置范围
- **递减曲线优化**: 支持线性、对数、指数、平方根多种曲线类型

### 2. 自动数据刷新服务
- **智能检测**: 自动检测数据年龄，防止数据过期
- **定期刷新**: 每5分钟检查一次，超过阈值自动添加新数据
- **手动触发**: 支持通过API或界面手动触发数据刷新

### 3. 实时配置管理API
- **动态调整**: 无需重启系统即可调整所有参数
- **配置预设**: 提供5种场景的预设配置
- **效果预览**: 实时预览不同参数下的递减曲线

## 🚀 快速开始

### 方式1: 使用启动脚本（推荐）
```bash
# 运行启动脚本，自动启动全系统
.\start_throughput_system.bat
```

### 方式2: 手动启动
```bash
# 1. 启动Redis
redis-server

# 2. 启动后端
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. 启动前端
cd frontend  
npm run dev
```

## 📊 访问地址

| 功能 | 地址 | 说明 |
|------|------|------|
| 🏠 前端主页 | http://localhost:3000 | 系统主入口 |
| 🔧 吞吐量配置 | http://localhost:3000/config/throughput | **核心配置界面** |
| 📈 集群状态监控 | http://localhost:3000/monitor/cluster-status | 查看吞吐量实时变化 |
| 📚 API文档 | http://localhost:8000/docs | 后端API文档 |

## 🎨 界面功能详解

### 1. 当前配置显示
显示系统当前使用的所有配置参数，包括：
- 时间窗口（分钟）
- 最小新鲜度因子  
- 递减曲线类型
- 自动刷新状态
- 基础乘数等

### 2. 配置调整面板
提供滑块和下拉选择器调整参数：
- **时间窗口**: 10-180分钟，数值越大递减越慢
- **最小新鲜度因子**: 0.1-0.8，数值越大保底值越高
- **递减曲线**: 对数曲线最平缓，指数曲线最陡峭
- **递减陡峭程度**: 0.1-2.0，数值越小越平缓

### 3. 曲线预览图表
使用ECharts实时显示新鲜度因子随时间的变化曲线，帮助可视化不同参数的效果。

### 4. 配置预设卡片
提供5种预设配置快速应用：

| 预设 | 适用场景 | 特点 |
|------|----------|------|
| 🏛️ 稳定模式 | 生产环境长期运行 | 90分钟窗口，对数曲线，递减缓慢 |
| ⚡ 响应模式 | 实时监控场景 | 45分钟窗口，指数曲线，快速响应 |
| 🛡️ 保守模式 | 数据保持时间长 | 120分钟窗口，极平缓递减 |
| 🚀 性能模式 | 高负载高吞吐量 | 60分钟窗口，高基础乘数 |
| 🧪 测试模式 | 开发调试环境 | 30分钟窗口，快速变化 |

### 5. 实时测试工具
- **开始测试**: 连续5次调用API，观察吞吐量变化趋势
- **手动刷新**: 立即向performance_metrics流添加新数据
- **性能监控**: 实时显示当前吞吐量、延迟、队列长度

## 🔧 API接口

### 配置管理
```http
GET /api/v1/config/throughput          # 获取当前配置
PUT /api/v1/config/throughput          # 更新配置
POST /api/v1/config/throughput/reset   # 重置默认配置
```

### 数据操作  
```http
POST /api/v1/config/throughput/refresh # 手动刷新数据
GET /api/v1/config/throughput/preview  # 预览曲线效果
```

### 状态监控
```http
GET /api/v1/cluster/status             # 获取集群状态和吞吐量
```

## 📈 优化效果

### 优化前
- 时间窗口: 30分钟（固定）
- 最小因子: 0.1（固定）
- 递减类型: 线性（固定）
- 典型递减: 31.9→31.7→31.5→31.3→31.1 (每3秒-0.2)

### 优化后
- 时间窗口: 60-90分钟（可配置）
- 最小因子: 0.3-0.4（可配置）
- 递减类型: 对数曲线（更平缓）
- **预期递减速度降低50-70%**

## 🛠 高级用法

### 1. 使用配置预设工具
```bash
# 列出所有预设
python throughput_presets.py list

# 应用稳定模式
python throughput_presets.py apply stable

# 比较两个预设
python throughput_presets.py compare stable responsive

# 查找最匹配的预设
python throughput_presets.py match
```

### 2. 运行测试验证
```bash
# 快速API测试
python test_api_quick.py

# 完整优化测试
python test_optimization_simple.py

# 原始功能测试
python test_throughput_optimization.py
```

### 3. 自定义配置
通过API或界面自定义配置参数：
```json
{
  "freshness_window_minutes": 75,
  "min_freshness_factor": 0.35,
  "decay_curve_type": "logarithmic",
  "decay_steepness": 0.4,
  "auto_refresh_enabled": true,
  "base_throughput_multiplier": 9.0
}
```

## 📋 使用建议

### 生产环境配置
```bash
python throughput_presets.py apply stable
```
- 90分钟时间窗口确保数据持久性
- 对数曲线提供平滑递减
- 0.4最小因子保证基底性能

### 测试环境配置  
```bash
python throughput_presets.py apply responsive
```
- 45分钟窗口快速响应变化
- 指数曲线敏感反映数据状态
- 适合调试和测试场景

### 高负载环境配置
```bash
python throughput_presets.py apply performance  
```
- 高基础乘数支持大吞吐量
- 线性递减确保稳定性
- 适合高并发生产环境

## 🔍 故障排除

### 1. 后端API无法访问
```bash
# 检查后端是否启动
curl http://localhost:8000/api/v1/config/throughput

# 检查Redis连接
redis-cli ping
```

### 2. 前端界面空白
- 确保后端API正常响应
- 检查浏览器控制台错误
- 验证路由配置是否正确

### 3. 配置不生效
- 确认配置更新API返回成功
- 检查后端日志是否有错误
- 验证新配置是否被正确加载

### 4. 自动刷新不工作
- 检查AutoRefreshService是否启动
- 确认Redis连接正常
- 查看后端日志中的刷新记录

## 📝 更新日志

### v1.0.0 (当前版本)
- ✅ 实现可配置的新鲜度因子系统
- ✅ 添加自动数据刷新服务
- ✅ 创建完整的配置管理API
- ✅ 构建可视化配置界面
- ✅ 提供5种配置预设
- ✅ 支持实时曲线预览
- ✅ 集成测试和验证工具

## 🤝 技术支持

如需技术支持或发现问题，请：
1. 运行测试脚本收集诊断信息
2. 检查后端日志输出
3. 查看API文档进行调试
4. 参考故障排除章节

---

**🎉 恭喜！您已成功部署吞吐量配置管理系统。现在可以通过可视化界面轻松优化系统性能了！**