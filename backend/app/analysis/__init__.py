"""
匝间短路分析模块
包含特征计算和故障评分功能
"""
from .feature_calculator import calculate_features
from .fault_scorer import calculate_fault_score

__all__ = ['calculate_features', 'calculate_fault_score'] 