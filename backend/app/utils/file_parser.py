import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
import io


def parse_csv(file_content: bytes) -> Tuple[pd.DataFrame, Optional[Dict[str, Any]]]:
    """
    解析CSV文件内容并进行基本预处理
    
    参数:
        file_content: 文件二进制内容
    
    返回:
        处理后的DataFrame和可能的错误信息
    """
    try:
        # 尝试解析CSV文件
        df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
        
        # 检查基本列是否存在
        required_columns = ["Ia", "Ib", "Ic", "Vdc", "Torque", "Speed", 
                          "Iq_actual", "Iq_ref", "I2_ref", "Eta_ref"]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return None, {
                "error": "Missing columns",
                "detail": f"缺少必要的列: {', '.join(missing_columns)}"
            }
        
        # 数据类型转换
        numeric_cols = ["Ia", "Ib", "Ic", "Vdc", "Torque", "Speed", 
                      "Iq_actual", "Iq_ref", "I2_ref", "Eta_ref"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 处理缺失值
        df = handle_missing_values(df)
        
        # 处理异常值
        df = handle_outliers(df)
        
        return df, None
        
    except Exception as e:
        return None, {
            "error": "Parse error",
            "detail": str(e)
        }


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    处理数据中的缺失值
    
    参数:
        df: 原始DataFrame
    
    返回:
        处理后的DataFrame
    """
    # 对于少量缺失值，使用插值填充
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].isna().sum() > 0:
            # 如果缺失值比例小于20%，使用线性插值
            if df[col].isna().mean() < 0.2:
                df[col] = df[col].interpolate(method='linear')
            # 否则使用前向填充
            else:
                df[col] = df[col].fillna(method='ffill')
    
    # 如果仍有缺失值，使用列均值填充
    df = df.fillna(df.mean())
    
    return df


def handle_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    处理数据中的异常值
    
    参数:
        df: 原始DataFrame
    
    返回:
        处理后的DataFrame
    """
    # 使用IQR方法识别并处理极端异常值
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        
        # 定义极端异常值的边界 (较宽松，避免误删有效数据)
        lower_bound = Q1 - 5 * IQR
        upper_bound = Q3 + 5 * IQR
        
        # 对极端异常值进行限幅处理
        df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)
    
    return df


def validate_data_consistency(df: pd.DataFrame) -> Dict[str, Any]:
    """
    验证数据一致性并提供基本统计信息
    
    参数:
        df: 处理后的DataFrame
    
    返回:
        包含数据统计信息的字典
    """
    stats = {
        "rows": len(df),
        "columns": len(df.columns),
        "missing_percentage": df.isna().mean().to_dict(),
        "basic_stats": {}
    }
    
    # 计算基本统计量
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        stats["basic_stats"][col] = {
            "mean": float(df[col].mean()),
            "std": float(df[col].std()),
            "min": float(df[col].min()),
            "max": float(df[col].max())
        }
    
    return stats 