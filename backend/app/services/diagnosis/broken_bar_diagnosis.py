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

def extract_broken_bar_features(current_data: np.ndarray, fs: float, f_supply: float = None, rpm: float = None) -> Dict[str, float]:
    """
    从电流信号中提取断条故障特征
    :param current_data: 电流数据
    :param fs: 采样频率
    :param f_supply: 电源频率，如果未提供将从频谱中估计
    :param rpm: 电机转速(RPM)，如果未提供将从频谱中估计
    :return: 特征字典
    """
    # 计算频谱
    freq, amp = calculate_spectrum(current_data, fs)
    
    # 如果未提供电源频率，从频谱中估计
    if f_supply is None:
        # 查找30-70Hz范围内的最大峰值作为电源频率
        mask = (freq >= 30) & (freq <= 70)
        if np.any(mask):
            f_supply_idx = np.argmax(amp[mask]) + np.where(mask)[0][0]
            f_supply = freq[f_supply_idx]
        else:
            f_supply = 50.0  # 默认50Hz
    else:
        # 在频谱中找到最接近提供的电源频率的点
        f_supply_idx = np.argmin(np.abs(freq - f_supply))
    
    logger.info(f"电源频率: {f_supply} Hz")
    
    # 获取电源频率的幅值
    fundamental_amp = amp[f_supply_idx]
    
    # 如果未提供转速，尝试从频谱中估计
    if rpm is None:
        # 简单估计：假设2极对电机，转差率约为3-5%
        rpm = f_supply * 60 / 2 * 0.95  # 假设4%的转差率
    
    # 计算转差率
    slip = 1.0 - (rpm * 2) / (f_supply * 60)  # 假设2极对电机
    slip = max(0.001, min(0.2, slip))  # 限制在合理范围内
    
    logger.info(f"转速: {rpm} RPM, 转差率: {slip}")
    
    # 计算断条特征频率
    f_brokenbar_lower = f_supply * (1 - 2 * slip)
    f_brokenbar_upper = f_supply * (1 + 2 * slip)
    
    # 寻找特征频率附近的峰值
    # 确定搜索范围
    search_range = max(1.0, slip * f_supply)  # Hz
    
    # 搜索下边带
    lower_mask = (freq >= f_brokenbar_lower - search_range) & (freq <= f_brokenbar_lower + search_range)
    if np.any(lower_mask):
        lower_idx = np.argmax(amp[lower_mask]) + np.where(lower_mask)[0][0]
        lower_freq = freq[lower_idx]
        lower_amp = amp[lower_idx]
    else:
        lower_idx = np.argmin(np.abs(freq - f_brokenbar_lower))
        lower_freq = freq[lower_idx]
        lower_amp = amp[lower_idx]
    
    # 搜索上边带
    upper_mask = (freq >= f_brokenbar_upper - search_range) & (freq <= f_brokenbar_upper + search_range)
    if np.any(upper_mask):
        upper_idx = np.argmax(amp[upper_mask]) + np.where(upper_mask)[0][0]
        upper_freq = freq[upper_idx]
        upper_amp = amp[upper_idx]
    else:
        upper_idx = np.argmin(np.abs(freq - f_brokenbar_upper))
        upper_freq = freq[upper_idx]
        upper_amp = amp[upper_idx]
    
    # 计算特征指标
    sideband_ratio = (lower_amp + upper_amp) / (2 * fundamental_amp) if fundamental_amp > 0 else 0
    normalized_fault_index = (lower_amp + upper_amp) / fundamental_amp if fundamental_amp > 0 else 0
    
    # 估计断条数量 - 使用更保守和合理的模型
    # 经验公式：根据幅值比估计断条数量
    # 注意：这只是一个简化的估计，实际数量还受电机特性、负载等因素影响
    if sideband_ratio < 0.1:
        broken_bar_count = 0
    elif sideband_ratio < 0.2:
        broken_bar_count = 1
    elif sideband_ratio < 0.35:
        broken_bar_count = 2
    else:
        broken_bar_count = min(5, int(round(sideband_ratio * 10)))  # 更保守的估计，最多5条
    
    # 收集特征参数
    features = {
        "power_supply_freq": f_supply,
        "rotor_speed": rpm,
        "slip": slip,
        "left_sideband_freq": lower_freq,
        "right_sideband_freq": upper_freq,
        "left_sideband_amp": float(lower_amp),
        "right_sideband_amp": float(upper_amp),
        "fundamental_amp": float(fundamental_amp),
        "sideband_ratio": float(sideband_ratio),
        "normalized_fault_index": float(normalized_fault_index),
        "broken_bar_count": broken_bar_count
    }
    
    # 附加时域特征
    features["current_rms"] = np.sqrt(np.mean(current_data**2))
    features["current_peak"] = np.max(np.abs(current_data))
    features["current_crest_factor"] = features["current_peak"] / features["current_rms"] if features["current_rms"] > 0 else 0
    
    # 计算总谐波畸变率
    thd = calculate_thd(amp, f_supply_idx)
    features["current_thd"] = thd
    
    return features

def calculate_thd(amp: np.ndarray, fundamental_idx: int, harmonics: int = 10) -> float:
    """
    计算总谐波畸变
    :param amp: 频谱幅值
    :param fundamental_idx: 基波索引
    :param harmonics: 要考虑的谐波数量
    :return: THD值
    """
    if fundamental_idx == 0 or fundamental_idx >= len(amp):
        return 0
    
    fundamental = amp[fundamental_idx]
    if fundamental == 0:
        return 0
    
    # 计算谐波幅值的平方和
    harmonic_sum = 0
    for h in range(2, harmonics + 1):
        h_idx = h * fundamental_idx
        if h_idx < len(amp):
            harmonic_sum += amp[h_idx] ** 2
    
    return np.sqrt(harmonic_sum) / fundamental

def detect_slot_harmonics(freq: np.ndarray, amp: np.ndarray, f_supply: float, rpm: float, rotor_slots: int = 28) -> Dict[str, Dict[str, float]]:
    """
    检测转子槽谐波
    :param freq: 频率数组
    :param amp: 幅值数组
    :param f_supply: 电源频率
    :param rpm: 电机转速
    :param rotor_slots: 转子槽数
    :return: 转子槽谐波数据
    """
    # 计算转差率
    slip = 1.0 - (rpm * 2) / (f_supply * 60)  # 假设2极对电机
    
    # 主槽谐波频率
    # 槽谐波频率公式: f_slot = f_supply * ((rotor_slots/p)*(1-s) ± k)
    # 其中p是极对数，s是转差率，k通常为1
    poles = 2  # 假设2极对
    
    # 计算几个主要的槽谐波频率
    principal_slot_freq = f_supply * ((rotor_slots/poles)*(1-slip) + 1)
    upper_sideband_freq = principal_slot_freq + 2*f_supply
    lower_sideband_freq = principal_slot_freq - 2*f_supply
    first_slot_harmonic = f_supply * ((rotor_slots/poles)*(1-slip) - 1)
    second_slot_harmonic = f_supply * ((rotor_slots/poles)*(1-slip) - 3)
    
    # 查找这些频率在频谱中的幅值
    find_amplitude = lambda target_freq: amp[np.argmin(np.abs(freq - target_freq))]
    
    # 查找电源频率的幅值作为参考
    f_supply_amp = find_amplitude(f_supply)
    
    # 计算相对幅值
    get_relative_amp = lambda target_freq: find_amplitude(target_freq) / f_supply_amp if f_supply_amp > 0 else 0
    
    slot_harmonics = {
        "principal_slot_harmonic": {
            "frequency": float(principal_slot_freq),
            "amplitude": float(get_relative_amp(principal_slot_freq)),
            "phase": 0.0  # 相位信息需要更复杂的计算
        },
        "upper_sideband": {
            "frequency": float(upper_sideband_freq),
            "amplitude": float(get_relative_amp(upper_sideband_freq)),
            "phase": 0.0
        },
        "lower_sideband": {
            "frequency": float(lower_sideband_freq),
            "amplitude": float(get_relative_amp(lower_sideband_freq)),
            "phase": 0.0
        },
        "first_slot_harmonic": {
            "frequency": float(first_slot_harmonic),
            "amplitude": float(get_relative_amp(first_slot_harmonic)),
            "phase": 0.0
        },
        "second_slot_harmonic": {
            "frequency": float(second_slot_harmonic),
            "amplitude": float(get_relative_amp(second_slot_harmonic)),
            "phase": 0.0
        }
    }
    
    return slot_harmonics

def analyze_broken_bar_health(df: pd.DataFrame) -> Dict[str, Any]:
    """
    分析电机断条健康状态
    :param df: 包含电机数据的DataFrame
    :return: 诊断结果
    """
    try:
        # 确定采样频率
        if 'timestamp' in df.columns and len(df) > 1:
            try:
                # 尝试将时间戳转换为时间差，计算平均采样周期
                if isinstance(df['timestamp'].iloc[0], str):
                    df['temp_time'] = pd.to_datetime(df['timestamp'])
                    time_diff = df['temp_time'].diff().dropna()
                    avg_period = time_diff.mean().total_seconds()
                    fs = 1.0 / avg_period if avg_period > 0 else 10000.0  # 默认10kHz
                else:
                    # 如果时间戳不是字符串，假设它是数字
                    time_diff = df['timestamp'].diff().dropna()
                    avg_period = time_diff.mean()
                    fs = 1.0 / avg_period if avg_period > 0 else 10000.0
            except Exception as e:
                logger.warning(f"从时间戳推断采样率失败: {str(e)}")
                fs = 10000.0  # 默认10kHz
        else:
            fs = 10000.0  # 默认采样率
        
        logger.info(f"采样频率: {fs} Hz")
        
        # 确定电源频率和转速
        f_supply = None
        rpm = None
        
        # 如果数据中包含转速信息
        if 'Speed' in df.columns and not df['Speed'].isnull().all():
            rpm = df['Speed'].mean()
        elif 'rpm' in df.columns and not df['rpm'].isnull().all():
            rpm = df['rpm'].mean()
        
        # 获取电流数据
        current_data = None
        if 'current' in df.columns:
            current_data = df['current'].values
        elif 'Ia' in df.columns:
            current_data = df['Ia'].values
        elif any(col.lower() in ['ia', 'current_a', 'i_a'] for col in df.columns):
            current_col = next(col for col in df.columns if col.lower() in ['ia', 'current_a', 'i_a'])
            current_data = df[current_col].values
        else:
            # 尝试查找任何看起来像是电流的列
            current_columns = [col for col in df.columns if 'curr' in col.lower()]
            if current_columns:
                current_data = df[current_columns[0]].values
        
        if current_data is None:
            raise ValueError("无法在数据中找到电流列")
        
        # 预处理电流数据 - 移除直流偏置
        current_data = current_data - np.mean(current_data)
        
        # 提取断条故障特征
        features = extract_broken_bar_features(current_data, fs, f_supply, rpm)
        
        # 增加转子槽谐波分析
        freq, amp = calculate_spectrum(current_data, fs)
        slot_harmonics = detect_slot_harmonics(freq, amp, features['power_supply_freq'], features['rotor_speed'])
        features['slot_harmonics'] = slot_harmonics
        
        # 计算置信度 - 基于特征强度和信号质量
        confidence = min(1.0, max(0.5, 0.7 + 0.3 * (1 - features['current_thd'])))
        
        # 判断故障程度
        sideband_ratio = features['sideband_ratio']
        normalized_fault_index = features['normalized_fault_index']
        broken_bar_count = features['broken_bar_count']
        
        # 设置更合理的阈值，符合工程实践
        warning_threshold = 0.15  # 15% - 更符合实际工程经验
        fault_threshold = 0.25    # 25% - 避免误报
        
        # 决定故障状态
        if normalized_fault_index > fault_threshold or broken_bar_count >= 3:
            status = "fault"
            # 使用更温和的评分函数，避免过度敏感
            score = min(1.0, (normalized_fault_index - fault_threshold) / (0.5 - fault_threshold) + 0.5)
        elif normalized_fault_index > warning_threshold or broken_bar_count >= 2:
            status = "warning"
            # 预警状态的评分范围控制在0.3-0.7之间
            score = 0.3 + (normalized_fault_index - warning_threshold) / (fault_threshold - warning_threshold) * 0.4
        else:
            status = "normal"
            # 正常状态的评分控制在0-0.3之间
            score = min(0.3, normalized_fault_index / warning_threshold * 0.3)
        
        # 修正得分确保在0-1范围内
        score = min(1.0, max(0.0, score))
        
        # 生成诊断结论
        diagnosis_conclusion = generate_diagnosis_conclusion(status, features)
        
        # 生成建议措施
        suggestions = generate_suggestions(status, features)
        
        # 准备时域数据用于前端绘图
        time_step = 1/fs
        time_points = np.arange(min(500, len(current_data))) * time_step
        time_values = current_data[:min(500, len(current_data))]
        
        # 组装结果
        result = {
            "status": status,
            "score": score,
            "broken_bar_count": broken_bar_count,
            "confidence": confidence,
            "features": features,
            "time_series": {
                "time": time_points.tolist(),
                "values": time_values.tolist()
            },
            "frequency_spectrum": {
                "frequency": freq.tolist(),
                "amplitude": amp.tolist()
            },
            "diagnosis_conclusion": diagnosis_conclusion,
            "suggestions": suggestions
        }
        
        return result
        
    except Exception as e:
        logger.exception(f"断条故障诊断分析失败: {str(e)}")
        # 返回错误结果
        return {
            "status": "error",
            "score": 0.0,
            "broken_bar_count": 0,
            "confidence": 0.0,
            "features": {},
            "time_series": {"time": [], "values": []},
            "frequency_spectrum": {"frequency": [], "amplitude": []},
            "diagnosis_conclusion": f"诊断过程中发生错误: {str(e)}",
            "suggestions": ["请检查数据质量并重新尝试分析", "确保数据包含足够的电流样本", "验证电机参数是否正确"]
        }

def generate_diagnosis_conclusion(status: str, features: Dict[str, Any]) -> str:
    """
    生成诊断结论
    :param status: 状态
    :param features: 特征参数
    :return: 诊断结论文本
    """
    sideband_ratio = features['sideband_ratio']
    broken_bar_count = features['broken_bar_count']
    slip = features['slip']
    f_supply = features['power_supply_freq']
    
    if status == "normal":
        return f"电机转子状态良好，未检测到明显的断条故障特征。转子边带比例为{sideband_ratio:.4f}，低于预警阈值。转差率为{slip:.4f}，电源频率为{f_supply:.1f}Hz。"
    
    elif status == "warning":
        if broken_bar_count == 0:
            return f"电机转子存在轻微异常，转子边带比例为{sideband_ratio:.4f}，位于预警区间。可能是由于转子导条存在裂纹或高阻抗点，但尚未完全断裂。建议增加监测频率，关注异常发展趋势。"
        else:
            return f"电机转子存在异常，检测到可能的断条故障，估计有{broken_bar_count}个断裂导条。转子边带比例为{sideband_ratio:.4f}，转差率为{slip:.4f}。此状态下电机效率将降低，温度会升高，应尽快排查。"
    
    elif status == "fault":
        cause = "可能是由于转子铸铝过程中的缺陷、过热损伤、启动应力、金属疲劳或频繁的反向启动导致。"
        effect = "断条故障会导致转子磁场不平衡，产生转矩脉动、振动增加、温度升高和效率下降。严重时会导致断条数量增加，甚至可能导致定子绕组损坏。"
        
        return f"电机转子存在严重的断条故障，估计有{broken_bar_count}个断裂导条。转子边带比例达到{sideband_ratio:.4f}，远高于正常值。{cause}{effect}建议尽快安排维修或更换。"
    
    else:
        return f"诊断过程出现异常，无法确定电机状态。请检查数据质量并重新尝试。"

def generate_suggestions(status: str, features: Dict[str, Any]) -> List[str]:
    """
    生成建议措施
    :param status: 状态
    :param features: 特征参数
    :return: 建议措施列表
    """
    broken_bar_count = features['broken_bar_count']
    
    if status == "normal":
        return [
            "按照常规维护计划执行电机维护",
            "定期进行电机电流监测，建立基准数据",
            "确保电机正确的负载和冷却条件"
        ]
    
    elif status == "warning":
        suggestions = [
            "增加电机电流监测频率，每月至少一次",
            "在下次计划停机时检查电机转子状态",
            "监测电机温度和振动变化",
            "避免频繁启停和过载运行"
        ]
        
        if broken_bar_count > 0:
            suggestions.append(f"关注边带频率处({features['left_sideband_freq']:.1f}Hz和{features['right_sideband_freq']:.1f}Hz)的幅值变化趋势")
            suggestions.append("计划在未来3-6个月内更换或修复转子")
        
        return suggestions
    
    elif status == "fault":
        severe = broken_bar_count >= 3
        
        suggestions = [
            "安排电机检修或更换转子",
            "进行详细的电机状态评估，包括温度、振动和效率测试",
            "检查电机负载情况，避免过载运行",
            "分析导致断条的根本原因，防止新转子再次发生类似问题"
        ]
        
        if severe:
            suggestions.insert(0, "尽快停机并更换转子，持续运行可能导致更严重的损坏")
            suggestions.append("检查定子绕组是否受到二次损伤")
        else:
            suggestions.insert(0, "计划在短期内(1-3个月)更换或修复转子")
            suggestions.append("在更换前，减轻电机负载，避免突然启停")
        
        return suggestions
    
    else:
        return [
            "请检查数据质量并重新尝试分析",
            "确保电流传感器正确安装和校准",
            "验证电机参数是否正确"
        ] 