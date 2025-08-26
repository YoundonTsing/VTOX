"""
传统故障诊断算法模块
用于基础队列和Redis List队列

包含详细的故障诊断算法实现：
- 匝间短路故障诊断
- 绝缘失效故障诊断
- 轴承故障诊断
- 偏心故障诊断
- 断条故障诊断
"""

# 诊断算法函数导入（这些是函数式的诊断实现）
from .turn_to_turn_diagnosis import *
from .insulation_diagnosis import *
from .bearing_diagnosis import *
from .eccentricity_diagnosis import *
from .broken_bar_diagnosis import *

__all__ = [
    # 匝间短路诊断
    'diagnose_turn_to_turn_fault',
    
    # 绝缘失效诊断
    'diagnose_insulation_fault',
    
    # 轴承故障诊断
    'diagnose_bearing_fault',
    
    # 偏心故障诊断
    'diagnose_eccentricity_fault',
    
    # 断条故障诊断
    'diagnose_broken_bar_fault'
] 