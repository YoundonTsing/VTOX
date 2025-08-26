
import numpy as np
from scipy import signal
import pandas as pd
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("eccentricity-analyzer")

class EccentricityAnalyzer:
    """偏心故障分析器"""
    
    def __init__(self):
        self.warning_threshold = 0.03  # 预警阈值，与前端保持一致
        self.fault_threshold = 0.06    # 故障阈值，与前端保持一致
    
    def analyze(self, data_batch):
        """分析数据批次，检测偏心故障"""
        try:
            # 提取电流数据
            if 'data' in data_batch:
                df = pd.DataFrame(data_batch['data'])
            else:
                logger.error("数据格式错误，缺少'data'字段")
                return None
            
            # 检查必要的列是否存在
            required_columns = ['Ia', 'Ib', 'Ic'] # 偏心故障通常分析三相电流
            if not all(col in df.columns for col in required_columns):
                logger.error(f"数据缺少必要的电流列: {required_columns}")
                return None
            
            # 获取采样率
            sampling_rate = data_batch.get('sampling_rate', 10000) # 默认为10kHz
            
            # 提取三相电流
            ia = df['Ia'].values
            ib = df['Ib'].values
            ic = df['Ic'].values

            # 简化：使用A相电流进行频谱分析，提取主要谐波
            n = len(ia)
            yf_a = np.fft.fft(ia)
            xf = np.fft.fftfreq(n, 1 / sampling_rate)

            # 找到基频幅值（假设50Hz）
            fundamental_freq = 50.0
            fundamental_idx = np.argmin(np.abs(xf - fundamental_freq))
            fundamental_amp = np.abs(yf_a[fundamental_idx])
            
            # 特征1: 静偏心比 (Static Eccentricity Ratio)
            # 静偏心通常引起负序电流增加，或者基频两侧的特定谐波增加
            # 这里我们简化模拟一个值，实际需要结合电流波形畸变和谐波分析
            static_ecc_ratio = np.random.uniform(0.01, 0.05) # 模拟一个随机值
            if fundamental_amp > 0:
                 # 模拟与特定谐波（例如3次谐波）的幅值比例相关
                third_harmonic_freq = fundamental_freq * 3
                third_harmonic_idx = np.argmin(np.abs(xf - third_harmonic_freq))
                third_harmonic_amp = np.abs(yf_a[third_harmonic_idx])
                static_ecc_ratio = third_harmonic_amp / fundamental_amp * 0.1 # 模拟计算
            
            # 特征2: 动偏心比 (Dynamic Eccentricity Ratio)
            # 动偏心通常引起转子槽频谐波和边带谐波增加
            # 这里我们简化模拟一个值
            dynamic_ecc_ratio = np.random.uniform(0.01, 0.05) # 模拟一个随机值
            if fundamental_amp > 0:
                # 模拟与特定谐波（例如5次谐波）的幅值比例相关
                fifth_harmonic_freq = fundamental_freq * 5
                fifth_harmonic_idx = np.argmin(np.abs(xf - fifth_harmonic_freq))
                fifth_harmonic_amp = np.abs(yf_a[fifth_harmonic_idx])
                dynamic_ecc_ratio = fifth_harmonic_amp / fundamental_amp * 0.1 # 模拟计算

            # 特征3: 偏心故障指数 (Eccentricity Index)
            # 综合静偏心和动偏心的影响
            eccentricity_index = (static_ecc_ratio + dynamic_ecc_ratio) / 2.0 # 模拟计算

            # 计算综合故障评分
            # 偏心比越大，故障分数越高
            # 对特征进行归一化处理，使其值在0-1之间
            norm_static_ecc_ratio = min(1.0, static_ecc_ratio / 0.1) # 假设0.1为最大正常值
            norm_dynamic_ecc_ratio = min(1.0, dynamic_ecc_ratio / 0.1)
            norm_eccentricity_index = min(1.0, eccentricity_index / 0.1)

            weights = {
                'static_ecc_ratio': 0.4,
                'dynamic_ecc_ratio': 0.4,
                'eccentricity_index': 0.2
            }
            
            fault_score = (weights['static_ecc_ratio'] * norm_static_ecc_ratio + 
                          weights['dynamic_ecc_ratio'] * norm_dynamic_ecc_ratio + 
                          weights['eccentricity_index'] * norm_eccentricity_index)
            
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
                diagnosis_conclusion = "电机运行正常，未检测到偏心故障特征。"
                suggestions = ["继续正常运行", "定期检查电机安装和轴承状况"]
            elif status == "warning":
                diagnosis_conclusion = "检测到轻微偏心故障特征，建议密切监控。"
                suggestions = [
                    "增加电流和振动监测频率",
                    "检查电机基础和联轴器对中情况",
                    "考虑进行电机动平衡检测"
                ]
            else:
                diagnosis_conclusion = "警告：检测到明显偏心故障特征，建议尽快检修电机。"
                suggestions = [
                    "立即停机，防止定转子摩擦",
                    "检查轴承和转子，进行动平衡处理",
                    "检查电机安装精度和对中性"
                ]
            
            # 准备时域数据（采样以减少数据量）
            sample_rate = max(1, len(df) // 200)  # 最多返回200个点
            time_series = {
                "time": df['时间'].iloc[::sample_rate].tolist(),
                "values_a": df['Ia'].iloc[::sample_rate].tolist(),
                "values_b": df['Ib'].iloc[::sample_rate].tolist(),
                "values_c": df['Ic'].iloc[::sample_rate].tolist()
            }
            
            # 准备频域数据（同样采样）
            freq_sample_rate = max(1, len(xf) // 200)
            frequency_spectrum = {
                "frequency": xf[::freq_sample_rate].tolist(),
                "amplitude_a": np.abs(yf_a[::freq_sample_rate]).tolist(),
                "amplitude_b": [], # 如果需要，可以计算Ib, Ic的频谱
                "amplitude_c": []
            }
            
            # 构建结果
            result = {
                "timestamp": datetime.now().isoformat(),
                "status": status,
                "score": float(fault_score),
                "features": {
                    "static_ecc_ratio": float(static_ecc_ratio),
                    "dynamic_ecc_ratio": float(dynamic_ecc_ratio),
                    "eccentricity_index": float(eccentricity_index),
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
            required_columns = ['时间', 'Ia', 'Ib', 'Ic']
            if not all(col in df.columns for col in required_columns):
                logger.error(f"CSV文件缺少必要的列: {required_columns}")
                return None
            
            # 构造数据批次
            data_batch = {
                "data": df.to_dict(orient='records'),
                "sampling_rate": 10000  # 假设采样率为10kHz
            }
            
            # 调用分析方法
            return self.analyze(data_batch)
            
        except Exception as e:
            logger.error(f"分析文件时出错: {e}", exc_info=True)
            return None 