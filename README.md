# 电机匝间短路故障诊断系统

这是一个基于Vue3+Vite前端和FastAPI后端的电机匝间短路故障诊断系统。系统可以分析电机运行数据，诊断可能存在的匝间短路故障。

## 功能特点

- **数据上传与分析**: 支持上传CSV格式的电机运行数据，系统自动分析并诊断匝间短路故障
- **自动数据格式转换**: 支持多种数据格式，自动将传感器原始数据转换为标准格式
- **故障评分与等级**: 提供0-1之间的故障概率评分，并给出正常/预警/故障三级诊断结果
- **特征参数分析**: 详细展示负序电流、电流不平衡度、DQ轴电流残差等关键诊断参数
- **动态阈值配置**: 允许用户自定义警告和故障阈值，灵活适应不同应用场景
- **可视化展示**: 通过图表直观展示诊断结果和关键参数


<img width="1920" height="889" alt="wechat_2025-08-28_151642_802" src="https://github.com/user-attachments/assets/5f65ad09-6827-41fa-81cb-991202e56644" />





## 系统架构

- **前端**: Vue3 + Vite + Element Plus + ECharts
- **后端**: FastAPI + Pandas + NumPy + SciPy

## 快速开始

### 前端部署

```bash
cd frontend
npm install
npm run dev
```

前端默认在 http://localhost:3000 运行

### 后端部署

```bash
cd backend
pip install -r requirements.txt
python run.py
```

后端API默认在 http://localhost:8000 运行

## 数据格式支持

系统支持以下CSV数据格式：

### 标准格式

```
timestamp,Ia,Ib,Ic,Vdc,Torque,Speed,Iq_actual,Iq_ref,I2_ref,Eta_ref,Id_actual
2023-10-01T08:31:09.549Z,10.02,8.56,10.78,384.54,155.36,3011.9,5.1,5,0.02,0.93,0.63
```

### 传感器原始格式

系统可自动处理如下格式的传感器原始数据：

```
Time[s],MotorRpm[Rpm],BUS_500K_DBC23BusVoltage,MotorTem,AphaseCurrent[A],BPhaseCurrent[A],CPhaseCurrent[A]
0,999,686,49,24,24,26
```

### 自动数据处理说明

系统会自动将传感器原始数据转换为分析所需的标准格式：

1. **d轴/q轴电流计算**：使用三相电流通过Clarke-Park变换计算
2. **扭矩估算**：使用q轴电流和扭矩常数估算
3. **缺失参数处理**：为缺失的参考值设置合理的默认值

详细的数据处理算法：

```python
# 关键计算逻辑
# d轴/q轴电流计算 (使用Clarke-Park变换)
def abc_to_dq(ia, ib, ic, rpm, time_elapsed):
    # Clarke变换 (3相 → α-β)
    i_alpha = (2*ia - ib - ic) / 3
    i_beta = (ib - ic) / np.sqrt(3)
    
    # 计算电角度
    freq = (rpm * pole_pairs) / 60
    theta = 2 * np.pi * freq * time_elapsed
    
    # Park变换 (α-β → dq)
    id = i_alpha * np.cos(theta) + i_beta * np.sin(theta)
    iq = -i_alpha * np.sin(theta) + i_beta * np.cos(theta)
    
    return id, iq
```

## 匝间短路故障诊断

系统使用多个特征参数综合评估匝间短路故障：

- **负序电流分量 (I₂)**：反映三相不平衡程度
- **电流不平衡度**：三相电流最大差异与平均值的比值
- **DQ轴电流残差**：实际与参考值的差异
- **ΔI_q的峭度**：反映瞬态异常程度
- **效率残差**：反映额外损耗

诊断阈值：
- **预警阈值**: 0.3 (默认值，可配置)
- **故障阈值**: 0.7 (默认值，可配置)

## API文档

后端API文档可在启动后访问：http://localhost:8000/docs

## 注意事项

- 系统默认使用4极对永磁同步电机模型，如需调整，请修改后端配置
- 为获得更精确的诊断结果，建议使用至少包含100个数据点的CSV文件 

## 匝间短路故障实时诊断系统

### 系统架构

```
+------------------+        +------------------+        +------------------+
|  数据源模拟应用   | ------ |    后端服务       | ------ |    前端监控界面   |
| (Python, 端口8000) | WebSocket | (FastAPI, 端口8000) | WebSocket | (Vue, 端口3000)       |
+------------------+        +------------------+        +------------------+
```
