import numpy as np
from typing import Dict, Any
import logging
import math

logger = logging.getLogger(__name__)

# 配置参数权重 (后期可根据历史数据训练优化)
WEIGHTS = {
    "I2_avg": 0.25,            # 负序电流平均值
    "I2_I1_ratio": 0.15,       # 负序/正序比值
    "delta_I2_avg": 0.10,      # 负序电流残差平均值
    "unbalance_avg": 0.15,     # 电流不平衡度
    "kurtosis_delta_iq": 0.25, # ΔI_q峭度
    "delta_eta_avg": 0.10      # 效率残差平均值
}

# 各特征参数的参考阈值 (后期可根据历史数据优化)
REFERENCE_VALUES = {
    "I2_avg": 0.05,            # 标幺值，超过0.05认为异常
    "I2_I1_ratio": 0.02,       # 正常情况下<2%
    "delta_I2_avg": 0.01,      # 与参考值的偏差
    "unbalance_avg": 5.0,      # 5%的不平衡度为警戒值
    "kurtosis_delta_iq": 3.0,  # 峭度超过3表示异常尖峰
    "delta_eta_avg": -0.03     # 效率下降3%为警戒值
}

# 特征值缩放系数 (调整灵敏度)
SCALE_FACTORS = {
    "I2_avg": 10.0,
    "I2_I1_ratio": 50.0,
    "delta_I2_avg": 80.0,
    "unbalance_avg": 0.2,
    "kurtosis_delta_iq": 0.3,
    "delta_eta_avg": -25.0     # 负值表示越小(负)越异常
}


def sigmoid(x: float) -> float:
    """
    Sigmoid函数，将任意实数映射到0~1之间
    """
    try:
        return 1 / (1 + np.exp(-x))
    except (OverflowError, ValueError):
        # 处理极端值
        return 0.0 if x < -100 else 1.0 if x > 100 else 0.5


def calculate_feature_score(feature_name: str, value: float) -> float:
    """
    计算单个特征参数的异常得分
    
    参数:
        feature_name: 特征参数名称
        value: 特征参数值
    
    返回:
        归一化后的异常得分(0~1)
    """
    # 检查值是否有效
    if feature_name not in REFERENCE_VALUES or not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
        logger.warning(f"特征 {feature_name} 值无效: {value}，使用默认得分0.5")
        return 0.5
    
    # 获取参考阈值和缩放系数
    ref_value = REFERENCE_VALUES[feature_name]
    scale = SCALE_FACTORS.get(feature_name, 1.0)
    
    try:
        # 特殊处理负向指标 (如效率残差，越负表示越异常)
        if scale < 0:
            # 负向指标转换为正向评分
            score = sigmoid(scale * (value - ref_value))
        else:
            # 正向指标 (值越大越异常)
            score = sigmoid(scale * (value / max(ref_value, 0.001) - 1.0))
        
        # 确保得分在0-1范围内
        score = max(0.0, min(1.0, score))
        
        logger.debug(f"特征 {feature_name}={value:.4f}, 参考值={ref_value:.4f}, 得分={score:.4f}")
        return score
    
    except Exception as e:
        logger.warning(f"计算特征 {feature_name} 得分时出错: {str(e)}，使用默认得分0.5")
        return 0.5


def calculate_fault_score(features: Dict[str, float]) -> Dict[str, Any]:
    """
    计算综合故障评分和状态
    
    参数:
        features: 包含各特征参数的字典
    
    返回:
        包含故障评分和状态的字典
    """
    logger.info(f"计算故障评分的输入特征: {features}")
    
    # 检查并修复无效特征值
    sanitized_features = sanitize_features(features)
    
    # 计算各特征的异常得分
    feature_scores = {}
    for feature_name in WEIGHTS.keys():
        if feature_name in sanitized_features:
            feature_scores[feature_name] = calculate_feature_score(feature_name, sanitized_features[feature_name])
        else:
            logger.warning(f"缺少特征 {feature_name}，使用默认得分0.5")
            feature_scores[feature_name] = 0.5
    
    # 计算加权总分
    total_weight = sum(WEIGHTS.values())
    weighted_sum = sum(WEIGHTS[name] * feature_scores[name] for name in WEIGHTS.keys())
    fault_score = weighted_sum / total_weight if total_weight > 0 else 0.5
    
    # 限制在0~1范围内
    fault_score = min(max(fault_score, 0.0), 1.0)
    
    # 判断故障等级
    if fault_score < 0.3:
        status = "NORMAL"
    elif fault_score < 0.7:
        status = "WARNING"
    else:
        status = "FAULT"
    
    # 记录结果
    logger.info(f"故障评分计算结果: 得分={fault_score:.4f}, 状态={status}")
    logger.debug(f"各特征得分: {feature_scores}")
    
    # 返回结果
    return {
        "score": float(fault_score),
        "status": status,
        "feature_scores": feature_scores
    }


def sanitize_features(features: Dict[str, float]) -> Dict[str, float]:
    """
    检查并修复特征值中的无效数据
    """
    sanitized = {}
    
    # 默认值映射
    defaults = {
        "I2_avg": 0.02,
        "I2_max": 0.025,
        "I2_I1_ratio": 0.01,
        "unbalance_avg": 2.5,
        "unbalance_max": 3.5,
        "delta_I2_avg": 0.0,
        "delta_I2_std": 0.002,
        "kurtosis_delta_iq": 2.0,
        "delta_Iq_std": 0.05,
        "delta_eta_avg": -0.02,
        "delta_eta_std": 0.005
    }
    
    for key, value in features.items():
        if not isinstance(value, (int, float)) or math.isnan(value) or math.isinf(value):
            if key in defaults:
                sanitized[key] = defaults[key]
                logger.warning(f"特征 {key} 值无效: {value}，使用默认值: {defaults[key]}")
            else:
                sanitized[key] = 0.0
                logger.warning(f"特征 {key} 值无效: {value}，使用默认值: 0.0")
        else:
            sanitized[key] = value
    
    return sanitized 