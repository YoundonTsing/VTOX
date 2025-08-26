import pandas as pd
import numpy as np
from typing import Dict, Any
import logging
import math
from scipy import stats

logger = logging.getLogger(__name__)

# 诊断状态
class InsulationStatus:
    HEALTHY = "HEALTHY"
    DEGRADING = "DEGRADING"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

# 诊断阈值（可通过配置修改）
THRESHOLDS = {
    "degrading": 0.3,    # 绝缘劣化阈值
    "warning": 0.6,      # 绝缘警告阈值
    "critical": 0.7,     # 绝缘危险阈值
    "temp_ratio": 1.1,   # 温度比率阈值
    "temp_rise_rate": 2.0,  # 温升速率阈值(°C/min)
    "thermal_residual": 10.0,  # 温度残差阈值(°C)
    "efficiency_drop": -0.03  # 效率下降阈值(比例)
}

def analyze_insulation_health(df: pd.DataFrame) -> Dict[str, Any]:
    """
    分析电机绝缘健康状态
    :param df: 预处理后的数据
    :return: 诊断结果
    """
    try:
        logger.info(f"开始绝缘健康状态诊断，数据行数：{len(df)}")
        
        # 1. 提取特征
        features = extract_insulation_features(df)
        logger.debug(f"提取的绝缘特征：{features}")
        
        # 2. 计算特征评分
        feature_scores = calculate_feature_scores(features)
        logger.debug(f"特征评分：{feature_scores}")
        
        # 3. 计算综合故障评分
        score = calculate_health_score(feature_scores)
        logger.info(f"计算的绝缘健康评分：{score}")
        
        # 4. 确定诊断状态
        status = determine_status(score)
        logger.info(f"诊断状态：{status}")
        
        # 5. 构建返回结果
        result = {
            "score": score,
            "status": status,
            "features": features,
            "feature_scores": feature_scores
        }
        
        return result
        
    except Exception as e:
        logger.exception("绝缘健康状态诊断失败")
        raise

def extract_insulation_features(df: pd.DataFrame) -> Dict[str, float]:
    """提取绝缘健康状态特征"""
    features = {}
    
    try:
        # 确保数据帧不为空
        if df.empty:
            raise ValueError("输入数据为空")
        
        logger.info(f"开始提取绝缘特征，数据行数: {len(df)}")
        
        # 1. 温度相关特征
        # 1.1 绕组温度比率
        if 'T_winding' in df.columns and not df['T_winding'].isna().all():
            T_winding_avg = df['T_winding'].mean()
            # 假设额定温度为90°C
            T_rated = 90.0
            temp_ratio = T_winding_avg / T_rated
            logger.debug(f"绕组温度比率: {temp_ratio:.4f}")
        else:
            # 如果没有绕组温度数据，使用默认值
            temp_ratio = 0.9  # 默认值，表示正常
            logger.info("绕组温度数据缺失，使用默认温度比率: 0.9")
        
        # 1.2 温升速率
        if 'T_winding' in df.columns and len(df) > 5:
            # 假设数据是按时间顺序排列的，计算温度变化率
            # 如果有时间戳列，可以使用实际时间间隔
            if 'timestamp' in df.columns:
                df['time_diff'] = df['timestamp'].diff()
                df['temp_diff'] = df['T_winding'].diff()
                # 计算每分钟温升
                df['temp_rise_rate'] = df['temp_diff'] / df['time_diff'] * 60
                temp_rise_rate = df['temp_rise_rate'].mean()
            else:
                # 如果没有时间戳，假设采样间隔为1秒
                temp_diff = df['T_winding'].diff()
                temp_rise_rate = temp_diff.mean() * 60  # 转换为每分钟
            
            # 确保值有效
            if pd.isna(temp_rise_rate) or math.isinf(temp_rise_rate):
                temp_rise_rate = 0.5  # 默认值
            
            logger.debug(f"温升速率: {temp_rise_rate:.4f} °C/min")
        else:
            temp_rise_rate = 0.5  # 默认值
            logger.info("无法计算温升速率，使用默认值: 0.5 °C/min")
        
        # 1.3 温度模型残差
        # 简化的温度模型: T_model = k1 * I^2 + k2
        # 其中I是电流均方根值，k1和k2是系数
        if all(col in df.columns for col in ['Ia', 'Ib', 'Ic', 'T_winding']):
            # 计算电流均方根值
            I_rms = np.sqrt((df['Ia']**2 + df['Ib']**2 + df['Ic']**2) / 3).mean()
            
            # 简化模型系数（实际应基于历史数据校准）
            k1 = 0.5
            k2 = 40
            
            # 计算模型预测温度
            T_model = k1 * I_rms**2 + k2
            
            # 计算残差
            T_measured = df['T_winding'].mean()
            thermal_residual = T_measured - T_model
            
            logger.debug(f"温度模型残差: {thermal_residual:.4f} °C")
        else:
            thermal_residual = 2.0  # 默认值
            logger.info("无法计算温度模型残差，使用默认值: 2.0 °C")
        
        # 2. 效率相关特征
        # 2.1 效率残差
        try:
            if all(col in df.columns for col in ['Torque', 'Speed', 'Vdc', 'Ia', 'Ib', 'Ic']):
                # 计算机械功率
                mech_power = df['Torque'].abs() * df['Speed'].abs() * 2 * np.pi / 60
                
                # 计算电功率
                elec_power = (df['Ia']**2 + df['Ib']**2 + df['Ic']**2).mean() * df['Vdc'].mean()
                
                # 计算实际效率
                if elec_power > 0 and mech_power.mean() > 0:
                    eta_actual = mech_power.mean() / elec_power
                    eta_actual = max(0.5, min(eta_actual, 0.98))  # 限制在合理范围
                else:
                    eta_actual = 0.85  # 默认效率
                
                # 参考效率（可以从数据中获取或使用默认值）
                if 'Eta_ref' in df.columns and not pd.isna(df['Eta_ref']).all():
                    eta_ref = df['Eta_ref'].mean()
                else:
                    eta_ref = 0.93  # 默认参考效率
                
                efficiency_residual = eta_actual - eta_ref
                logger.debug(f"效率残差: {efficiency_residual:.4f}")
            else:
                efficiency_residual = -0.01  # 默认值
                logger.info("无法计算效率残差，使用默认值: -0.01")
        except Exception as e:
            logger.warning(f"计算效率残差时出错: {str(e)}")
            efficiency_residual = -0.01  # 默认值
        
        # 3. 电流残差趋势
        # 这里使用简化方法，实际应分析长期数据
        if 'Id_actual' in df.columns and 'Iq_actual' in df.columns:
            # 假设参考值为平均值
            Id_ref = df['Id_actual'].mean()
            Iq_ref = df['Iq_actual'].mean()
            
            # 计算残差
            delta_Id = df['Id_actual'] - Id_ref
            delta_Iq = df['Iq_actual'] - Iq_ref
            
            # 分析趋势（使用简单线性回归）
            x = np.arange(len(df))
            
            # Id趋势
            try:
                Id_slope, _, _, _, _ = stats.linregress(x, delta_Id)
            except:
                Id_slope = 0
                
            # Iq趋势
            try:
                Iq_slope, _, _, _, _ = stats.linregress(x, delta_Iq)
            except:
                Iq_slope = 0
            
            # 使用斜率的绝对值作为趋势指标
            current_residual_trend = max(abs(Id_slope), abs(Iq_slope)) * 1000
            logger.debug(f"电流残差趋势: {current_residual_trend:.6f}")
        else:
            current_residual_trend = 0.001  # 默认值
            logger.info("无法计算电流残差趋势，使用默认值: 0.001")
        
        # 4. 热老化累积
        # 简化计算，实际应基于长期温度数据
        if 'T_winding' in df.columns:
            T_ref = 90  # 参考温度
            k = 2  # 阿伦尼乌斯公式相关常数
            
            # 计算每个时间点的老化因子
            aging_factors = np.maximum(0, (df['T_winding'] - T_ref) ** k)
            
            # 假设每个数据点间隔为1分钟，转换为小时
            delta_t = 1/60
            
            # 累积老化
            thermal_aging = aging_factors.sum() * delta_t
            
            # 归一化到0-1000范围
            thermal_aging = min(1000, thermal_aging)
            logger.debug(f"热老化累积: {thermal_aging:.2f}")
        else:
            thermal_aging = 100  # 默认值
            logger.info("无法计算热老化累积，使用默认值: 100")
        
        # 存储特征
        features = {
            "temp_ratio": float(temp_ratio),
            "temp_rise_rate": float(temp_rise_rate),
            "thermal_residual": float(thermal_residual),
            "efficiency_residual": float(efficiency_residual),
            "current_residual_trend": float(current_residual_trend),
            "thermal_aging": float(thermal_aging)
        }
        
        logger.info(f"特征提取完成，特征数: {len(features)}")
        return features
    
    except Exception as e:
        logger.exception(f"特征提取失败: {str(e)}")
        
        # 返回默认特征值，避免整个过程崩溃
        default_features = {
            "temp_ratio": 0.9,
            "temp_rise_rate": 0.5,
            "thermal_residual": 2.0,
            "efficiency_residual": -0.01,
            "current_residual_trend": 0.001,
            "thermal_aging": 100
        }
        return default_features

def calculate_feature_scores(features: Dict[str, float]) -> Dict[str, float]:
    """计算各特征的异常得分"""
    try:
        # 温度比率得分
        temp_ratio_score = sigmoid((features["temp_ratio"] - THRESHOLDS["temp_ratio"]) * 10)
        
        # 温升速率得分
        temp_rise_rate_score = sigmoid((features["temp_rise_rate"] - THRESHOLDS["temp_rise_rate"]) * 2)
        
        # 温度模型残差得分
        thermal_residual_score = sigmoid((features["thermal_residual"] - THRESHOLDS["thermal_residual"]) * 0.5)
        
        # 效率残差得分 (负值表示效率下降)
        efficiency_residual_score = sigmoid((THRESHOLDS["efficiency_drop"] - features["efficiency_residual"]) * 30)
        
        # 电流残差趋势得分
        current_trend_score = sigmoid((features["current_residual_trend"] - 0.005) * 200)
        
        # 热老化累积得分
        thermal_aging_score = min(1.0, features["thermal_aging"] / 1000)
        
        return {
            "temp_ratio": float(temp_ratio_score),
            "temp_rise_rate": float(temp_rise_rate_score),
            "thermal_residual": float(thermal_residual_score),
            "efficiency_residual": float(efficiency_residual_score),
            "current_residual_trend": float(current_trend_score),
            "thermal_aging": float(thermal_aging_score)
        }
    
    except Exception as e:
        logger.exception(f"计算特征得分失败: {str(e)}")
        
        # 返回默认得分
        return {
            "temp_ratio": 0.2,
            "temp_rise_rate": 0.2,
            "thermal_residual": 0.2,
            "efficiency_residual": 0.2,
            "current_residual_trend": 0.2,
            "thermal_aging": 0.2
        }

def calculate_health_score(feature_scores: Dict[str, float]) -> float:
    """计算绝缘健康综合评分"""
    try:
        # 各特征权重
        weights = {
            "temp_ratio": 0.15,
            "temp_rise_rate": 0.20,
            "thermal_residual": 0.25,
            "efficiency_residual": 0.15,
            "current_residual_trend": 0.15,
            "thermal_aging": 0.10
        }
        
        # 加权计算总分
        total_score = 0
        total_weight = 0
        
        for key, score in feature_scores.items():
            if key in weights:
                total_score += score * weights[key]
                total_weight += weights[key]
        
        # 归一化得分
        health_score = total_score / total_weight if total_weight > 0 else 0.5
        
        # 确保分数在0-1范围内
        health_score = min(max(health_score, 0), 1)
        
        return float(health_score)
    
    except Exception as e:
        logger.exception("健康评分计算失败")
        return 0.5  # 返回中间值表示无法确定

def determine_status(score: float) -> str:
    """根据评分确定绝缘状态"""
    if score >= THRESHOLDS["critical"]:
        return InsulationStatus.CRITICAL
    elif score >= THRESHOLDS["warning"]:
        return InsulationStatus.WARNING
    elif score >= THRESHOLDS["degrading"]:
        return InsulationStatus.DEGRADING
    else:
        return InsulationStatus.HEALTHY

def sigmoid(x: float) -> float:
    """Sigmoid函数，将任意实数映射到0~1区间"""
    try:
        return 1 / (1 + np.exp(-x))
    except (OverflowError, ValueError):
        # 处理极端值
        return 0 if x < 0 else 1 