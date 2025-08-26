
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
logger = logging.getLogger("broken-bar-analyzer")

class BrokenBarAnalyzer:
    """断条故障分析器 - 性能优化版本"""
    
    def __init__(self):
        self.warning_threshold = 0.15  # 预警阈值，更新为更合理的值
        self.fault_threshold = 0.25    # 故障阈值，更新为更合理的值
        
        # 性能优化配置
        self.chart_config = {
            "time_series_points": 50,    # 时域图数据点数
            "spectrum_points": 30,       # 频谱图数据点数
            "feature_history_points": 10  # 特征历史点数
        }
    
    def intelligent_current_sampling(self, time_data, current_data, target_points=50):
        """智能电流数据采样 - 保留断条故障特征"""
        try:
            if len(time_data) <= target_points:
                return time_data, current_data
            
            # 1. 检测关键特征点（断条故障相关）
            key_indices = []
            
            # 检测调制幅值变化点（断条故障的典型特征）
            # 使用移动窗口计算电流包络
            window_size = max(20, len(current_data) // 10)
            envelope = []
            for i in range(len(current_data)):
                start_idx = max(0, i - window_size // 2)
                end_idx = min(len(current_data), i + window_size // 2)
                envelope.append(np.max(np.abs(current_data[start_idx:end_idx])))
            
            # 检测包络变化点
            envelope_diff = np.diff(envelope)
            significant_changes = np.where(np.abs(envelope_diff) > np.std(envelope_diff) * 1.5)[0]
            key_indices.extend(significant_changes.tolist())
            
            # 检测电流RMS值的周期性变化
            try:
                # 计算短时RMS
                rms_window = max(50, len(current_data) // 20)
                rms_values = []
                for i in range(0, len(current_data) - rms_window, rms_window // 2):
                    rms_val = np.sqrt(np.mean(current_data[i:i+rms_window]**2))
                    rms_values.append((i + rms_window // 2, rms_val))
                
                if len(rms_values) > 3:
                    # 找到RMS变化较大的点
                    rms_indices = [idx for idx, _ in rms_values]
                    rms_vals = [val for _, val in rms_values]
                    rms_std = np.std(rms_vals)
                    rms_mean = np.mean(rms_vals)
                    
                    for i, (idx, val) in enumerate(rms_values):
                        if abs(val - rms_mean) > rms_std * 0.8:
                            key_indices.append(idx)
            except Exception as e:
                logger.debug(f"RMS分析失败: {e}")
            
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
                # 优先保留特征变化点
                key_set = set(key_indices)
                priority_indices = [idx for idx in all_indices if idx in key_set]
                remaining_indices = [idx for idx in all_indices if idx not in key_set]
                
                final_indices = priority_indices[:target_points//2] + remaining_indices[:target_points-len(priority_indices[:target_points//2])]
                all_indices = sorted(final_indices)
            
            # 提取采样数据
            sampled_time = [time_data[i] for i in all_indices]
            sampled_current = [current_data[i] for i in all_indices]
            
            return sampled_time, sampled_current
            
        except Exception as e:
            logger.warning(f"智能电流采样失败，使用均匀采样: {e}")
            # 降级到均匀采样
            indices = np.linspace(0, len(time_data) - 1, target_points, dtype=int)
            return [time_data[i] for i in indices], [current_data[i] for i in indices]
    
    def intelligent_broken_bar_spectrum_sampling(self, freq_data, amplitude_data, target_points=30):
        """智能断条频谱采样 - 保留断条特征频率"""
        try:
            if len(freq_data) <= target_points:
                return freq_data, amplitude_data
            
            # 1. 断条故障特征频率
            fundamental_freq = 50.0
            slip = 0.02  # 典型滑差值
            
            # 断条故障的边频带：f_sb = f_s * (1 ± 2*k*s), k=1,2,3...
            sideband_frequencies = []
            for k in [1, 2, 3]:
                lower_sb = fundamental_freq * (1 - 2 * k * slip)
                upper_sb = fundamental_freq * (1 + 2 * k * slip)
                sideband_frequencies.extend([lower_sb, upper_sb])
            
            # 还要包含基频
            fault_frequencies = [fundamental_freq] + sideband_frequencies
            key_indices = []
            
            # 查找断条特征频率附近的点
            for fault_freq in fault_frequencies:
                freq_range = 2  # Hz范围（断条边频带相对较窄）
                indices = np.where((freq_data >= fault_freq - freq_range) & 
                                 (freq_data <= fault_freq + freq_range))[0]
                if len(indices) > 0:
                    # 选择幅值最大的点
                    max_idx = indices[np.argmax([amplitude_data[i] for i in indices])]
                    key_indices.append(max_idx)
            
            # 查找其他显著频率成分（峰值检测）
            try:
                # 找到频谱中的峰值
                peaks, properties = signal.find_peaks(amplitude_data, 
                                                    height=np.max(amplitude_data) * 0.1,
                                                    distance=len(amplitude_data) // 50)
                
                # 选择前5个最高的峰值
                if len(peaks) > 0:
                    peak_heights = [amplitude_data[p] for p in peaks]
                    sorted_peaks = sorted(zip(peaks, peak_heights), key=lambda x: x[1], reverse=True)
                    top_peaks = [p for p, _ in sorted_peaks[:5]]
                    key_indices.extend(top_peaks)
            except Exception as e:
                logger.debug(f"峰值检测失败: {e}")
            
            # 2. 对数采样其他频率点
            remaining_points = target_points - len(key_indices)
            if remaining_points > 0:
                # 排除已选择的关键频率点
                excluded_indices = set(key_indices)
                available_indices = [i for i in range(len(freq_data)) if i not in excluded_indices]
                
                if len(available_indices) > 0:
                    # 线性采样（断条分析主要关注低频部分）
                    if len(available_indices) > remaining_points:
                        step = len(available_indices) / remaining_points
                        linear_indices = [int(i * step) for i in range(remaining_points)]
                        additional_indices = [available_indices[min(i, len(available_indices)-1)] for i in linear_indices]
                    else:
                        additional_indices = available_indices
                    
                    key_indices.extend(additional_indices)
            
            # 3. 排序并提取数据
            final_indices = sorted(list(set(key_indices)))[:target_points]
            
            sampled_freq = [freq_data[i] for i in final_indices]
            sampled_amplitude = [amplitude_data[i] for i in final_indices]
            
            return sampled_freq, sampled_amplitude
            
        except Exception as e:
            logger.warning(f"智能断条频谱采样失败，使用均匀采样: {e}")
            # 降级到均匀采样
            indices = np.linspace(0, len(freq_data) - 1, target_points, dtype=int)
            return [freq_data[i] for i in indices], [amplitude_data[i] for i in indices]
    
    def format_current_for_chartjs(self, time_data, current_data):
        """将电流数据格式化为Chart.js格式"""
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
                    "label": "A相电流",
                    "data": [round(float(val), 3) for val in current_data],
                    "borderColor": "#409EFF",
                    "borderWidth": 1,
                    "pointRadius": 0,
                    "fill": False,
                    "tension": 0.2
                }
            ]
        }
    
    def format_broken_bar_spectrum_for_chartjs(self, freq_data, amplitude_data):
        """将断条频谱数据格式化为Chart.js格式"""
        return {
            "labels": [round(float(f), 1) for f in freq_data],
            "datasets": [
                {
                    "label": "电流频谱",
                    "data": [round(float(val), 6) for val in amplitude_data],
                    "borderColor": "#409EFF",
                    "borderWidth": 1,
                    "pointRadius": 0,
                    "fill": False
                }
            ]
        }
    
    def analyze(self, data_batch):
        """分析数据批次，检测断条故障"""
        try:
            # 提取电流数据
            if 'data' in data_batch:
                df = pd.DataFrame(data_batch['data'])
            else:
                logger.error("数据格式错误，缺少'data'字段")
                return None
            
            # 检查必要的列是否存在，断条故障通常分析单相或三相电流
            required_columns = ['Ia'] # 假设只需要Ia，如果需要三相，则改为['Ia', 'Ib', 'Ic']
            if not all(col in df.columns for col in required_columns):
                logger.error(f"数据缺少必要的电流列: {required_columns}")
                return None
            
            # 获取采样率
            sampling_rate = data_batch.get('sampling_rate', 10000) # 默认为10kHz
            
            # 提取A相电流
            ia = df['Ia'].values
            
            # 特征1: 计算边频带幅值比 (Sideband Ratio)
            # 这里需要更复杂的FFT分析来准确计算边频带。为简化，我们先模拟一些数据。
            # 实际应用中，需要根据电机参数和滑差s来计算边频带频率。
            # 假设基频为50Hz，滑差s为0.02 (2%)
            fundamental_freq = 50.0
            slip = 0.02 # 假设滑差

            # 计算频谱
            try:
                # 计算FFT
                n = len(ia)
                yf = np.fft.fft(ia)
                xf = np.fft.fftfreq(n, 1 / sampling_rate)
                
                # 只取正频率部分
                positive_indices = xf >= 0
                freqs = xf[positive_indices]
                spectrum = np.abs(yf[positive_indices])
                
                # 查找基频（50Hz左右）
                fundamental_range = (48, 52)
                fundamental_indices = np.where((freqs >= fundamental_range[0]) & 
                                             (freqs <= fundamental_range[1]))[0]
                
                if len(fundamental_indices) > 0:
                    fundamental_idx = fundamental_indices[np.argmax(spectrum[fundamental_indices])]
                    fundamental_amplitude = spectrum[fundamental_idx]
                    actual_fundamental_freq = freqs[fundamental_idx]
                    logger.debug(f"找到基频: {actual_fundamental_freq:.2f}Hz, 幅值: {fundamental_amplitude:.4f}")
                else:
                    logger.warning("未找到基频，使用默认值50Hz")
                    actual_fundamental_freq = 50.0
                    fundamental_amplitude = 1.0  # 默认值
                
                # 计算边频带（断条故障特征）
                # 左边频带: f_s * (1 - 2*s) 和右边频带: f_s * (1 + 2*s)
                left_sideband_freq = actual_fundamental_freq * (1 - 2 * slip)
                right_sideband_freq = actual_fundamental_freq * (1 + 2 * slip)
                
                # 查找边频带幅值
                def find_sideband_amplitude(target_freq, search_range=1.0):
                    indices = np.where((freqs >= target_freq - search_range) & 
                                     (freqs <= target_freq + search_range))[0]
                    if len(indices) > 0:
                        max_idx = indices[np.argmax(spectrum[indices])]
                        return spectrum[max_idx]
                    return 0.0
                
                left_sideband_amplitude = find_sideband_amplitude(left_sideband_freq)
                right_sideband_amplitude = find_sideband_amplitude(right_sideband_freq)
                
                # 计算边频带比值
                max_sideband_amplitude = max(left_sideband_amplitude, right_sideband_amplitude)
                if fundamental_amplitude > 0:
                    sideband_ratio = max_sideband_amplitude / fundamental_amplitude
                else:
                    sideband_ratio = 0.0
                
                logger.debug(f"边频带分析: 左边频带{left_sideband_freq:.2f}Hz={left_sideband_amplitude:.4f}, "
                           f"右边频带{right_sideband_freq:.2f}Hz={right_sideband_amplitude:.4f}, "
                           f"比值={sideband_ratio:.4f}")
                
            except Exception as e:
                logger.error(f"频谱分析失败: {e}")
                sideband_ratio = 0.0
                freqs = np.array([])
                spectrum = np.array([])
            
            # 特征2: 归一化故障指数
            # 这是一个综合指标，结合多个断条故障特征
            # 简化版本：基于边频带比值和电流不平衡
            try:
                # 计算电流的调制深度
                current_envelope = np.abs(signal.hilbert(ia - np.mean(ia)))
                modulation_depth = (np.max(current_envelope) - np.min(current_envelope)) / np.mean(current_envelope)
                
                # 归一化故障指数 = 边频带比值 * 调制深度权重
                normalized_fault_index = sideband_ratio * (1 + 0.3 * min(modulation_depth, 1.0))
                
            except Exception as e:
                logger.warning(f"调制深度计算失败: {e}")
                normalized_fault_index = sideband_ratio  # 降级到只使用边频带比值
            
            # 特征3: 估计断条数量
            # 基于故障严重程度的简单估算
            if normalized_fault_index < 0.05:
                broken_bar_count = 0
            elif normalized_fault_index < 0.15:
                broken_bar_count = 1
            elif normalized_fault_index < 0.25:
                broken_bar_count = 2
            else:
                broken_bar_count = min(3, int(normalized_fault_index * 10))  # 最多估算3根
            
            # 计算综合故障评分
            weights = {
                'sideband_ratio': 0.6,
                'normalized_fault_index': 0.4
            }
            
            fault_score = (weights['sideband_ratio'] * sideband_ratio + 
                          weights['normalized_fault_index'] * normalized_fault_index)
            
            # 确定状态
            if fault_score > self.fault_threshold:
                status = "fault"
            elif fault_score > self.warning_threshold:
                status = "warning"
            else:
                status = "normal"
            
            # 估计故障严重程度
            if fault_score > self.warning_threshold:
                severity = min(1.0, fault_score / (self.fault_threshold * 1.5))
            else:
                severity = 0.0
            
            # 准备诊断结论（可选传输）
            if status == "normal":
                diagnosis_conclusion = "电机运行正常，未检测到断条故障特征。"
                suggestions = ["继续正常运行", "按计划进行常规维护"]
            elif status == "warning":
                diagnosis_conclusion = f"检测到轻微断条故障特征，估计有{broken_bar_count}根导条存在问题。"
                suggestions = [
                    "增加电流监测频率",
                    "进行转子检查",
                    "分析电机启动电流特征"
                ]
            else:
                diagnosis_conclusion = f"警告：检测到明显断条故障，估计有{broken_bar_count}根导条断裂。"
                suggestions = [
                    "立即安排转子检修",
                    "更换断裂导条",
                    "检查转子平衡",
                    "分析故障原因，防止再次发生"
                ]
            
            # === 性能优化：智能采样到Chart.js格式 ===
            
            # 1. 时域电流数据智能采样
            time_data = df['时间'].tolist() if '时间' in df.columns else list(range(len(df)))
            
            sampled_time, sampled_current = self.intelligent_current_sampling(
                time_data, ia.tolist(), self.chart_config["time_series_points"]
            )
            
            # 格式化为Chart.js格式
            chartjs_time_series = self.format_current_for_chartjs(sampled_time, sampled_current)
            
            # 2. 频域数据智能采样
            if len(freqs) > 0 and len(spectrum) > 0:
                sampled_freq, sampled_spectrum = self.intelligent_broken_bar_spectrum_sampling(
                    freqs.tolist(), spectrum.tolist(), self.chart_config["spectrum_points"]
                )
                
                # 格式化为Chart.js格式
                chartjs_spectrum = self.format_broken_bar_spectrum_for_chartjs(sampled_freq, sampled_spectrum)
            else:
                # 空的频谱数据
                chartjs_spectrum = {
                    "labels": [],
                    "datasets": [{
                        "label": "电流频谱",
                        "data": [],
                        "borderColor": "#409EFF",
                        "borderWidth": 1,
                        "pointRadius": 0,
                        "fill": False
                    }]
                }
                sampled_freq = []
                sampled_spectrum = []
            
            # 构建优化后的结果
            result = {
                "timestamp": datetime.now().isoformat(),
                "status": status,
                "score": float(fault_score),
                "features": {
                    "sideband_ratio": float(sideband_ratio),
                    "normalized_fault_index": float(normalized_fault_index),
                    "broken_bar_count": int(broken_bar_count), # 整数类型
                    "fault_severity": float(severity)
                },
                
                # 直接可用的Chart.js格式数据
                "charts": {
                    "timeSeries": chartjs_time_series,
                    "spectrum": chartjs_spectrum
                },
                
                # 传统格式保留（向后兼容）
                "time_series": {
                    "time": sampled_time,
                    "values_a": sampled_current,
                    "values_b": [],  # 断条分析通常只用A相
                    "values_c": []
                },
                "frequency_spectrum": {
                    "frequency": sampled_freq,
                    "amplitude_a": sampled_spectrum,
                    "amplitude_b": [],
                    "amplitude_c": []
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
            
            logger.info(f"[性能优化] 断条分析结果 - 状态: {status}, 评分: {fault_score:.2f}")
            logger.info(f"[性能优化] 数据点数: 时域{len(sampled_current)}点, 频域{len(sampled_spectrum)}点")
            logger.debug(f"特征详情: 边频带比值={sideband_ratio:.4f}, 故障指数={normalized_fault_index:.4f}, 估计断条数={broken_bar_count}")
            
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
            required_columns = ['时间', 'Ia'] # 假设只需要Ia
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