import numpy as np
import pandas as pd
from scipy import signal
import logging
from typing import Dict, List, Tuple, Any
import math

logger = logging.getLogger(__name__)

def calculate_time_domain_features(data: np.ndarray) -> Dict[str, float]:
    """
    计算时域特征参数
    :param data: 振动信号数据
    :return: 时域特征参数字典
    """
    # 去除平均值
    data_zero_mean = data - np.mean(data)
    
    # 基本统计量
    rms = np.sqrt(np.mean(np.square(data_zero_mean)))
    peak = np.max(np.abs(data_zero_mean))
    peak_to_peak = np.max(data_zero_mean) - np.min(data_zero_mean)
    crest_factor = peak / rms if rms > 0 else 0
    
    # 统计矩
    variance = np.var(data_zero_mean)
    skewness = np.mean(np.power(data_zero_mean / (np.sqrt(variance) if variance > 0 else 1), 3))
    kurtosis = np.mean(np.power(data_zero_mean / (np.sqrt(variance) if variance > 0 else 1), 4)) - 3
    
    # 波形因子和脉冲因子
    abs_mean = np.mean(np.abs(data_zero_mean))
    form_factor = rms / (abs_mean if abs_mean > 0 else 1)
    impulse_factor = peak / (abs_mean if abs_mean > 0 else 1)
    
    return {
        "rms": float(rms),
        "peak": float(peak),
        "peak_to_peak": float(peak_to_peak),
        "crest_factor": float(crest_factor),
        "variance": float(variance),
        "skewness": float(skewness),
        "kurtosis": float(kurtosis),
        "form_factor": float(form_factor),
        "impulse_factor": float(impulse_factor)
    }

def calculate_frequency_domain_features(data: np.ndarray, fs: float = 10000.0) -> Tuple[Dict[str, float], np.ndarray, np.ndarray]:
    """
    计算频域特征参数
    :param data: 振动信号数据
    :param fs: 采样频率
    :return: 频域特征参数字典，频率，幅值
    """
    # 计算FFT
    n = len(data)
    fft_data = np.fft.rfft(data * np.hanning(n)) / n
    freqs = np.fft.rfftfreq(n, d=1/fs)
    amplitude = 2 * np.abs(fft_data)  # 乘以2是为了获得单边频谱的正确幅值
    
    # 计算频域特征
    freq_mean = np.sum(freqs * amplitude) / np.sum(amplitude) if np.sum(amplitude) > 0 else 0
    freq_rms = np.sqrt(np.sum(np.power(amplitude, 2)))
    freq_kurtosis = np.sum(np.power(freqs - freq_mean, 4) * amplitude) / (np.sum(amplitude) * np.power(np.sqrt(np.sum(np.power(freqs - freq_mean, 2) * amplitude) / np.sum(amplitude)), 4)) if np.sum(amplitude) > 0 else 0
    
    # 能量分布
    freq_bands = [
        (0, 500),       # 低频带
        (500, 1000),    # 中低频带
        (1000, 2000),   # 中频带
        (2000, 3000),   # 中高频带
        (3000, fs/2)    # 高频带
    ]
    
    energy_bands = {}
    total_energy = np.sum(np.power(amplitude, 2))
    
    for i, (low, high) in enumerate(freq_bands):
        mask = (freqs >= low) & (freqs <= high)
        band_energy = np.sum(np.power(amplitude[mask], 2))
        energy_ratio = band_energy / total_energy if total_energy > 0 else 0
        energy_bands[f"energy_band_{i+1}"] = float(energy_ratio)
    
    features = {
        "freq_mean": float(freq_mean),
        "freq_rms": float(freq_rms),
        "freq_kurtosis": float(freq_kurtosis)
    }
    features.update(energy_bands)
    
    return features, freqs, amplitude

def calculate_envelope_spectrum(data: np.ndarray, fs: float = 10000.0) -> Tuple[np.ndarray, np.ndarray]:
    """
    计算包络谱
    :param data: 振动信号数据
    :param fs: 采样频率
    :return: 频率, 包络谱幅值
    """
    # 对信号进行带通滤波，截取轴承故障频率区域
    nyquist = fs / 2
    
    # 修正：确保滤波器频率在0到1之间
    # 如果采样频率过低，调整滤波器频率范围
    if nyquist < 5000:
        low = 0.1  # 使用归一化频率
        high = 0.45  # 使用归一化频率
    else:
        low = 1000 / nyquist  # 低频截止为1000Hz
        high = min(5000 / nyquist, 0.95)  # 高频截止为5000Hz，但不超过0.95
    
    # 确保频率在有效范围内
    if low >= high or low <= 0 or high >= 1:
        # 如果频率范围无效，使用安全的默认值
        low = 0.1
        high = 0.45
    
    b, a = signal.butter(4, [low, high], btype='band')
    filtered_data = signal.filtfilt(b, a, data)
    
    # 计算希尔伯特变换获取包络
    analytic_signal = signal.hilbert(filtered_data)
    envelope = np.abs(analytic_signal)
    
    # 对包络做FFT分析
    n = len(envelope)
    fft_data = np.fft.rfft(envelope * np.hanning(n)) / n
    freqs = np.fft.rfftfreq(n, d=1/fs)
    amplitude = 2 * np.abs(fft_data)
    
    # 只保留低频部分 (0-500Hz)
    max_freq = min(500, nyquist * 0.9)  # 不超过奈奎斯特频率的90%
    mask = freqs <= max_freq
    freqs = freqs[mask]
    amplitude = amplitude[mask]
    
    return freqs, amplitude

def detect_bearing_fault_frequencies(envelope_freqs: np.ndarray, envelope_amp: np.ndarray, rpm: float = None) -> Dict[str, float]:
    """
    在包络谱中检测轴承特征故障频率
    :param envelope_freqs: 包络谱频率
    :param envelope_amp: 包络谱幅值
    :param rpm: 电机转速(每分钟转数)
    :return: 故障类型概率字典
    """
    # 如果没有提供RPM，尝试从包络谱中估计基频
    if rpm is None:
        # 查找显著峰值
        peaks, _ = signal.find_peaks(envelope_amp, height=np.max(envelope_amp)*0.2)
        
        if len(peaks) > 0:
            # 根据峰值估计RPM (转化为Hz)
            peak_freqs = envelope_freqs[peaks]
            rpm = min(peak_freqs) * 60 if len(peak_freqs) > 0 else 1500  # 默认1500 RPM
        else:
            rpm = 1500  # 默认1500 RPM
    
    # 转化RPM为Hz
    shaft_freq = rpm / 60.0
    
    # 假设的轴承参数 (这里使用常见的比例关系，实际应根据具体轴承几何参数计算)
    # 这些是相对于轴转速的倍数
    bpfi = 4.7 * shaft_freq  # 内圈故障频率
    bpfo = 3.1 * shaft_freq  # 外圈故障频率
    bsf = 1.8 * shaft_freq   # 滚动体故障频率
    ftf = 0.4 * shaft_freq   # 保持架故障频率
    
    # 计算故障频率对应的峰值比例
    fault_freqs = {
        "inner_race": bpfi,
        "outer_race": bpfo,
        "ball": bsf,
        "cage": ftf
    }
    
    # 计算每种故障的能量
    fault_energies = {}
    total_energy = np.sum(envelope_amp)
    
    for fault_type, freq in fault_freqs.items():
        # 查找对应故障频率及其谐波附近的能量
        harmonics = [freq * i for i in range(1, 4)]  # 考虑1-3次谐波
        fault_energy = 0
        
        for harmonic in harmonics:
            # 在频率周围搜索峰值
            freq_range = 0.05 * harmonic  # 搜索范围为频率的±5%
            indices = np.where((envelope_freqs >= harmonic - freq_range) & 
                              (envelope_freqs <= harmonic + freq_range))[0]
            
            if len(indices) > 0:
                fault_energy += np.max(envelope_amp[indices])
        
        fault_energies[fault_type] = fault_energy / total_energy if total_energy > 0 else 0
    
    # 计算正常状态的概率 (能量更均匀分布)
    total_fault_energy = sum(fault_energies.values())
    normal_prob = 1.0 - min(1.0, total_fault_energy)
    
    # 将所有概率标准化为总和为1
    fault_probabilities = {k: v for k, v in fault_energies.items()}
    fault_probabilities["normal"] = normal_prob
    
    # 标准化概率
    total_prob = sum(fault_probabilities.values())
    if total_prob > 0:
        fault_probabilities = {k: v/total_prob for k, v in fault_probabilities.items()}
    
    return fault_probabilities

def analyze_bearing_health(df: pd.DataFrame) -> Dict[str, Any]:
    """
    分析轴承健康状态
    :param df: 包含振动数据的DataFrame
    :return: 诊断结果字典
    """
    try:
        # 确定振动数据列
        vibration_columns = [col for col in df.columns if any(s in col.lower() for s in ['vib', 'acc', 'accel'])]
        
        # 如果没有找到明确的振动列，尝试使用其他列
        if not vibration_columns:
            # 尝试使用电流列作为振动数据（电机电流也可以反映轴承状态）
            current_columns = [col for col in df.columns if any(s in col.lower() for s in ['current', 'ia', 'ib', 'ic'])]
            if current_columns:
                vibration_column = current_columns[0]
                logger.info(f"未找到振动数据列，使用电流列作为替代: {vibration_column}")
            # 如果仍然没有找到合适的列，使用第二列（假设第一列是时间）
            elif len(df.columns) > 1:
                vibration_column = df.columns[1]
                logger.info(f"未找到振动或电流数据列，使用第二列: {vibration_column}")
            else:
                raise ValueError("无法确定哪一列是振动数据")
        else:
            vibration_column = vibration_columns[0]
            logger.info(f"使用振动数据列: {vibration_column}")
        
        # 提取振动数据
        vibration_data = df[vibration_column].values
        
        # 确保振动数据是数值类型
        try:
            vibration_data = vibration_data.astype(float)
        except ValueError:
            logger.warning(f"振动数据转换为数值类型失败，尝试替代方法")
            # 尝试逐个转换
            numeric_data = []
            for val in vibration_data:
                try:
                    numeric_data.append(float(val))
                except (ValueError, TypeError):
                    numeric_data.append(0.0)
            vibration_data = np.array(numeric_data)
        
        # 确定采样频率 (从时间列估计或使用默认值)
        fs = 10000.0  # 默认10kHz
        time_columns = [col for col in df.columns if any(s in col.lower() for s in ['time', '时间', 'timestamp'])]
        if time_columns:
            time_col = time_columns[0]
            
            # 确保时间列是数值类型
            try:
                # 尝试将时间列转换为数值类型
                time_values = pd.to_numeric(df[time_col], errors='coerce')
                # 去除NaN值
                time_values = time_values.dropna()
                
                if len(time_values) > 1:
                    # 计算时间差
                    time_diff = np.diff(time_values.values)
                    avg_diff = np.mean(time_diff)
                    if avg_diff > 0:
                        fs = 1.0 / avg_diff
                        logger.info(f"从时间列估计采样频率: {fs:.2f} Hz")
            except Exception as e:
                logger.warning(f"时间列转换为数值类型失败: {str(e)}，使用默认采样频率")
        
        # 如果采样频率太低，可能导致分析不准确，给出警告
        if fs < 1000:
            logger.warning(f"采样频率较低 ({fs:.2f} Hz)，可能影响分析精度")
        
        # 提取转速 (如果有)
        rpm = None
        rpm_columns = [col for col in df.columns if any(s in col.lower() for s in ['rpm', 'speed', '转速'])]
        if rpm_columns:
            rpm_col = rpm_columns[0]
            try:
                rpm_values = pd.to_numeric(df[rpm_col], errors='coerce')
                rpm = np.mean(rpm_values.dropna())
                logger.info(f"检测到转速数据: {rpm:.2f} RPM")
            except Exception as e:
                logger.warning(f"转速数据处理失败: {str(e)}，使用默认值")
                rpm = 1500.0
        
        # 计算时域特征
        time_features = calculate_time_domain_features(vibration_data)
        
        # 计算频域特征和频谱
        freq_features, freqs, amplitude = calculate_frequency_domain_features(vibration_data, fs)
        
        try:
            # 尝试计算包络谱
            envelope_freqs, envelope_amp = calculate_envelope_spectrum(vibration_data, fs)
        except Exception as e:
            # 如果包络谱计算失败，使用空数组代替
            logger.warning(f"计算包络谱失败: {str(e)}，将使用空数组")
            envelope_freqs = np.array([0])
            envelope_amp = np.array([0])
        
        # 检测故障频率
        fault_probabilities = detect_bearing_fault_frequencies(envelope_freqs, envelope_amp, rpm)
        
        # 合并所有特征
        features = {**time_features, **freq_features}
        
        # 增加故障概率特征
        features.update({f"{k}_prob": v for k, v in fault_probabilities.items()})
        
        # 确定故障类型和状态
        fault_type = max(fault_probabilities.items(), key=lambda x: x[1] if x[0] != 'normal' else 0)[0]
        if fault_type == 'normal':
            fault_type = None
        
        # 计算故障评分 (0-1, 越高表示故障越严重)
        normal_prob = fault_probabilities.get('normal', 0)
        score = 1.0 - normal_prob
        
        # 确定状态
        status = "normal"
        if score >= 0.75:
            status = "fault"
        elif score >= 0.5:
            status = "warning"
        
        # 生成诊断结论
        diagnosis_conclusion = generate_diagnosis_conclusion(status, fault_type, features, fault_probabilities)
        
        # 生成建议
        suggestions = generate_suggestions(status, fault_type)
        
        # 整理返回结果
        time_indices = list(range(len(vibration_data)))
        time_values = [i / fs for i in time_indices]
        
        # 限制数据点数量，避免返回太多点
        max_points = 1000
        if len(time_values) > max_points:
            step = len(time_values) // max_points
            time_values = time_values[::step]
            vibration_data = vibration_data[::step]
        
        if len(freqs) > max_points:
            step = len(freqs) // max_points
            freqs = freqs[::step]
            amplitude = amplitude[::step]
        
        if len(envelope_freqs) > max_points:
            step = len(envelope_freqs) // max_points
            envelope_freqs = envelope_freqs[::step]
            envelope_amp = envelope_amp[::step]
        
        return {
            "status": status,
            "score": float(score),
            "fault_type": fault_type,
            "fault_probabilities": {k: float(v) for k, v in fault_probabilities.items()},
            "features": {k: float(v) if isinstance(v, (int, float, np.number)) else v for k, v in features.items()},
            "time_series": {
                "time": [float(t) for t in time_values],
                "values": [float(v) for v in vibration_data]
            },
            "frequency_spectrum": {
                "frequency": [float(f) for f in freqs],
                "amplitude": [float(a) for a in amplitude]
            },
            "envelope_spectrum": {
                "frequency": [float(f) for f in envelope_freqs],
                "amplitude": [float(a) for a in envelope_amp]
            },
            "diagnosis_conclusion": diagnosis_conclusion,
            "suggestions": suggestions
        }
        
    except Exception as e:
        logger.exception(f"轴承健康状态分析错误: {str(e)}")
        raise ValueError(f"轴承诊断过程中出错: {str(e)}")

def generate_diagnosis_conclusion(status: str, fault_type: str, features: Dict[str, float], 
                                fault_probabilities: Dict[str, float]) -> str:
    """
    生成诊断结论
    :param status: 诊断状态
    :param fault_type: 故障类型
    :param features: 特征参数
    :param fault_probabilities: 故障概率
    :return: 诊断结论文本
    """
    if status == "normal":
        return "轴承运行状态正常，未检测到显著的故障特征。各项振动指标在合理范围内，建议继续定期监测。"
    
    conclusion = ""
    
    if status == "warning":
        conclusion = "轴承运行状态异常，检测到轻微故障迹象。"
    elif status == "fault":
        conclusion = "轴承运行状态严重异常，检测到明显故障特征。"
    
    # 添加故障类型描述
    if fault_type == "inner_race":
        conclusion += f"内圈故障概率为{fault_probabilities.get('inner_race', 0)*100:.1f}%，表现为内圈特征频率({features.get('freq_mean', 0):.1f}Hz)及其谐波在振动谱中显著。"
        conclusion += f"峭度值{features.get('kurtosis', 0):.2f}高于正常水平，表明存在冲击成分，这是内圈损伤的典型特征。"
    
    elif fault_type == "outer_race":
        conclusion += f"外圈故障概率为{fault_probabilities.get('outer_race', 0)*100:.1f}%，表现为外圈特征频率及其谐波在振动谱中显著。"
        conclusion += f"RMS值{features.get('rms', 0):.2f}高于正常水平，表明整体振动能量增加，这通常与外圈损伤有关。"
    
    elif fault_type == "ball":
        conclusion += f"滚动体故障概率为{fault_probabilities.get('ball', 0)*100:.1f}%，表现为滚动体特征频率在包络谱中显著。"
        conclusion += f"峰值因子{features.get('crest_factor', 0):.2f}和脉冲因子{features.get('impulse_factor', 0):.2f}较高，表明存在间歇性冲击，这是滚动体损伤的典型特征。"
    
    elif fault_type == "cage":
        conclusion += f"保持架故障概率为{fault_probabilities.get('cage', 0)*100:.1f}%，表现为保持架特征频率及其调制边带在振动谱中显著。"
    
    # 添加严重程度描述
    if features.get('kurtosis', 0) > 5:
        conclusion += " 信号峭度值显著偏高，表明冲击成分明显，故障可能已经发展到中期阶段。"
    
    if features.get('rms', 0) > 2:
        conclusion += " 振动能量水平较高，表明故障已对轴承整体运行造成显著影响。"
    
    return conclusion

def generate_suggestions(status: str, fault_type: str) -> List[str]:
    """
    生成建议措施
    :param status: 诊断状态
    :param fault_type: 故障类型
    :return: 建议措施列表
    """
    suggestions = []
    
    if status == "normal":
        suggestions = [
            "继续按照常规维护计划进行定期检查",
            "保持良好的润滑状态，定期检查润滑油质量和油位",
            "记录轴承振动基线数据，用于未来对比分析",
            "确保电机运行环境清洁，避免灰尘和杂质进入轴承"
        ]
    elif status == "warning":
        suggestions = [
            "增加监测频率，建议每周进行一次振动测量",
            "检查轴承润滑情况，必要时添加或更换润滑油",
            "避免电机长时间满负荷运行，必要时减少负载",
            "计划在下一次设备停机时进行详细检查"
        ]
        
        if fault_type == "inner_race":
            suggestions.append("检查轴承是否存在安装不当导致的轴向预载过大问题")
            suggestions.append("评估轴承内圈与轴的配合情况，是否存在过盈量不当")
        elif fault_type == "outer_race":
            suggestions.append("检查轴承座是否有松动或变形")
            suggestions.append("评估轴承外圈与轴承座的配合情况")
        elif fault_type == "ball":
            suggestions.append("检查润滑油是否存在污染或金属颗粒")
            suggestions.append("考虑更换为更高等级的润滑油")
        elif fault_type == "cage":
            suggestions.append("检查轴承是否存在异常的轴向载荷")
            suggestions.append("避免频繁启停和负载变化")
    
    elif status == "fault":
        suggestions = [
            "尽快安排设备停机检修",
            "准备替换轴承，建议更换同型号或升级型号轴承",
            "在更换前检查电机轴和轴承座，确保无变形和损伤",
            "分析故障根因，防止类似故障再次发生"
        ]
        
        if fault_type == "inner_race":
            suggestions.append("检查轴是否存在弯曲或加工精度问题")
            suggestions.append("确保新轴承安装时轴向预载合适")
        elif fault_type == "outer_race":
            suggestions.append("检查轴承座是否有磨损、腐蚀或变形")
            suggestions.append("确保轴承座安装面的平面度和同轴度")
        elif fault_type == "ball":
            suggestions.append("检查是否存在过载或冲击载荷导致滚动体损伤")
            suggestions.append("考虑改进润滑系统，提高润滑效果")
        elif fault_type == "cage":
            suggestions.append("检查电机是否存在过大的轴向载荷")
            suggestions.append("考虑更换为更高质量的轴承，带有更坚固的保持架")
    
    return suggestions 