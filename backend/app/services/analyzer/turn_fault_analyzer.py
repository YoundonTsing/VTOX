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
logger = logging.getLogger("turn-fault-analyzer")

class TurnFaultAnalyzer:
    """匝间短路故障分析器 - 性能优化版本"""
    
    def __init__(self):
        self.warning_threshold = 0.15  # 预警阈值
        self.fault_threshold = 0.30    # 故障阈值
        
        # 性能优化配置
        self.chart_config = {
            "time_series_points": 50,    # 时域图数据点数
            "spectrum_points": 30,       # 频谱图数据点数
            "feature_history_points": 10  # 特征历史点数
        }
    
    def intelligent_time_series_sampling(self, time_data, current_data, target_points=50):
        """智能时域数据采样 - 保留关键特征"""
        try:
            if len(time_data) <= target_points:
                return time_data, current_data
            
            # 1. 检测关键特征点（峰值、零点等）
            key_indices = []
            
            # 检测峰值点
            peaks, _ = signal.find_peaks(np.abs(current_data), height=np.max(np.abs(current_data)) * 0.8)
            key_indices.extend(peaks)
            
            # 检测零点附近
            zero_crossings = np.where(np.diff(np.sign(current_data)))[0]
            key_indices.extend(zero_crossings)
            
            # 去重并排序
            key_indices = sorted(list(set(key_indices)))
            key_indices = [idx for idx in key_indices if 0 <= idx < len(time_data)]
            
            # 2. 计算需要的均匀采样点数
            uniform_points_needed = max(0, target_points - len(key_indices))
            
            # 3. 均匀采样
            if uniform_points_needed > 0:
                uniform_indices = np.linspace(0, len(time_data) - 1, uniform_points_needed, dtype=int)
                all_indices = sorted(list(set(key_indices + uniform_indices.tolist())))
            else:
                all_indices = key_indices[:target_points]
            
            # 4. 确保不超过目标点数
            if len(all_indices) > target_points:
                # 优先保留关键特征点
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
            logger.warning(f"智能采样失败，使用均匀采样: {e}")
            # 降级到均匀采样
            indices = np.linspace(0, len(time_data) - 1, target_points, dtype=int)
            return [time_data[i] for i in indices], [current_data[i] for i in indices]
    
    def intelligent_spectrum_sampling(self, freq_data, amplitude_data, target_points=30):
        """智能频谱采样 - 保留故障特征频率"""
        try:
            if len(freq_data) <= target_points:
                return freq_data, amplitude_data
            
            # 1. 故障特征频率（匝间短路相关）
            fault_frequencies = [50, 150, 250]  # 基频和三次、五次谐波
            key_indices = []
            
            # 查找故障特征频率附近的点
            for fault_freq in fault_frequencies:
                freq_range = 5  # Hz范围
                indices = np.where((freq_data >= fault_freq - freq_range) & 
                                 (freq_data <= fault_freq + freq_range))[0]
                if len(indices) > 0:
                    # 选择幅值最大的点
                    max_idx = indices[np.argmax([amplitude_data[i] for i in indices])]
                    key_indices.append(max_idx)
            
            # 2. 对数采样其他频率点
            remaining_points = target_points - len(key_indices)
            if remaining_points > 0:
                # 排除已选择的关键频率点
                excluded_indices = set(key_indices)
                available_indices = [i for i in range(len(freq_data)) if i not in excluded_indices]
                
                if len(available_indices) > 0:
                    # 对数空间采样
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
            logger.warning(f"智能频谱采样失败，使用均匀采样: {e}")
            # 降级到均匀采样
            indices = np.linspace(0, len(freq_data) - 1, target_points, dtype=int)
            return [freq_data[i] for i in indices], [amplitude_data[i] for i in indices]
    
    def format_time_series_for_chartjs(self, time_data, ia_data, ib_data, ic_data):
        """将时域数据格式化为Chart.js格式"""
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
                    "data": [round(float(val), 3) for val in ia_data],
                    "borderColor": "#409EFF",
                    "borderWidth": 1,
                    "pointRadius": 0,
                    "fill": False,
                    "tension": 0.2
                },
                {
                    "label": "B相电流", 
                    "data": [round(float(val), 3) for val in ib_data],
                    "borderColor": "#67C23A",
                    "borderWidth": 1,
                    "pointRadius": 0,
                    "fill": False,
                    "tension": 0.2
                },
                {
                    "label": "C相电流",
                    "data": [round(float(val), 3) for val in ic_data], 
                    "borderColor": "#E6A23C",
                    "borderWidth": 1,
                    "pointRadius": 0,
                    "fill": False,
                    "tension": 0.2
                }
            ]
        }
    
    def format_spectrum_for_chartjs(self, freq_data, amplitude_a, amplitude_b, amplitude_c):
        """将频谱数据格式化为Chart.js格式"""
        return {
            "labels": [round(float(f), 1) for f in freq_data],
            "datasets": [
                {
                    "label": "A相频谱",
                    "data": [round(float(val), 4) for val in amplitude_a],
                    "borderColor": "#409EFF",
                    "borderWidth": 1,
                    "pointRadius": 0,
                    "fill": False
                },
                {
                    "label": "B相频谱",
                    "data": [round(float(val), 4) for val in amplitude_b],
                    "borderColor": "#67C23A", 
                    "borderWidth": 1,
                    "pointRadius": 0,
                    "fill": False
                },
                {
                    "label": "C相频谱",
                    "data": [round(float(val), 4) for val in amplitude_c],
                    "borderColor": "#E6A23C",
                    "borderWidth": 1,
                    "pointRadius": 0,
                    "fill": False
                }
            ]
        }

    def analyze(self, data_batch):
        """分析数据批次，检测匝间短路故障"""
        try:
            # 提取电流数据
            if 'data' in data_batch:
                df = pd.DataFrame(data_batch['data'])
            else:
                logger.error("数据格式错误，缺少'data'字段")
                return None
            
            # 检查必要的列是否存在
            required_columns = ['Ia', 'Ib', 'Ic']
            if not all(col in df.columns for col in required_columns):
                logger.error(f"数据缺少必要的电流列: {required_columns}")
                return None
            
            # 获取采样率
            sampling_rate = data_batch.get('sampling_rate', 10000)
            
            # 提取三相电流
            ia = df['Ia'].values
            ib = df['Ib'].values
            ic = df['Ic'].values
            
            # 特征1: 计算电流不平衡度
            rms_a = np.sqrt(np.mean(ia**2))
            rms_b = np.sqrt(np.mean(ib**2))
            rms_c = np.sqrt(np.mean(ic**2))
            
            avg_rms = (rms_a + rms_b + rms_c) / 3
            max_deviation = max(abs(rms_a - avg_rms), abs(rms_b - avg_rms), abs(rms_c - avg_rms))
            
            # 防止除零错误
            if avg_rms > 1e-10:
                current_imbalance = max_deviation / avg_rms
            else:
                current_imbalance = 0.0
                logger.warning("电流RMS值过小，无法计算不平衡度")
                
            logger.debug(f"电流RMS值: A={rms_a:.3f}, B={rms_b:.3f}, C={rms_c:.3f}, 不平衡度={current_imbalance:.4f}")
            
            # 特征2: 计算三相电流的频谱
            data_length = len(ia)
            if data_length < 8:
                logger.error(f"数据长度过短({data_length})，无法进行频谱分析")
                return None
                
            # 根据数据长度调整FFT参数
            fft_size = min(8192, data_length)
            if fft_size < 64:  # 确保有足够的频率分辨率
                fft_size = min(64, data_length)
                logger.warning(f"数据长度较短({data_length})，调整FFT大小为{fft_size}")
            
            try:
                # A相频谱
                freq_a, spectrum_a = signal.welch(ia, fs=sampling_rate, nperseg=fft_size)
                # B相频谱
                freq_b, spectrum_b = signal.welch(ib, fs=sampling_rate, nperseg=fft_size)
                # C相频谱
                freq_c, spectrum_c = signal.welch(ic, fs=sampling_rate, nperseg=fft_size)
                
                logger.debug(f"频谱计算完成 - 数据长度:{data_length}, FFT大小:{fft_size}, 频率点数:{len(freq_a)}, 最大频率:{freq_a[-1]:.1f}Hz")
                
            except Exception as e:
                logger.error(f"频谱计算失败: {e}")
                return None
            
            # 查找基频位置
            fundamental_freq_range = (45, 65)
            fundamental_indices = np.where((freq_a >= fundamental_freq_range[0]) & 
                                          (freq_a <= fundamental_freq_range[1]))[0]
            
            if len(fundamental_indices) == 0:
                # 如果在标准范围内找不到基频，扩大搜索范围
                logger.warning(f"在标准基频范围({fundamental_freq_range[0]}-{fundamental_freq_range[1]}Hz)内未找到基频，扩大搜索范围")
                fundamental_freq_range = (40, 70)
                fundamental_indices = np.where((freq_a >= fundamental_freq_range[0]) & 
                                              (freq_a <= fundamental_freq_range[1]))[0]
                
                if len(fundamental_indices) == 0:
                    # 如果仍然找不到，使用整个频谱的前10%作为低频区域
                    max_search_idx = max(10, len(freq_a) // 10)  # 至少搜索前10个点
                    fundamental_indices = np.arange(1, min(max_search_idx, len(freq_a)))  # 跳过DC分量
                    logger.warning(f"扩大范围后仍未找到基频，使用前{len(fundamental_indices)}个频率点搜索")
            
            if len(fundamental_indices) > 0:
                fundamental_idx_a = fundamental_indices[np.argmax(spectrum_a[fundamental_indices])]
                fundamental_freq = freq_a[fundamental_idx_a]
                fundamental_amp_a = spectrum_a[fundamental_idx_a]
                fundamental_amp_b = spectrum_b[fundamental_idx_a]
                fundamental_amp_c = spectrum_c[fundamental_idx_a]
                logger.debug(f"找到基频: {fundamental_freq:.2f}Hz")
            else:
                # 极端情况：使用固定的基频值
                fundamental_freq = 50.0
                fundamental_idx_a = 1  # 使用第二个频率点（跳过DC）
                fundamental_amp_a = spectrum_a[fundamental_idx_a] if len(spectrum_a) > 1 else 1.0
                fundamental_amp_b = spectrum_b[fundamental_idx_a] if len(spectrum_b) > 1 else 1.0
                fundamental_amp_c = spectrum_c[fundamental_idx_a] if len(spectrum_c) > 1 else 1.0
                logger.error(f"无法找到合适的基频，使用默认值50Hz，幅值: A={fundamental_amp_a:.3f}")
            
            
            # 特征3: 计算三次谐波比例
            third_harmonic_freq = fundamental_freq * 3
            third_harmonic_range = (third_harmonic_freq - 5, third_harmonic_freq + 5)
            
            third_indices = np.where((freq_a >= third_harmonic_range[0]) & 
                                    (freq_a <= third_harmonic_range[1]))[0]
            
            if len(third_indices) > 0 and fundamental_amp_a > 0 and fundamental_amp_b > 0 and fundamental_amp_c > 0:
                third_idx_a = third_indices[np.argmax(spectrum_a[third_indices])]
                third_amp_a = spectrum_a[third_idx_a]
                third_amp_b = spectrum_b[third_idx_a]
                third_amp_c = spectrum_c[third_idx_a]
                
                # 安全的除法计算，避免除零错误
                third_harmonic_ratio_a = third_amp_a / max(fundamental_amp_a, 1e-10)
                third_harmonic_ratio_b = third_amp_b / max(fundamental_amp_b, 1e-10)
                third_harmonic_ratio_c = third_amp_c / max(fundamental_amp_c, 1e-10)
                
                # 取最大的三次谐波比例
                third_harmonic_ratio = max(third_harmonic_ratio_a, 
                                          third_harmonic_ratio_b, 
                                          third_harmonic_ratio_c)
                logger.debug(f"三次谐波比例: A={third_harmonic_ratio_a:.4f}, B={third_harmonic_ratio_b:.4f}, C={third_harmonic_ratio_c:.4f}")
            else:
                third_harmonic_ratio = 0.0
                if len(third_indices) == 0:
                    logger.debug(f"在三次谐波范围({third_harmonic_range[0]:.1f}-{third_harmonic_range[1]:.1f}Hz)内未找到频率点")
                else:
                    logger.debug("基波幅值过小，跳过三次谐波计算")
            
            # 特征4: 计算负序分量比例
            # 简化计算: 使用三相电流的不平衡作为负序分量的近似
            negative_sequence_ratio = current_imbalance
            
            # 计算综合故障评分
            # 权重可以根据实际情况调整
            weights = {
                'current_imbalance': 0.4,
                'third_harmonic_ratio': 0.3,
                'negative_sequence_ratio': 0.3
            }
            
            fault_score = (weights['current_imbalance'] * current_imbalance + 
                          weights['third_harmonic_ratio'] * third_harmonic_ratio + 
                          weights['negative_sequence_ratio'] * negative_sequence_ratio)
            
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
                diagnosis_conclusion = "电机运行正常，未检测到匝间短路故障特征。"
                suggestions = ["继续正常运行", "按计划进行常规维护"]
            elif status == "warning":
                diagnosis_conclusion = "检测到轻微匝间短路故障特征，建议密切监控。"
                suggestions = [
                    "增加监测频率",
                    "检查电机绝缘状况",
                    "准备备用电机"
                ]
            else:
                diagnosis_conclusion = "警告：检测到明显匝间短路故障特征，建议尽快检修电机。"
                suggestions = [
                    "安排电机检修",
                    "减少负载运行",
                    "准备更换电机",
                    "进行绝缘电阻测试确认故障"
                ]
            
            # === 性能优化：智能采样到Chart.js格式 ===
            
            # 1. 时域数据智能采样
            time_data = df['时间'].tolist() if '时间' in df.columns else list(range(len(df)))
            
            # 分别对三相电流进行智能采样
            sampled_time_a, sampled_ia = self.intelligent_time_series_sampling(
                time_data, ia.tolist(), self.chart_config["time_series_points"]
            )
            _, sampled_ib = self.intelligent_time_series_sampling(
                time_data, ib.tolist(), self.chart_config["time_series_points"]
            )
            _, sampled_ic = self.intelligent_time_series_sampling(
                time_data, ic.tolist(), self.chart_config["time_series_points"]
            )
            
            # 格式化为Chart.js格式
            chartjs_time_series = self.format_time_series_for_chartjs(
                sampled_time_a, sampled_ia, sampled_ib, sampled_ic
            )
            
            # 2. 频域数据智能采样
            sampled_freq_a, sampled_spectrum_a = self.intelligent_spectrum_sampling(
                freq_a.tolist(), spectrum_a.tolist(), self.chart_config["spectrum_points"]
            )
            _, sampled_spectrum_b = self.intelligent_spectrum_sampling(
                freq_b.tolist(), spectrum_b.tolist(), self.chart_config["spectrum_points"]
            )
            _, sampled_spectrum_c = self.intelligent_spectrum_sampling(
                freq_c.tolist(), spectrum_c.tolist(), self.chart_config["spectrum_points"]
            )
            
            # 格式化为Chart.js格式
            chartjs_spectrum = self.format_spectrum_for_chartjs(
                sampled_freq_a, sampled_spectrum_a, sampled_spectrum_b, sampled_spectrum_c
            )
            
            # 构建优化后的结果
            result = {
                "timestamp": datetime.now().isoformat(),
                "status": status,
                "score": float(fault_score),
                "features": {
                    "current_imbalance": float(current_imbalance),
                    "third_harmonic_ratio": float(third_harmonic_ratio),
                    "negative_sequence_ratio": float(negative_sequence_ratio),
                    "fault_severity": float(severity)
                },
                
                # 直接可用的Chart.js格式数据
                "charts": {
                    "timeSeries": chartjs_time_series,
                    "spectrum": chartjs_spectrum
                },
                
                # 传统格式保留（向后兼容）
                "time_series": {
                    "time": sampled_time_a,
                    "values_a": sampled_ia,
                    "values_b": sampled_ib,
                    "values_c": sampled_ic
                },
                "frequency_spectrum": {
                    "frequency": sampled_freq_a,
                    "amplitude_a": sampled_spectrum_a,
                    "amplitude_b": sampled_spectrum_b,
                    "amplitude_c": sampled_spectrum_c
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
            
            logger.info(f"[性能优化] 分析结果 - 状态: {status}, 评分: {fault_score:.2f}")
            logger.info(f"[性能优化] 数据点数: 时域{len(sampled_ia)}点, 频域{len(sampled_spectrum_a)}点")
            logger.debug(f"特征详情: 电流不平衡度={current_imbalance:.6f}, 三次谐波比例={third_harmonic_ratio:.6f}, 负序分量比例={negative_sequence_ratio:.6f}")
            
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