import numpy as np
import pandas as pd
from scipy import stats
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def calculate_features(df: pd.DataFrame) -> Dict[str, float]:
    """
    计算电机数据的特征参数
    
    参数:
        df: 包含电机数据的DataFrame
        
    返回:
        包含计算出的特征参数的字典
    """
    # 检查并处理缺失数据
    df = handle_missing_data(df)
    
    # 1. 计算负序电流分量 I₂
    a = np.exp(1j * 2 * np.pi / 3)  # 120°相位因子
    I_positive = (df['Ia'] + a * df['Ib'] + a**2 * df['Ic']) / 3
    I_negative = (df['Ia'] + a**2 * df['Ib'] + a * df['Ic']) / 3
    I2 = np.abs(I_negative)
    I1 = np.abs(I_positive)
    
    # 2. 计算电流不平衡度
    I_avg = (df['Ia'] + df['Ib'] + df['Ic']) / 3
    unbalance = (df[['Ia', 'Ib', 'Ic']].max(axis=1) - df[['Ia', 'Ib', 'Ic']].min(axis=1)) / I_avg * 100
    
    # 3. 计算I₂残差ΔI₂ (与参考值的差异)
    if 'I2_ref' in df.columns and not df['I2_ref'].isna().all():
        I2_ref = df['I2_ref']
    else:
        # 如果没有I2_ref，使用I2平均值的10%作为参考值
        I2_ref = pd.Series([np.mean(I2) * 0.1] * len(df))
        logger.info(f"I2_ref列缺失，使用I2平均值的10%作为参考值: {I2_ref.mean():.4f}")
        
    delta_I2 = I2 - I2_ref
    
    # 4. 计算ΔI_q及其峭度
    if 'Iq_actual' in df.columns and 'Iq_ref' in df.columns and not (df['Iq_actual'].isna().all() or df['Iq_ref'].isna().all()):
        delta_Iq = df['Iq_actual'] - df['Iq_ref']
    else:
        # 如果没有Iq数据，使用转矩和电流估算
        try:
            # 估算q轴电流：Iq ≈ Torque / (1.5 * p * λ_m)，其中p是极对数，λ_m是永磁体磁链
            # 这里使用简化计算，假设Iq_actual与Torque成正比
            if 'Torque' in df.columns and not df['Torque'].isna().all():
                # 使用转矩估算Iq_actual
                torque_avg = df['Torque'].abs().mean()
                current_avg = df[['Ia', 'Ib', 'Ic']].abs().mean().mean()
                
                # 简化估算：Iq_actual ≈ k * Torque，其中k是比例系数
                k = current_avg / (torque_avg + 1e-6)  # 避免除零
                Iq_actual = df['Torque'].abs() * k
                
                # Iq_ref设为Iq_actual的平均值
                Iq_ref = pd.Series([Iq_actual.mean()] * len(df))
                
                delta_Iq = Iq_actual - Iq_ref
                logger.info(f"Iq数据缺失，使用转矩估算Iq值，平均值: {Iq_actual.mean():.4f}")
            else:
                # 如果没有转矩数据，使用默认值
                delta_Iq = pd.Series([0.05] * len(df))
                logger.info("Iq和转矩数据均缺失，使用默认Iq残差值: 0.05")
        except Exception as e:
            logger.warning(f"估算Iq值时出错: {str(e)}，使用默认值")
            delta_Iq = pd.Series([0.05] * len(df))
    
    # 使用滑动窗口计算峭度 (窗口大小100个样本)
    try:
        # 检查样本量是否足够
        valid_data = delta_Iq.dropna()
        if len(valid_data) >= 8:  # 至少需要8个点才能计算峭度
            window_size = min(len(valid_data), 100)
            kurtosis_values = []
            
            for i in range(0, len(valid_data) - window_size + 1, max(1, window_size // 10)):
                window_data = valid_data.iloc[i:i+window_size]
                try:
                    kurt = stats.kurtosis(window_data, fisher=True)  # Fisher=True减去3，使正态分布的峭度为0
                    if not np.isnan(kurt) and not np.isinf(kurt):
                        kurtosis_values.append(kurt)
                except Exception:
                    continue
            
            if kurtosis_values:
                kurtosis_delta_iq = np.mean(kurtosis_values)
            else:
                kurtosis_delta_iq = 2.0  # 默认值
                logger.info("无法计算有效峭度值，使用默认值: 2.0")
        else:
            kurtosis_delta_iq = 2.0  # 默认值
            logger.info(f"样本量不足({len(valid_data)}个)，无法计算峭度，使用默认值: 2.0")
    except Exception as e:
        logger.warning(f"计算峭度时出错: {str(e)}，使用默认值")
        kurtosis_delta_iq = 2.0  # 默认值
    
    # 5. 计算效率残差Δη
    try:
        # 计算实际效率
        if ('Torque' in df.columns and not df['Torque'].isna().all() and 
            'Speed' in df.columns and not df['Speed'].isna().all() and 
            'Vdc' in df.columns and not df['Vdc'].isna().all() and
            not (df['Ia'].isna().all() or df['Ib'].isna().all() or df['Ic'].isna().all())):
            
            # 计算机械功率 (W) = 转矩(Nm) * 转速(rad/s)
            # 将rpm转换为rad/s: ω(rad/s) = rpm * 2π/60
            mech_power = df['Torque'].abs() * df['Speed'].abs() * 2 * np.pi / 60
            
            # 计算电功率 (W) = 三相电流平方和的平均值 * 电压
            elec_power = (df['Ia']**2 + df['Ib']**2 + df['Ic']**2).mean() * df['Vdc'].mean()
            
            if elec_power > 0 and mech_power.mean() > 0:
                eta_actual = mech_power.mean() / elec_power
                # 限制效率在合理范围内 (0.5-0.98)
                eta_actual = max(0.5, min(eta_actual, 0.98))
                logger.info(f"计算得到实际效率: {eta_actual:.4f}")
            else:
                eta_actual = 0.85  # 默认效率
                logger.info("功率计算结果异常，使用默认效率: 0.85")
        else:
            eta_actual = 0.85  # 默认效率
            logger.info("缺少计算效率所需的列，使用默认效率: 0.85")
        
        # 获取参考效率
        if 'Eta_ref' in df.columns and not df['Eta_ref'].isna().all():
            eta_ref = df['Eta_ref'].mean()
        else:
            # 如果没有参考效率，使用0.93作为默认值
            eta_ref = 0.93
            logger.info(f"Eta_ref列缺失，使用默认参考效率: {eta_ref}")
        
        delta_eta = eta_actual - eta_ref
        
    except Exception as e:
        logger.warning(f"计算效率残差时出错: {str(e)}，使用默认值")
        delta_eta = -0.02  # 默认效率残差
    
    # 6. 计算DQ轴电流残差的标准差 (衡量波动性)
    if 'Id_actual' in df.columns and not df['Id_actual'].isna().all():
        delta_Id_std = df['Id_actual'].std()
    else:
        delta_Id_std = 0.02  # 默认值
        logger.info("Id_actual列缺失，使用默认标准差: 0.02")
    
    delta_Iq_std = delta_Iq.std()
    
    # 返回计算的特征参数
    features = {
        "I2_avg": float(I2.mean()),
        "I2_max": float(I2.max()),
        "I2_I1_ratio": float((I2 / I1).mean()),  # I₂/I₁比值，更能反映严重程度
        "unbalance_avg": float(unbalance.mean()),
        "unbalance_max": float(unbalance.max()),
        "delta_I2_avg": float(delta_I2.mean()),
        "delta_I2_std": float(delta_I2.std()),
        "kurtosis_delta_iq": float(kurtosis_delta_iq),
        "delta_Iq_std": float(delta_Iq_std),
        "delta_eta_avg": float(delta_eta),
        "delta_eta_std": float(0.01)  # 简化处理
    }
    
    # 检查并处理无效值
    for key, value in features.items():
        if np.isnan(value) or np.isinf(value):
            logger.warning(f"特征 {key} 计算结果无效，使用默认值")
            if key == "kurtosis_delta_iq":
                features[key] = 2.0
            elif key == "delta_eta_avg":
                features[key] = -0.02
            elif "I2" in key:
                features[key] = 0.02
            elif "unbalance" in key:
                features[key] = 5.0
            else:
                features[key] = 0.01
    
    logger.info(f"特征计算完成: {features}")
    return features

def handle_missing_data(df: pd.DataFrame) -> pd.DataFrame:
    """处理缺失的数据列"""
    # 创建副本避免修改原始数据
    df = df.copy()
    
    # 1. 检查并填充基本电流数据
    for col in ['Ia', 'Ib', 'Ic']:
        if col not in df.columns or df[col].isna().all():
            logger.warning(f"缺少基本电流列 {col}，无法进行有效分析")
            # 使用其他相电流的平均值，或默认值
            available_currents = [c for c in ['Ia', 'Ib', 'Ic'] if c in df.columns and not df[c].isna().all()]
            if available_currents:
                avg_current = df[available_currents].mean().mean()
                df[col] = avg_current
                logger.info(f"使用其他相电流平均值 {avg_current:.2f} 填充 {col}")
            else:
                df[col] = 100  # 默认电流值
                logger.info(f"所有相电流数据缺失，使用默认值 100 填充 {col}")
    
    # 2. 检查并填充电压数据
    if 'Vdc' not in df.columns or df['Vdc'].isna().all():
        df['Vdc'] = 380  # 默认电压值
        logger.info("缺少电压数据，使用默认值: 380V")
    
    # 3. 检查并填充转矩和转速数据
    if 'Torque' not in df.columns or df['Torque'].isna().all():
        # 根据电流估算转矩: T ≈ k * I
        avg_current = df[['Ia', 'Ib', 'Ic']].mean().mean()
        df['Torque'] = avg_current * 5  # 简化估算
        logger.info(f"缺少转矩数据，根据电流估算: {df['Torque'].mean():.2f}Nm")
    
    if 'Speed' not in df.columns or df['Speed'].isna().all():
        df['Speed'] = 1500  # 默认转速，单位rpm
        logger.info("缺少转速数据，使用默认值: 1500rpm")
    
    return df 