import numpy as np
import pandas as pd
from scipy import signal
from scipy.fft import fft, fftfreq
import logging
import math
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

def calculate_spectrum(data: np.ndarray, fs: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    计算信号的频谱
    :param data: 时域信号
    :param fs: 采样频率
    :return: 频率和幅值
    """
    n = len(data)
    # 应用汉宁窗减少频谱泄漏
    window = np.hanning(n)
    windowed_data = data * window
    
    # 计算FFT
    yf = fft(windowed_data)
    # 只取一半的频谱(由于共轭对称性)
    amplitude = 2.0/n * np.abs(yf[:n//2])
    xf = fftfreq(n, 1/fs)[:n//2]
    
    return xf, amplitude

def extract_current_features(current_data: np.ndarray, fs: float, f_supply: float, rpm: float) -> Dict[str, float]:
    """
    从电流信号中提取偏心故障特征
    :param current_data: 电流数据
    :param fs: 采样频率
    :param f_supply: 电源频率
    :param rpm: 电机转速(RPM)
    :return: 特征字典
    """
    # 转换转速为转子频率
    f_rotor = rpm / 60.0  # Hz
    
    # 计算频谱
    freq, amp = calculate_spectrum(current_data, fs)
    
    # 归一化频谱，使基波幅值为1
    f_supply_idx = np.argmin(np.abs(freq - f_supply))
    fundamental_amp = amp[f_supply_idx]
    normalized_amp = amp / fundamental_amp if fundamental_amp > 0 else amp
    
    # 特征字典
    features = {}
    
    # 查找特征频率分量 f_s ± k*f_r
    k_values = [1, 2, 3]  # 通常考虑k=1,2,3
    for k in k_values:
        # 侧边带频率
        f_ecc_lower = f_supply - k * f_rotor
        f_ecc_upper = f_supply + k * f_rotor
        
        # 查找最接近的频率点
        idx_lower = np.argmin(np.abs(freq - f_ecc_lower))
        idx_upper = np.argmin(np.abs(freq - f_ecc_upper))
        
        # 确保查找到的频率在合理范围内
        if abs(freq[idx_lower] - f_ecc_lower) > 0.5 or abs(freq[idx_upper] - f_ecc_upper) > 0.5:
            logger.warning(f"频率分辨率不足，无法准确定位k={k}的特征频率")
        
        # 记录特征频率的幅值
        features[f'lower_sideband_k{k}'] = normalized_amp[idx_lower]
        features[f'upper_sideband_k{k}'] = normalized_amp[idx_upper]
        features[f'sideband_avg_k{k}'] = (normalized_amp[idx_lower] + normalized_amp[idx_upper]) / 2
        features[f'sideband_diff_k{k}'] = abs(normalized_amp[idx_lower] - normalized_amp[idx_upper])
    
    # 计算偏心严重程度指标
    features['eccentricity_index'] = (features['sideband_avg_k1'] + 0.5*features['sideband_avg_k2'] + 0.25*features['sideband_avg_k3']) / 1.75
    
    # 计算静态/动态偏心比例指标
    # 通常静态偏心会导致上下边带不对称，而动态偏心更对称
    static_weight = np.mean([features[f'sideband_diff_k{k}'] for k in k_values])
    dynamic_weight = np.mean([features[f'sideband_avg_k{k}'] for k in k_values]) - static_weight
    total_weight = static_weight + dynamic_weight
    
    if total_weight > 0:
        features['static_ecc_ratio'] = static_weight / total_weight
        features['dynamic_ecc_ratio'] = dynamic_weight / total_weight
    else:
        features['static_ecc_ratio'] = 0
        features['dynamic_ecc_ratio'] = 0
    
    # 计算一些时域特征
    features['current_rms'] = np.sqrt(np.mean(current_data**2))
    features['current_peak'] = np.max(np.abs(current_data))
    features['current_crest_factor'] = features['current_peak'] / features['current_rms'] if features['current_rms'] > 0 else 0
    features['current_thd'] = calculate_thd(amp, f_supply_idx)
    
    return features

def calculate_thd(amp: np.ndarray, fundamental_idx: int, harmonics: int = 10) -> float:
    """
    计算总谐波畸变
    :param amp: 频谱幅值
    :param fundamental_idx: 基波索引
    :param harmonics: 要考虑的谐波数量
    :return: THD值
    """
    if fundamental_idx == 0:
        return 0
    
    fundamental = amp[fundamental_idx]
    if fundamental == 0:
        return 0
    
    # 计算谐波幅值的平方和
    harmonic_sum = 0
    for h in range(2, harmonics + 1):
        h_idx = fundamental_idx * h
        if h_idx < len(amp):
            harmonic_sum += amp[h_idx] ** 2
    
    return np.sqrt(harmonic_sum) / fundamental

def perform_envelope_analysis(current_data: np.ndarray, fs: float, f_supply: float) -> Dict[str, np.ndarray]:
    """
    执行包络分析，用于检测偏心故障
    :param current_data: 电流数据
    :param fs: 采样频率
    :param f_supply: 电源频率
    :return: 包络频谱
    """
    # 设计一个带通滤波器，中心在电源频率附近
    nyquist = fs / 2
    low = (f_supply - 10) / nyquist
    high = (f_supply + 10) / nyquist
    b, a = signal.butter(4, [low, high], btype='band')
    
    # 应用滤波器
    filtered_data = signal.filtfilt(b, a, current_data)
    
    # 计算希尔伯特变换得到包络
    analytic_signal = signal.hilbert(filtered_data)
    envelope = np.abs(analytic_signal)
    
    # 去除直流分量
    envelope = envelope - np.mean(envelope)
    
    # 计算包络谱
    env_freq, env_amp = calculate_spectrum(envelope, fs)
    
    return {'frequency': env_freq.tolist(), 'amplitude': env_amp.tolist()}

def detect_eccentricity_type(features: Dict[str, float]) -> Tuple[str, float]:
    """
    根据特征判断偏心类型
    :param features: 特征字典
    :return: 偏心类型和置信度
    """
    # 静态比例和动态比例
    static_ratio = features['static_ecc_ratio']
    dynamic_ratio = features['dynamic_ecc_ratio']
    
    # 偏心严重程度
    severity = features['eccentricity_index']
    
    if severity < 0.05:  # 阈值需要根据实际数据调整
        return "normal", 1.0 - severity * 10
    
    # 确定类型
    if static_ratio > 0.7:
        return "static", static_ratio
    elif dynamic_ratio > 0.7:
        return "dynamic", dynamic_ratio
    else:
        return "mixed", max(static_ratio, dynamic_ratio)

def analyze_eccentricity_health(df: pd.DataFrame) -> Dict[str, Any]:
    """
    分析电机的偏心健康状态
    :param df: 包含电机数据的DataFrame
    :return: 诊断结果
    """
    try:
        # 确定采样频率 (从时间戳推断)
        if 'timestamp' in df.columns and len(df) > 1:
            try:
                # 尝试将时间戳转换为时间差，计算平均采样周期
                if isinstance(df['timestamp'].iloc[0], str):
                    df['temp_time'] = pd.to_datetime(df['timestamp'])
                    time_diff = df['temp_time'].diff().dropna()
                    avg_period = time_diff.mean().total_seconds()
                    fs = 1.0 / avg_period if avg_period > 0 else 1000.0  # 默认1kHz
                else:
                    # 如果时间戳不是字符串，假设它是数字
                    time_diff = df['timestamp'].diff().dropna()
                    avg_period = time_diff.mean()
                    fs = 1.0 / avg_period if avg_period > 0 else 1000.0
            except Exception as e:
                logger.warning(f"从时间戳推断采样率失败: {str(e)}")
                fs = 1000.0  # 默认1kHz
        else:
            fs = 1000.0  # 默认采样率
        
        logger.info(f"采样频率: {fs} Hz")
        
        # 确定电源频率 (通常是50Hz或60Hz，可以从频谱中检测)
        # 这里暂时使用默认值，实际应用中应从频谱中检测
        f_supply = 50.0  # 默认50Hz (中国/欧洲标准)
        
        # 确定转速 (从数据中获取或估计)
        if 'Speed' in df.columns and not df['Speed'].isnull().all():
            rpm = df['Speed'].mean()
        elif 'rpm' in df.columns and not df['rpm'].isnull().all():
            rpm = df['rpm'].mean()
        else:
            # 假设是4极电机，从电源频率估计同步转速
            rpm = f_supply * 60 / 2  # 4极电机的同步转速
        
        logger.info(f"电机转速: {rpm} RPM")
        
        # 获取三相电流数据
        if all(col in df.columns for col in ['Ia', 'Ib', 'Ic']):
            current_a = df['Ia'].values
            current_b = df['Ib'].values
            current_c = df['Ic'].values
        else:
            # 尝试寻找替代列名
            current_columns = [col for col in df.columns if 'current' in col.lower() or 'ia' == col.lower() or 'ib' == col.lower() or 'ic' == col.lower()]
            if len(current_columns) >= 3:
                current_a = df[current_columns[0]].values
                current_b = df[current_columns[1]].values
                current_c = df[current_columns[2]].values
            elif len(current_columns) >= 1:
                # 至少有一相电流
                logger.warning("只找到一相电流数据，诊断可能不够准确")
                current_a = df[current_columns[0]].values
                current_b = current_a.copy()  # 简单复制作为替代
                current_c = current_a.copy()
            else:
                raise ValueError("无法找到电流数据列")
        
        # 检查数据质量
        if len(current_a) < 100:
            raise ValueError(f"数据点数不足: {len(current_a)} < 100")
        
        # 提取特征
        features_a = extract_current_features(current_a, fs, f_supply, rpm)
        features_b = extract_current_features(current_b, fs, f_supply, rpm)
        features_c = extract_current_features(current_c, fs, f_supply, rpm)
        
        # 综合三相特征 (取平均)
        features = {}
        for key in features_a.keys():
            features[key] = (features_a[key] + features_b[key] + features_c[key]) / 3
        
        # 执行包络分析 (主要使用A相)
        envelope_spectrum = perform_envelope_analysis(current_a, fs, f_supply)
        
        # 计算频谱
        freq_a, amp_a = calculate_spectrum(current_a, fs)
        
        # 制作时域数据示例 (采样100个点)
        time_step = 1/fs
        time_points = np.arange(min(100, len(current_a))) * time_step
        time_series_a = current_a[:min(100, len(current_a))]
        
        # 偏心类型检测
        ecc_type, confidence = detect_eccentricity_type(features)
        
        # 计算故障评分 (0-1之间，0表示健康，1表示严重故障)
        severity_score = min(1.0, features['eccentricity_index'] * 10)  # 乘以10是为了放大轻微偏心的影响
        
        # 确定状态
        if severity_score < 0.3:
            status = "normal"
        elif severity_score < 0.6:
            status = "warning"
        else:
            status = "fault"
        
        # 生成诊断结论
        conclusion = generate_diagnosis_conclusion(status, ecc_type, severity_score, features)
        
        # 生成建议措施
        suggestions = generate_suggestions(status, ecc_type, severity_score)
        
        # 准备返回结果
        result = {
            "status": status,
            "score": severity_score,
            "eccentricity_type": ecc_type,
            "confidence": confidence,
            "features": {
                "sideband_k1": features['sideband_avg_k1'],
                "sideband_k2": features['sideband_avg_k2'],
                "sideband_k3": features['sideband_avg_k3'],
                "eccentricity_index": features['eccentricity_index'],
                "static_ratio": features['static_ecc_ratio'],
                "dynamic_ratio": features['dynamic_ecc_ratio'],
                "current_rms": features['current_rms'],
                "current_thd": features['current_thd'],
                "power_supply": f_supply,
                "rpm": rpm
            },
            "time_series": {
                "time": time_points.tolist(),
                "values": time_series_a.tolist()
            },
            "frequency_spectrum": {
                "frequency": freq_a.tolist(),
                "amplitude": amp_a.tolist()
            },
            "envelope_spectrum": envelope_spectrum,
            "diagnosis_conclusion": conclusion,
            "suggestions": suggestions
        }
        
        return result
        
    except Exception as e:
        logger.exception(f"偏心故障诊断分析失败: {str(e)}")
        # 返回错误结果
        return {
            "status": "error",
            "score": 0.0,
            "eccentricity_type": "unknown",
            "confidence": 0.0,
            "features": {},
            "time_series": {"time": [], "values": []},
            "frequency_spectrum": {"frequency": [], "amplitude": []},
            "envelope_spectrum": {"frequency": [], "amplitude": []},
            "diagnosis_conclusion": f"诊断过程中发生错误: {str(e)}",
            "suggestions": ["请检查数据质量并重新尝试分析", "确保数据包含足够的电流样本", "验证电机参数是否正确"]
        }

def generate_diagnosis_conclusion(status: str, ecc_type: str, severity: float, features: Dict[str, float]) -> str:
    """
    生成诊断结论
    :param status: 状态 (normal, warning, fault)
    :param ecc_type: 偏心类型 (normal, static, dynamic, mixed)
    :param severity: 严重程度 (0-1)
    :param features: 特征字典
    :return: 诊断结论文本
    """
    if status == "normal":
        return "电机运行状态良好，未检测到明显的偏心故障特征。监测指标在正常范围内，电流频谱中的特征边带幅值较低。"
    
    severity_text = "轻微" if severity < 0.4 else ("中度" if severity < 0.7 else "严重")
    
    if ecc_type == "static":
        conclusion = f"电机存在{severity_text}静态偏心故障，特征指数为{severity:.2f}。静态偏心通常由定子和转子中心不同心引起，可能是由于安装不当、轴承座磨损或定子变形导致。"
        if features['static_ecc_ratio'] > 0.8:
            conclusion += f"静态偏心占比高达{features['static_ecc_ratio']:.2f}，几乎不存在动态偏心成分。"
    elif ecc_type == "dynamic":
        conclusion = f"电机存在{severity_text}动态偏心故障，特征指数为{severity:.2f}。动态偏心通常由转子旋转中心偏离几何中心引起，可能是转子弯曲、轴承磨损或转子动平衡问题导致。"
        if features['dynamic_ecc_ratio'] > 0.8:
            conclusion += f"动态偏心占比高达{features['dynamic_ecc_ratio']:.2f}，几乎不存在静态偏心成分。"
    else:  # mixed
        conclusion = f"电机存在{severity_text}混合偏心故障，特征指数为{severity:.2f}。检测到同时存在静态偏心({features['static_ecc_ratio']:.2f})和动态偏心({features['dynamic_ecc_ratio']:.2f})特征。"
        conclusion += "混合偏心通常表明机械问题较为复杂，可能同时存在多种故障原因。"
    
    if status == "warning":
        conclusion += "该级别的偏心可能导致轻微振动增加、效率下降和寿命缩短，建议在计划维护时关注。"
    elif status == "fault":
        conclusion += "该级别的偏心会显著增加电机振动、噪声，降低效率，并可能导致定子-转子摩擦或轴承加速损坏，应尽快安排检修。"
    
    return conclusion

def generate_suggestions(status: str, ecc_type: str, severity: float) -> List[str]:
    """
    生成建议措施
    :param status: 状态 (normal, warning, fault)
    :param ecc_type: 偏心类型 (normal, static, dynamic, mixed)
    :param severity: 严重程度 (0-1)
    :return: 建议措施列表
    """
    suggestions = []
    
    if status == "normal":
        suggestions = [
            "继续按照常规计划进行电机维护",
            "保持良好的运行环境，避免过热和过载",
            "定期进行状态监测，记录基准数据以便后续对比"
        ]
        return suggestions
    
    # 通用建议
    suggestions.append("增加状态监测频率，关注偏心特征指标变化趋势")
    
    if status == "warning":
        suggestions.append("在下次计划停机时检查电机")
        if ecc_type == "static":
            suggestions.extend([
                "检查电机安装情况，确认底座和法兰是否平整",
                "检查定子外壳是否变形或损坏",
                "验证端盖和轴承座的同心度",
                "考虑使用精密激光对中工具重新对中电机与负载"
            ])
        elif ecc_type == "dynamic":
            suggestions.extend([
                "检查转子是否弯曲或不平衡",
                "检查轴承内外圈磨损情况",
                "进行电机转子动平衡测试",
                "检查联轴器磨损情况和偏差"
            ])
        else:  # mixed
            suggestions.extend([
                "全面检查电机机械系统，包括轴承、定子和转子",
                "检查电机安装底座和联轴器",
                "测量轴线偏移和转子动平衡情况"
            ])
    
    elif status == "fault":
        suggestions.append("尽快安排停机检修")
        if severity > 0.8:
            suggestions.append("考虑准备备用电机，防止意外停机")
        
        if ecc_type == "static":
            suggestions.extend([
                "重新安装电机，确保完全对中",
                "更换可能变形的底座或法兰",
                "检查并修复定子铁芯变形问题",
                "使用激光对中工具进行精确对中"
            ])
        elif ecc_type == "dynamic":
            suggestions.extend([
                "更换磨损的轴承",
                "校正或更换弯曲的转轴",
                "重新平衡转子",
                "检查并修复可能的转子损伤"
            ])
        else:  # mixed
            suggestions.extend([
                "进行全面检修，可能需要拆解电机",
                "更换磨损部件，特别是轴承和联轴器",
                "重新对中并平衡电机系统",
                "考虑电机是否需要返厂维修或更换"
            ])
    
    return suggestions 