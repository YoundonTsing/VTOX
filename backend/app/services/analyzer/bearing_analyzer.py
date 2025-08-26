
import numpy as np
from scipy import stats, signal
import pandas as pd
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bearing-analyzer")

class BearingAnalyzer:
    """轴承故障分析器 - 性能优化版本"""
    
    def __init__(self):
        self.warning_threshold = 0.3  # 预警阈值，与前端保持一致
        self.fault_threshold = 0.6    # 故障阈值，与前端保持一致
        
        # 性能优化配置
        self.chart_config = {
            "time_series_points": 50,    # 时域图数据点数
            "spectrum_points": 30,       # 频谱图数据点数
            "feature_history_points": 10  # 特征历史点数
        }
    
    def intelligent_vibration_sampling(self, time_data, vibration_data, target_points=50):
        """智能振动数据采样 - 保留冲击特征"""
        try:
            if len(time_data) <= target_points:
                return time_data, vibration_data
            
            # 1. 检测冲击特征点（轴承故障的关键特征）
            key_indices = []
            
            # 检测冲击峰值（高于平均值3倍标准差的点）
            mean_val = np.mean(np.abs(vibration_data))
            std_val = np.std(vibration_data)
            threshold = mean_val + 2 * std_val
            
            impact_peaks = np.where(np.abs(vibration_data) > threshold)[0]
            key_indices.extend(impact_peaks.tolist())
            
            # 检测峭度高的区域（表明有冲击）
            window_size = max(10, len(vibration_data) // 20)
            for i in range(0, len(vibration_data) - window_size, window_size):
                window_data = vibration_data[i:i+window_size]
                if len(window_data) > 3:
                    window_kurtosis = stats.kurtosis(window_data)
                    if window_kurtosis > 3:  # 正态分布的峭度为3
                        # 找到窗口内的最大值点
                        max_idx = i + np.argmax(np.abs(window_data))
                        key_indices.append(max_idx)
            
            # 去重并排序
            key_indices = sorted(list(set(key_indices)))
            key_indices = [idx for idx in key_indices if 0 <= idx < len(time_data)]
            
            # 2. 计算需要的均匀采样点数
            uniform_points_needed = max(0, target_points - len(key_indices))
            
            # 3. 均匀采样填充
            if uniform_points_needed > 0:
                uniform_indices = np.linspace(0, len(time_data) - 1, uniform_points_needed, dtype=int)
                all_indices = sorted(list(set(key_indices + uniform_indices.tolist())))
            else:
                all_indices = key_indices[:target_points]
            
            # 4. 确保不超过目标点数
            if len(all_indices) > target_points:
                # 优先保留冲击特征点
                key_set = set(key_indices)
                priority_indices = [idx for idx in all_indices if idx in key_set]
                remaining_indices = [idx for idx in all_indices if idx not in key_set]
                
                final_indices = priority_indices[:target_points//2] + remaining_indices[:target_points-len(priority_indices[:target_points//2])]
                all_indices = sorted(final_indices)
            
            # 提取采样数据
            sampled_time = [time_data[i] for i in all_indices]
            sampled_vibration = [vibration_data[i] for i in all_indices]
            
            return sampled_time, sampled_vibration
            
        except Exception as e:
            logger.warning(f"智能振动采样失败，使用均匀采样: {e}")
            # 降级到均匀采样
            indices = np.linspace(0, len(time_data) - 1, target_points, dtype=int)
            return [time_data[i] for i in indices], [vibration_data[i] for i in indices]
    
    def intelligent_bearing_spectrum_sampling(self, freq_data, amplitude_data, target_points=30):
        """智能轴承频谱采样 - 保留轴承特征频率"""
        try:
            if len(freq_data) <= target_points:
                return freq_data, amplitude_data
            
            # 1. 轴承故障特征频率（示例值，实际应根据轴承参数计算）
            bearing_frequencies = [
                120.5,  # 外圈故障频率
                95.3,   # 内圈故障频率  
                45.2,   # 滚动体故障频率
                15.8    # 保持架故障频率
            ]
            
            key_indices = []
            
            # 查找轴承特征频率附近的点
            for bearing_freq in bearing_frequencies:
                freq_range = 10  # Hz范围（轴承故障频带较宽）
                indices = np.where((freq_data >= bearing_freq - freq_range) & 
                                 (freq_data <= bearing_freq + freq_range))[0]
                if len(indices) > 0:
                    # 选择幅值最大的点
                    max_idx = indices[np.argmax([amplitude_data[i] for i in indices])]
                    key_indices.append(max_idx)
            
            # 查找高频共振频率（通常在1-10kHz范围）
            high_freq_indices = np.where((freq_data >= 1000) & (freq_data <= 10000))[0]
            if len(high_freq_indices) > 0:
                # 在高频范围内找几个峰值
                high_freq_amplitudes = [amplitude_data[i] for i in high_freq_indices]
                if len(high_freq_amplitudes) > 5:
                    # 找到前3个峰值
                    peaks, _ = signal.find_peaks(high_freq_amplitudes, height=np.max(high_freq_amplitudes) * 0.5)
                    for peak in peaks[:3]:
                        key_indices.append(high_freq_indices[peak])
            
            # 2. 对数采样其他频率点
            remaining_points = target_points - len(key_indices)
            if remaining_points > 0:
                # 排除已选择的关键频率点
                excluded_indices = set(key_indices)
                available_indices = [i for i in range(len(freq_data)) if i not in excluded_indices]
                
                if len(available_indices) > 0:
                    # 对数空间采样（低频密集，高频稀疏）
                    if len(available_indices) > remaining_points:
                        log_indices = np.logspace(0, np.log10(len(available_indices)), remaining_points, dtype=int) - 1
                        log_indices = np.clip(log_indices, 0, len(available_indices) - 1)
                        additional_indices = [available_indices[i] for i in log_indices]
                    else:
                        additional_indices = available_indices
                    
                    key_indices.extend(additional_indices)
            
            # 3. 排序并提取数据
            final_indices = sorted(list(set(key_indices)))[:target_points]
            
            sampled_freq = [freq_data[i] for i in final_indices]
            sampled_amplitude = [amplitude_data[i] for i in final_indices]
            
            return sampled_freq, sampled_amplitude
            
        except Exception as e:
            logger.warning(f"智能轴承频谱采样失败，使用均匀采样: {e}")
            # 降级到均匀采样
            indices = np.linspace(0, len(freq_data) - 1, target_points, dtype=int)
            return [freq_data[i] for i in indices], [amplitude_data[i] for i in indices]
    
    def format_vibration_for_chartjs(self, time_data, vibration_data):
        """将振动数据格式化为Chart.js格式"""
        # 格式化时间标签
        formatted_time = []
        for t in time_data:
            if isinstance(t, (int, float)):
                # 如果是数值，转换为时间格式
                current_time = datetime.now()
                time_str = current_time.strftime("%H:%M:%S")
                formatted_time.append(time_str)
            else:
                # 如果已经是时间格式，直接使用
                formatted_time.append(str(t))
        
        return {
            "labels": formatted_time,
            "datasets": [
                {
                    "label": "振动信号",
                    "data": [round(float(val), 4) for val in vibration_data],
                    "borderColor": "#409EFF",
                    "borderWidth": 1,
                    "pointRadius": 0,
                    "fill": False,
                    "tension": 0.1
                }
            ]
        }
    
    def format_bearing_spectrum_for_chartjs(self, freq_data, amplitude_data):
        """将轴承频谱数据格式化为Chart.js格式"""
        return {
            "labels": [round(float(f), 1) for f in freq_data],
            "datasets": [
                {
                    "label": "振动频谱",
                    "data": [round(float(val), 6) for val in amplitude_data],
                    "borderColor": "#409EFF",
                    "borderWidth": 1,
                    "pointRadius": 0,
                    "fill": False
                }
            ]
        }

    def analyze(self, data_batch):
        """分析数据批次，检测轴承故障"""
        try:
            # 提取数据
            if 'data' in data_batch:
                df = pd.DataFrame(data_batch['data'])
            else:
                logger.error("数据格式错误，缺少'data'字段")
                return None
            
            # 检查必要的列是否存在 - 支持多种振动列名
            required_columns = ['vibration'] # 原始期望的列名
            vibration_columns = ['vibration_x', 'vibration_y', 'vibration', '振动_X', '振动_Y', '振动_Z'] # 支持的振动列名
            
            # 查找可用的振动列
            available_vibration_cols = [col for col in vibration_columns if col in df.columns]
            
            if not available_vibration_cols:
                logger.error(f"数据缺少必要的振动列，支持的列名: {vibration_columns}")
                return None
            
            # 使用第一个可用的振动列，优先使用vibration_x
            vibration_col = available_vibration_cols[0]
            if 'vibration_x' in available_vibration_cols:
                vibration_col = 'vibration_x'
            
            logger.info(f"使用振动数据列: {vibration_col}")
            
            # 提取振动数据
            vibration_data = df[vibration_col].values
            
            if len(vibration_data) == 0:
                logger.warning("振动数据为空，无法进行分析。")
                return None

            # 特征1: 峭度 (Kurtosis)
            # 峭度用于衡量信号的尖锐程度，早期故障时会升高
            try:
                kurtosis = stats.kurtosis(vibration_data) # 默认使用fisher = True
                # 检查并处理NaN值
                if np.isnan(kurtosis) or np.isinf(kurtosis):
                    kurtosis = 3.0  # 正态分布的默认峭度值
                    logger.warning("峭度计算结果为NaN/Inf，使用默认值3.0")
            except Exception as e:
                kurtosis = 3.0
                logger.warning(f"峭度计算异常: {e}，使用默认值3.0")

            # 特征2: 波峰因数 (Crest Factor)
            # 波峰因数 = 峰值 / RMS值
            try:
                rms = np.sqrt(np.mean(vibration_data**2))
                peak_value = np.max(np.abs(vibration_data))
                crest_factor = peak_value / rms if rms > 0 else 1.0
                # 检查并处理NaN值
                if np.isnan(crest_factor) or np.isinf(crest_factor):
                    crest_factor = 1.0
                    logger.warning("波峰因数计算结果为NaN/Inf，使用默认值1.0")
            except Exception as e:
                crest_factor = 1.0
                logger.warning(f"波峰因数计算异常: {e}，使用默认值1.0")
            
            # 特征3: 轴承特征频率 (Bearing Characteristic Frequencies)
            # 实际需要根据轴承型号、转速等参数计算。这里返回一个模拟值。
            # 示例：假设一个典型的外圈故障频率
            bearing_characteristic_frequency = 120.5 # Hz (模拟值)

            # 计算综合故障评分
            # 峭度和波峰因数越大，故障分数越高
            # 对峭度进行归一化，假设正常值接近3（正态分布），故障时会显著升高
            try:
                normalized_kurtosis = max(0.0, (kurtosis - 3.0) / 10.0) # 模拟归一化到0-1范围
                normalized_crest_factor = max(0.0, (crest_factor - 3.0) / 5.0) # 模拟归一化
                
                # 确保归一化值不是NaN
                if np.isnan(normalized_kurtosis) or np.isinf(normalized_kurtosis):
                    normalized_kurtosis = 0.0
                if np.isnan(normalized_crest_factor) or np.isinf(normalized_crest_factor):
                    normalized_crest_factor = 0.0
                
                # 权重可以根据实际情况调整
                weights = {
                    'kurtosis': 0.5,
                    'crest_factor': 0.5,
                }
                
                fault_score = (weights['kurtosis'] * normalized_kurtosis + 
                              weights['crest_factor'] * normalized_crest_factor)
                
                # 确保故障评分不是NaN
                if np.isnan(fault_score) or np.isinf(fault_score):
                    fault_score = 0.0
                    logger.warning("故障评分计算结果为NaN/Inf，使用默认值0.0")
                    
            except Exception as e:
                fault_score = 0.0
                normalized_kurtosis = 0.0
                normalized_crest_factor = 0.0
                logger.warning(f"故障评分计算异常: {e}，使用默认值")
            
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
            
            # 准备诊断结论（可选传输）
            if status == "normal":
                diagnosis_conclusion = "电机轴承运行正常，未检测到故障特征。"
                suggestions = ["继续正常运行", "按计划进行润滑和检查"]
            elif status == "warning":
                diagnosis_conclusion = "检测到轻微轴承故障特征，建议密切监控或进一步检查。"
                suggestions = [
                    "增加振动监测频率",
                    "检查轴承润滑状况",
                    "进行冲击脉冲或包络解调分析"
                ]
            else:
                diagnosis_conclusion = "警告：检测到明显轴承故障特征，建议尽快检修或更换轴承。"
                suggestions = [
                    "立即安排轴承检修或更换",
                    "检查轴承游隙和安装情况",
                    "分析磨损颗粒，确认故障类型"
                ]
            
            # === 性能优化：智能采样到Chart.js格式 ===
            
            # 1. 时域振动数据智能采样
            time_data = df['时间'].tolist() if '时间' in df.columns else list(range(len(df)))
            
            sampled_time, sampled_vibration = self.intelligent_vibration_sampling(
                time_data, vibration_data.tolist(), self.chart_config["time_series_points"]
            )
            
            # 格式化为Chart.js格式
            chartjs_time_series = self.format_vibration_for_chartjs(sampled_time, sampled_vibration)
            
            # 2. 频域数据智能采样
            # 轴承故障通常需要更复杂的频域（如包络解调频谱）来诊断，这里简化。
            # 可以计算原始振动信号的FFT作为参考
            sampling_rate = data_batch.get('sampling_rate', 10000) # 默认为10kHz
            n = len(vibration_data)
            yf = np.fft.fft(vibration_data)
            xf = np.fft.fftfreq(n, 1 / sampling_rate)

            # 只取正频率部分
            positive_freq_indices = xf >= 0
            freq_data = xf[positive_freq_indices]
            amplitude_data = np.abs(yf[positive_freq_indices])
            
            sampled_freq, sampled_amplitude = self.intelligent_bearing_spectrum_sampling(
                freq_data.tolist(), amplitude_data.tolist(), self.chart_config["spectrum_points"]
            )
            
            # 格式化为Chart.js格式
            chartjs_spectrum = self.format_bearing_spectrum_for_chartjs(sampled_freq, sampled_amplitude)
            
            # 构建优化后的结果
            result = {
                "timestamp": datetime.now().isoformat(),
                "status": status,
                "score": float(fault_score),
                "features": {
                    "bearing_characteristic_frequency": float(bearing_characteristic_frequency) if not np.isnan(bearing_characteristic_frequency) else 120.5,
                    "crest_factor": float(crest_factor) if not np.isnan(crest_factor) else 1.0,
                    "kurtosis": float(kurtosis) if not np.isnan(kurtosis) else 3.0,
                    "fault_severity": float(severity) if not np.isnan(severity) else 0.0
                },
                
                # 直接可用的Chart.js格式数据
                "charts": {
                    "timeSeries": chartjs_time_series,
                    "spectrum": chartjs_spectrum
                },
                
                # 传统格式保留（向后兼容）
                "time_series": {
                    "time": sampled_time,
                    "values": sampled_vibration,
                },
                "frequency_spectrum": {
                    "frequency": sampled_freq,
                    "amplitude": sampled_amplitude
                },
                
                # 可选的详细信息
                "details": {
                    "includeConclusion": False,  # 默认不传输
                    "includeSuggestions": False  # 默认不传输
                }
            }
            
            # 可选传输诊断结论
            if result["details"]["includeConclusion"]:
                result["diagnosis_conclusion"] = diagnosis_conclusion
            if result["details"]["includeSuggestions"]:
                result["suggestions"] = suggestions
            
            logger.info(f"[性能优化] 轴承分析结果 - 状态: {status}, 评分: {fault_score:.2f}")
            logger.info(f"[性能优化] 数据点数: 时域{len(sampled_vibration)}点, 频域{len(sampled_amplitude)}点")
            logger.debug(f"特征详情: 峭度={kurtosis:.4f}, 波峰因数={crest_factor:.4f}, 特征频率={bearing_characteristic_frequency:.2f}Hz")
            
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
            required_columns = ['时间', 'vibration'] # 假设需要这些列
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