
import numpy as np
import pandas as pd
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("insulation-analyzer")

class InsulationAnalyzer:
    """绝缘失效分析器"""
    
    def __init__(self):
        self.warning_threshold = 0.1  # 预警阈值，与前端保持一致
        self.fault_threshold = 0.2    # 故障阈值，与前端保持一致
    
    def analyze(self, data_batch):
        """分析数据批次，检测绝缘失效"""
        try:
            # 提取数据
            if 'data' in data_batch:
                df = pd.DataFrame(data_batch['data'])
            else:
                logger.error("数据格式错误，缺少'data'字段")
                return None
            
            # 检查必要的列是否存在 - 使用电流和温度数据检测绝缘故障
            current_columns = ['Ia', 'Ib', 'Ic']  # 三相电流
            temp_columns = ['温度', 'temperature']  # 温度
            
            # 查找可用的电流列
            available_current_cols = [col for col in current_columns if col in df.columns]
            available_temp_cols = [col for col in temp_columns if col in df.columns]
            
            if len(available_current_cols) < 3:
                logger.error(f"数据缺少三相电流数据，需要: {current_columns}, 可用: {available_current_cols}")
                return None
                
            if not available_temp_cols:
                logger.warning(f"数据缺少温度数据，将跳过温度分析，支持的列名: {temp_columns}")
                temp_col = None
            else:
                temp_col = available_temp_cols[0]
            
            # 提取三相电流数据
            ia_data = df[available_current_cols[0]].values
            ib_data = df[available_current_cols[1]].values  
            ic_data = df[available_current_cols[2]].values
            
            # 提取温度数据（如果有）
            temp_data = df[temp_col].values if temp_col else None
            
            if len(ia_data) == 0:
                logger.warning("电流数据为空，无法进行绝缘分析。")
                return None
            
            # 特征1: 电流不平衡 (Current Imbalance)
            # 计算三相电流的平均值和标准差
            avg_current = np.mean(ia_data)
            std_current = np.std(ia_data)
            
            # 计算电流不平衡度
            # 假设电流不平衡度超过0.15表示异常
            current_imbalance = std_current / avg_current if avg_current > 0 else 0.0
            
            # 特征2: 温度异常 (Temperature Anomaly)
            # 假设温度超过40度表示异常
            temp_anomaly = 0.0
            if temp_data is not None and len(temp_data) > 0:
                avg_temp = np.mean(temp_data)
                std_temp = np.std(temp_data)
                temp_anomaly = std_temp / avg_temp if avg_temp > 0 else 0.0
            
            # 特征3: 介质损耗 (Dielectric Loss)
            # 介质损耗通常需要复杂的测量设备，这里我们基于绝缘电阻和泄漏电流进行模拟。
            # 假设介质损耗与泄漏电流成正比，与绝缘电阻成反比。
            # 这里为简化，给出一个模拟计算，实际应根据具体模型来计算。
            dielectric_loss = (current_imbalance / 10) * 1000 if current_imbalance > 0 else 0.0 # 模拟归一化到0-1之间

            # 计算综合故障评分
            # 电流不平衡越大，温度异常越大，介质损耗越大，分数越高。
            # 需要将特征转换为与故障程度正相关的指标。
            # 例如，使用电流不平衡的倒数，或将其与参考值比较。
            # 这里我们假设电流不平衡的“好”是低值，所以取其倒数来反映故障程度。
            # 为了避免除以零，并使数值有意义，进行适当缩放和处理。

            # 将电流不平衡反向处理，使其与故障程度正相关
            # 假设正常电流不平衡很低，比如0.05。故障时可能达到0.15。
            # 我们将其转换为一个0-1的得分，电流不平衡越大，得分越高。
            # 例如，使用 1 / (current_imbalance + epsilon) 或者 (max_current_imbalance - current_imbalance) / max_current_imbalance
            # 这里简单模拟，电流不平衡越大，得分越高。
            score_from_current_imbalance = 0.0
            if current_imbalance > 0.05: # 故障
                score_from_current_imbalance = 1.0
            elif current_imbalance > 0.02: # 预警
                score_from_current_imbalance = 0.5
            else: # 正常
                score_from_current_imbalance = 0.0

            # 温度异常直接与故障程度正相关
            # 假设0.05是预警，0.1是故障
            score_from_temp_anomaly = 0.0
            if temp_anomaly > 0.1: # 故障
                score_from_temp_anomaly = 1.0
            elif temp_anomaly > 0.05: # 预警
                score_from_temp_anomaly = 0.5
            else: # 正常
                score_from_temp_anomaly = 0.0

            # 介质损耗直接与故障程度正相关
            score_from_dielectric_loss = dielectric_loss # 因为之前已经模拟归一化到0-1
            
            # 权重可以根据实际情况调整
            weights = {
                'current_imbalance': 0.4,
                'temp_anomaly': 0.3,
                'dielectric_loss': 0.3
            }
            
            fault_score = (weights['current_imbalance'] * score_from_current_imbalance + 
                          weights['temp_anomaly'] * score_from_temp_anomaly + 
                          weights['dielectric_loss'] * score_from_dielectric_loss)
            
            # 确定状态
            if fault_score > self.fault_threshold:
                status = "fault"
            elif fault_score > self.warning_threshold:
                status = "warning"
            else:
                status = "normal"
            
            # 估计故障严重程度
            if fault_score > self.warning_threshold:
                # 将故障评分归一化到0-1范围
                severity = min(1.0, fault_score / (self.fault_threshold * 1.5))
            else:
                severity = 0.0
            
            # 准备诊断结论
            if status == "normal":
                diagnosis_conclusion = "电机绝缘状况良好，未检测到绝缘失效特征。"
                suggestions = ["继续正常运行", "按计划进行绝缘预防性维护"]
            elif status == "warning":
                diagnosis_conclusion = "检测到轻微绝缘劣化特征，建议密切监控绝缘状况。"
                suggestions = [
                    "增加绝缘监测频率",
                    "检查环境湿度和温度对绝缘的影响",
                    "考虑进行进一步的绝缘测试（如吸收比、极化指数）"
                ]
            else:
                diagnosis_conclusion = "警告：检测到明显绝缘失效特征，建议立即停机检查并修复。"
                suggestions = [
                    "立即停机，防止故障扩大",
                    "进行全面的绝缘测试，定位故障点",
                    "修复或更换损坏的绝缘部件"
                ]
            
            # 准备时域数据（采样以减少数据量）
            sample_rate = max(1, len(df) // 200)  # 最多返回200个点
            time_series = {
                "time": df['时间'].iloc[::sample_rate].tolist() if '时间' in df.columns else list(range(len(df)))[::sample_rate],
                "values_current_imbalance": df['Ia'].iloc[::sample_rate].tolist() if 'Ia' in df.columns else [],
                "values_temp_anomaly": df[temp_col].iloc[::sample_rate].tolist() if temp_col in df.columns else []
            }
            
            # 绝缘失效通常没有频域分析，或者有特殊的频域分析方法（如介质损耗因数），这里留空或简化处理。
            frequency_spectrum = {
                "frequency": [],
                "amplitude": []
            }
            
            # 构建结果
            result = {
                "timestamp": datetime.now().isoformat(),
                "status": status,
                "score": float(fault_score),
                "features": {
                    "current_imbalance": float(current_imbalance),
                    "temp_anomaly": float(temp_anomaly),
                    "dielectric_loss": float(dielectric_loss),
                    "fault_severity": float(severity)
                },
                "time_series": time_series,
                "frequency_spectrum": frequency_spectrum,
                "diagnosis_conclusion": diagnosis_conclusion,
                "suggestions": suggestions
            }
            
            logger.info(f"分析结果 - 状态: {status}, 评分: {fault_score:.2f}, 特征: {result['features']}")
            return result
            
        except Exception as e:
            logger.error(f"分析数据时出错: {e}", exc_info=True)
            return None
    
    def analyze_file(self, file_path):
        """分析CSV文件中的数据"""
        try:
            # 读取CSV文件
            df = pd.read_csv(file_path)
            
            # 检查必要的列是否存在
            required_columns = ['时间', 'Ia', 'Ib', 'Ic'] # 假设需要这些列
            if not all(col in df.columns for col in required_columns):
                logger.error(f"CSV文件缺少必要的列: {required_columns}")
                return None
            
            # 构造数据批次
            data_batch = {
                "data": df.to_dict(orient='records'),
                "sampling_rate": 1 # 对于绝缘电阻和泄漏电流，采样率可能不那么关键，这里设为1
            }
            
            # 调用分析方法
            return self.analyze(data_batch)
            
        except Exception as e:
            logger.error(f"分析文件时出错: {e}", exc_info=True)
            return None 