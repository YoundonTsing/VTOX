import pandas as pd
import numpy as np
from typing import Dict, Any
import logging
import math

# 导入分析模块和数据模型
from ...analysis.feature_calculator import calculate_features
from ...analysis.fault_scorer import calculate_fault_score
from ...models.diagnosis_models import DiagnosisStatus, DiagnosisResult, Features

logger = logging.getLogger(__name__)

# 诊断阈值（可通过配置修改）
THRESHOLDS = {
    "warning": 0.3,
    "fault": 0.7,
    "I2_avg": 0.05,            # 负序电流平均值阈值
    "I2_I1_ratio": 0.02,       # 负序/正序比值阈值
    "unbalance_avg": 5.0,      # 电流不平衡度阈值(%)
    "kurtosis_delta_iq": 3.0,  # ΔI_q峭度阈值
    "delta_eta_avg": -0.03     # 效率残差平均值阈值
}

def analyze_turn_to_turn_fault(df: pd.DataFrame) -> Dict[str, Any]:
    """
    分析匝间短路故障
    :param df: 预处理后的数据
    :return: 诊断结果
    """
    try:
        logger.info(f"开始匝间短路故障诊断，数据行数：{len(df)}")
        
        # 1. 提取特征
        features = extract_features(df)
        logger.debug(f"提取的特征：{features}")
        
        # 2. 计算综合故障评分
        result = calculate_fault_score(features)
        logger.info(f"计算的故障评分：{result['score']}")
        
        # 3. 添加特征到结果中
        result["features"] = features
        
        return result
        
    except Exception as e:
        logger.exception("匝间短路故障诊断失败")
        raise

def extract_features(df: pd.DataFrame) -> Dict[str, float]:
    """提取匝间短路诊断特征"""
    try:
        # 确保数据帧不为空
        if df.empty:
            raise ValueError("输入数据为空")
        
        logger.info(f"开始提取特征，数据行数: {len(df)}")
        
        # 使用分析模块中的特征计算函数
        try:
            features = calculate_features(df)
            logger.info(f"特征提取完成，特征数: {len(features)}")
            return features
        except Exception as e:
            logger.error(f"使用特征计算器失败: {str(e)}")
            # 如果特征计算器失败，回退到原有的特征提取逻辑
            return _legacy_extract_features(df)
    
    except Exception as e:
        logger.exception(f"特征提取失败: {str(e)}")
        
        # 返回默认特征值，避免整个过程崩溃
        default_features = {
            "I2_avg": 0.02,
            "I2_max": 0.025,
            "I2_I1_ratio": 0.01,
            "unbalance_avg": 2.5,
            "unbalance_max": 3.5,
            "delta_I2_avg": 0.0,
            "delta_I2_std": 0.002,
            "kurtosis_delta_iq": 1.5,
            "delta_Iq_std": 0.05,
            "delta_eta_avg": -0.01,
            "delta_eta_std": 0.005
        }
        return default_features

def _legacy_extract_features(df: pd.DataFrame) -> Dict[str, float]:
    """原有的特征提取逻辑，作为备份"""
    # 1. 计算三相电流平均值
    ia_avg = df['Ia'].mean() if 'Ia' in df.columns else 0
    ib_avg = df['Ib'].mean() if 'Ib' in df.columns else 0
    ic_avg = df['Ic'].mean() if 'Ic' in df.columns else 0
    i_avg = (ia_avg + ib_avg + ic_avg) / 3 if ia_avg and ib_avg and ic_avg else 0
    
    logger.debug(f"三相电流平均值: A={ia_avg:.4f}, B={ib_avg:.4f}, C={ic_avg:.4f}")
    
    # 2. 计算正序分量和负序分量
    a = complex(-0.5, 0.866)  # 1∠120° = -0.5 + j0.866
    a2 = complex(-0.5, -0.866)  # 1∠240° = -0.5 - j0.866
    
    # 对每行计算正负序分量
    i_positive_sum = 0
    i_negative_sum = 0
    
    for _, row in df.iterrows():
        try:
            ia = float(row['Ia']) if 'Ia' in row and pd.notna(row['Ia']) else 0
            ib = float(row['Ib']) if 'Ib' in row and pd.notna(row['Ib']) else 0
            ic = float(row['Ic']) if 'Ic' in row and pd.notna(row['Ic']) else 0
            
            i_positive = (ia + a * ib + a2 * ic) / 3
            i_negative = (ia + a2 * ib + a * ic) / 3
            
            i_positive_sum += abs(i_positive)
            i_negative_sum += abs(i_negative)
        except (TypeError, ValueError) as e:
            logger.warning(f"计算正负序分量时出错: {str(e)}")
            # 跳过此行
            continue
    
    # 计算平均值
    row_count = len(df)
    i_positive_avg = i_positive_sum / row_count if row_count > 0 else 0
    i_negative_avg = i_negative_sum / row_count if row_count > 0 else 0
    
    logger.debug(f"正负序分量: 正序={i_positive_avg:.6f}, 负序={i_negative_avg:.6f}")
    
    # 3. 计算电流不平衡度
    unbalance_sum = 0
    valid_rows = 0
    
    for _, row in df.iterrows():
        try:
            ia = float(row['Ia']) if 'Ia' in row and pd.notna(row['Ia']) else 0
            ib = float(row['Ib']) if 'Ib' in row and pd.notna(row['Ib']) else 0
            ic = float(row['Ic']) if 'Ic' in row and pd.notna(row['Ic']) else 0
            
            i_max = max(ia, ib, ic)
            i_min = min(ia, ib, ic)
            i_avg_row = (ia + ib + ic) / 3 if (ia != 0 or ib != 0 or ic != 0) else 1
            
            unbalance = (i_max - i_min) / i_avg_row * 100 if i_avg_row > 0 else 0
            unbalance_sum += unbalance
            valid_rows += 1
        except (TypeError, ValueError) as e:
            logger.warning(f"计算电流不平衡度时出错: {str(e)}")
            # 跳过此行
            continue
    
    # 计算平均不平衡度
    unbalance_avg = unbalance_sum / valid_rows if valid_rows > 0 else 0
    
    logger.debug(f"电流不平衡度: {unbalance_avg:.2f}%")
    
    # 4. 计算DQ轴电流残差（如果有）
    try:
        if 'Iq_ref' in df.columns and 'Iq_actual' in df.columns:
            iq_ref_avg = df['Iq_ref'].mean()
            iq_actual_avg = df['Iq_actual'].mean()
            delta_iq_avg = iq_actual_avg - iq_ref_avg
            delta_iq_std = df['Iq_actual'].std()
        else:
            # 使用默认值
            delta_iq_avg = 0.1
            delta_iq_std = 0.05
            logger.info("DQ轴电流列不存在，使用默认残差值")
        
        if 'Id_actual' in df.columns:
            id_ref = 0  # 通常PMSM电机的id参考值为0
            id_actual_avg = df['Id_actual'].mean()
            delta_id_avg = id_actual_avg - id_ref
            delta_id_std = df['Id_actual'].std()
        else:
            # 使用默认值
            delta_id_avg = 0.05
            delta_id_std = 0.02
            logger.info("Id_actual列不存在，使用默认值")
    except Exception as e:
        logger.warning(f"计算DQ轴电流残差时出错: {str(e)}")
        delta_iq_avg = 0.1
        delta_iq_std = 0.05
        delta_id_avg = 0.05
        delta_id_std = 0.02
    
    # 5. 计算ΔI_q的峭度
    try:
        if 'Iq_actual' in df.columns and 'Iq_ref' in df.columns:
            delta_iq = df['Iq_actual'] - df['Iq_ref']
            
            # 检查数据点是否足够计算峭度
            if len(delta_iq) >= 4:  # 至少需要4个点才能计算峭度
                # 计算峭度 = [平均(x-μ)^4] / [平均(x-μ)^2]^2 - 3
                mean = delta_iq.mean()
                diff_squared = (delta_iq - mean) ** 2
                diff_fourth = (delta_iq - mean) ** 4
                
                variance_squared = (diff_squared.mean()) ** 2
                if variance_squared > 0:
                    kurtosis_delta_iq = diff_fourth.mean() / variance_squared - 3
                else:
                    kurtosis_delta_iq = 0
            else:
                kurtosis_delta_iq = 0
        else:
            # 对于没有q轴电流的数据，使用默认值
            kurtosis_delta_iq = 2.0
            logger.info("Iq列不存在，使用默认峭度值")
    except Exception as e:
        logger.warning(f"计算ΔI_q峭度时出错: {str(e)}")
        kurtosis_delta_iq = 2.0
    
    # 6. 计算效率残差（如果有）
    try:
        # 获取Eta_ref值（如果存在）或使用默认值
        if 'Eta_ref' in df.columns and not pd.isna(df['Eta_ref']).all():
            eta_ref_avg = df['Eta_ref'].mean()
        else:
            eta_ref_avg = 0.93  # 默认效率参考值
            logger.info("Eta_ref列不存在或为空，使用默认效率参考值0.93")
        
        # 如果有转矩和转速列，计算实际效率
        if 'Torque' in df.columns and 'Speed' in df.columns and 'Vdc' in df.columns:
            # 检查数据是否有效
            valid_torque = not pd.isna(df['Torque']).all()
            valid_speed = not pd.isna(df['Speed']).all()
            valid_vdc = not pd.isna(df['Vdc']).all()
            valid_current = not (pd.isna(df['Ia']).all() or pd.isna(df['Ib']).all() or pd.isna(df['Ic']).all())
            
            if valid_torque and valid_speed and valid_vdc and valid_current:
                # 计算机械功率 (W) = 转矩(Nm) * 转速(rad/s)
                # 将rpm转换为rad/s: ω(rad/s) = rpm * 2π/60
                mech_power = df['Torque'] * df['Speed'] * 2 * np.pi / 60
                
                # 计算电功率 (W) = 三相电流平方和的平均值 * 电压
                # 注意：这里假设电流单位是A，电压单位是V
                # 如果单位不同，需要进行转换
                elec_power = (df['Ia']**2 + df['Ib']**2 + df['Ic']**2).mean() * df['Vdc'].mean()
                
                if elec_power > 0:
                    eta_actual = abs(mech_power.mean()) / elec_power
                    # 限制效率在合理范围内 (0-1)
                    eta_actual = max(0, min(eta_actual, 0.99))
                    delta_eta_avg = eta_actual - eta_ref_avg
                    
                    logger.info(f"计算得到实际效率: {eta_actual:.4f}, 效率残差: {delta_eta_avg:.4f}")
                else:
                    delta_eta_avg = -0.02
                    logger.warning("电功率计算结果为零或负值，使用默认效率残差")
            else:
                delta_eta_avg = -0.02
                logger.info("转矩、转速或电压数据存在无效值，使用默认效率残差")
        else:
            # 使用默认值
            delta_eta_avg = -0.02
            logger.info("缺少计算实际效率所需的列，使用默认效率残差")
    except Exception as e:
        logger.exception(f"计算效率残差时出错: {str(e)}")
        delta_eta_avg = -0.02
    
    # 使用不平衡度和负序分量估计故障程度，创建模拟特征值
    # 这里是一个简化的示例，实际应根据电机特性进行调整
    severity = max(0, min(1, unbalance_avg / 20))  # 0-1范围的故障严重度估计
    
    # 存储特征
    features = {
        "I2_avg": i_negative_avg,
        "I2_max": i_negative_avg * (1.2 + 0.3 * severity),  # 根据故障严重度调整峰值
        "I2_I1_ratio": i_negative_avg / i_positive_avg if i_positive_avg > 0 else 0.01,
        "unbalance_avg": unbalance_avg,
        "unbalance_max": unbalance_avg * (1.3 + 0.2 * severity),  # 根据故障严重度调整峰值
        "delta_I2_avg": i_negative_avg - 0.02,  # 相对于标准参考值的残差
        "delta_I2_std": i_negative_avg * (0.1 + 0.2 * severity),  # 根据故障严重度调整波动性
        "kurtosis_delta_iq": kurtosis_delta_iq,
        "delta_Iq_std": delta_iq_std,
        "delta_eta_avg": delta_eta_avg,
        "delta_eta_std": 0.01 * (1 + severity)  # 根据故障严重度调整波动性
    }
    
    return features 