"""
⚠️  文件已迁移通知
==================

此文件已迁移到新位置：backend/app/services/redis_stream/distributed_diagnosis_stream.py

请关闭当前文件，并从新位置重新打开：
- 新路径：backend/app/services/redis_stream/distributed_diagnosis_stream.py

这是一个临时重定向文件，用于消除VS Code缓存导致的导入错误。
"""

# 临时导入analyzer来消除Pylance错误
from .analyzer.turn_fault_analyzer import TurnFaultAnalyzer
from .analyzer.insulation_analyzer import InsulationAnalyzer
from .analyzer.bearing_analyzer import BearingAnalyzer
from .analyzer.eccentricity_analyzer import EccentricityAnalyzer
from .analyzer.broken_bar_analyzer import BrokenBarAnalyzer

# 重定向导入到新位置
try:
    from .redis_stream.distributed_diagnosis_stream import *
    print("🔄 已从新位置重定向导入 DistributedDiagnosisStream")
except ImportError as e:
    print(f"❌ 重定向失败: {e}")
    print("📍 请手动打开新位置的文件：backend/app/services/redis_stream/distributed_diagnosis_stream.py") 