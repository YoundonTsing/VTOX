"""
车联网故障诊断服务模块

模块结构：
├── analyzer/              # 性能优化版分析器（Redis Stream）
├── diagnosis/             # 传统诊断算法（基础队列）  
├── redis_queue/           # Redis List队列架构
├── redis_stream/          # Redis Stream分布式架构
├── simple_queue.py        # 简单内存队列
└── memory_queue.py        # 内存队列

架构选择指南：
- 基础应用：使用 simple_queue + diagnosis 模块
- 持久化需求：使用 redis_queue + diagnosis 模块  
- 分布式车联网：使用 redis_stream + analyzer 模块
"""

# 基础队列服务
from .simple_queue import simple_queue, SimpleQueue, TOPICS
from .memory_queue import MemoryQueue

# 队列架构模块
from . import redis_queue
from . import redis_stream

# 分析器模块
from . import analyzer
from . import diagnosis

__all__ = [
    # 基础队列
    'simple_queue',
    'SimpleQueue', 
    'MemoryQueue',
    'TOPICS',
    
    # 架构模块
    'redis_queue',
    'redis_stream',
    
    # 分析模块
    'analyzer',
    'diagnosis'
] 