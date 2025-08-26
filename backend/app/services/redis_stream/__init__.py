"""
Redis Stream分布式架构模块
基于Redis Stream实现的分布式故障诊断系统

特性：
- 基于Redis Stream的分布式消息处理
- 支持消费者组和负载均衡
- 消息持久化和历史记录
- 故障恢复和事件溯源
- 车联网专用故障诊断
- 🆕 Stream维护和内存管理
"""

from .distributed_diagnosis_stream import (
    DistributedDiagnosisStream, 
    distributed_diagnosis,
    FaultType,
    DiagnosisResult
)

from .stream_manager import StreamManager, stream_manager

# 🆕 维护功能导出（可选，不影响现有功能）
try:
    from .stream_maintenance import (
        StreamMaintenanceManager,
        StreamMaintenanceConfig,
        MaintenanceStats,
        stream_maintenance_manager
    )
    _MAINTENANCE_AVAILABLE = True
except ImportError:
    # 如果维护模块不可用，不影响主要功能
    _MAINTENANCE_AVAILABLE = False

__all__ = [
    'DistributedDiagnosisStream',
    'distributed_diagnosis', 
    'FaultType',
    'DiagnosisResult',
    'StreamManager',
    'stream_manager'
]

# 可选的维护功能导出
if _MAINTENANCE_AVAILABLE:
    __all__.extend([
        'StreamMaintenanceManager',
        'StreamMaintenanceConfig', 
        'MaintenanceStats',
        'stream_maintenance_manager'
    ]) 