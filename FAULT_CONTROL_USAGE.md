# 多故障模拟器 - 故障严重程度控制说明

## 🎯 功能概述

`turn_fault_simulator.py` 现在支持通过命令行参数灵活控制各种故障的严重程度范围，让您可以模拟不同程度的故障场景。

## 📋 可控制的故障类型

1. **匝间短路故障** (`turn_fault`)
2. **断条故障** (`broken_bar`) 
3. **绝缘失效** (`insulation`)
4. **轴承故障** (`bearing`)
5. **偏心故障** (`eccentricity`)

## 🔧 使用方法

### 方法一：预设故障模式 (推荐)

使用预定义的故障严重程度模式：

```bash
# 轻微故障模式 (0.05 - 0.35范围)
python turn_fault_simulator.py --fault-mode light

# 正常故障模式 (0.1 - 0.7范围) 
python turn_fault_simulator.py --fault-mode normal

# 严重故障模式 (0.25 - 0.85范围)
python turn_fault_simulator.py --fault-mode severe

# 危急故障模式 (0.5 - 0.95范围)
python turn_fault_simulator.py --fault-mode critical
```

### 方法二：单独控制每种故障

精确控制每种故障的严重程度范围：

```bash
# 自定义各种故障的范围
python turn_fault_simulator.py \
  --turn-fault-range 0.2 0.8 \
  --broken-bar-range 0.1 0.6 \
  --insulation-range 0.05 0.4 \
  --bearing-range 0.3 0.9 \
  --eccentricity-range 0.1 0.5
```

### 方法三：结合其他参数

```bash
# 组合使用增强系数和故障模式
python turn_fault_simulator.py \
  --enhancement 2.0 \
  --fault-mode severe \
  --sampling-rate 4000 \
  --batch-size 400
```

## 📊 预设故障模式详细说明

| 模式 | 描述 | 匝间短路 | 断条 | 绝缘失效 | 轴承 | 偏心 |
|------|------|----------|------|----------|------|------|
| `light` | 轻微故障 | 0.05-0.3 | 0.05-0.25 | 0.05-0.2 | 0.05-0.35 | 0.05-0.2 |
| `normal` | 正常故障 | 0.1-0.6 | 0.1-0.5 | 0.1-0.4 | 0.1-0.7 | 0.1-0.4 |
| `severe` | 严重故障 | 0.3-0.8 | 0.3-0.75 | 0.25-0.65 | 0.3-0.85 | 0.25-0.6 |
| `critical` | 危急故障 | 0.6-0.95 | 0.6-0.9 | 0.5-0.8 | 0.6-0.95 | 0.5-0.8 |

## 💡 实用示例

### 测试轻微故障场景
适合测试早期故障检测算法：
```bash
python turn_fault_simulator.py --fault-mode light --enhancement 1.0
```

### 模拟高风险生产环境  
适合测试严重故障的诊断能力：
```bash
python turn_fault_simulator.py --fault-mode critical --enhancement 2.5
```

### 针对特定故障类型测试
只关注轴承故障，其他故障设为很低：
```bash
python turn_fault_simulator.py \
  --turn-fault-range 0.01 0.1 \
  --broken-bar-range 0.01 0.1 \
  --insulation-range 0.01 0.1 \
  --bearing-range 0.6 0.9 \
  --eccentricity-range 0.01 0.1
```

### 模拟渐进式故障发展
通过多次启动，逐步增加故障严重程度：
```bash
# 第一阶段：早期故障
python turn_fault_simulator.py --fault-mode light

# 第二阶段：发展期故障  
python turn_fault_simulator.py --fault-mode normal

# 第三阶段：严重故障
python turn_fault_simulator.py --fault-mode severe
```

## 🎛️ 完整参数列表

```bash
python turn_fault_simulator.py --help
```

**基础参数**:
- `--host`: 服务器地址 (默认: localhost)
- `--port`: 服务器端口 (默认: 8000)  
- `--sampling-rate`: 采样率Hz (默认: 8000)
- `--batch-size`: 批次大小 (默认: 800)
- `--enhancement`: 增强系数 (默认: 1.5)

**故障控制参数**:
- `--fault-mode`: 预设模式 [light|normal|severe|critical]
- `--turn-fault-range MIN MAX`: 匝间短路范围
- `--broken-bar-range MIN MAX`: 断条故障范围  
- `--insulation-range MIN MAX`: 绝缘失效范围
- `--bearing-range MIN MAX`: 轴承故障范围
- `--eccentricity-range MIN MAX`: 偏心故障范围

## ⚙️ 技术说明

### 故障严重程度含义
- **0.0**: 无故障
- **0.1-0.3**: 轻微故障
- **0.3-0.6**: 中等故障  
- **0.6-0.8**: 严重故障
- **0.8-1.0**: 危急故障

### 阈值机制
只有当随机生成的故障严重程度 > 0.2 时，该故障特征才会被添加到信号中。

### 实时调整
每个数据批次都会重新随机生成故障严重程度，在设定范围内变化，模拟真实的故障发展过程。

## 🎉 使用建议

1. **开发阶段**: 使用 `--fault-mode light` 进行基础测试
2. **算法训练**: 使用 `--fault-mode normal` 获得平衡的数据集
3. **极限测试**: 使用 `--fault-mode critical` 测试算法的极限能力
4. **特定研究**: 使用单独的范围参数精确控制目标故障类型

通过这些灵活的控制选项，您可以精确模拟各种故障场景，为故障诊断算法提供丰富多样的测试数据！ 