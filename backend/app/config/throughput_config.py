# -*- coding: utf-8 -*-
"""
吞吐量计算配置
包含新鲜度因子、时间窗口、递减曲线等参数的配置
"""
from dataclasses import dataclass
from typing import Optional
import math

@dataclass
class ThroughputConfig:
    """吞吐量计算配置类"""
    
    # 新鲜度因子配置
    freshness_window_minutes: int = 60  # 从30分钟延长到60分钟
    min_freshness_factor: float = 0.3   # 从0.1提高到0.3
    
    # 递减曲线配置 (支持多种曲线类型)
    decay_curve_type: str = "logarithmic"  # linear, exponential, logarithmic
    decay_steepness: float = 0.5  # 递减陡峭程度 (0.1-1.0, 越小越平缓)
    
    # 自动刷新配置
    auto_refresh_enabled: bool = True
    refresh_threshold_minutes: int = 45  # 当数据超过45分钟时自动添加刷新数据
    refresh_base_value: float = 8.0  # 刷新时的基础性能值
    
    # 计算权重配置
    base_throughput_multiplier: float = 8.0  # 从6.0提高到8.0
    activity_weight: float = 0.7  # 活跃度权重
    freshness_weight: float = 0.3  # 新鲜度权重
    
    def calculate_freshness_factor(self, age_minutes: float) -> float:
        """
        计算新鲜度因子
        支持多种递减曲线类型
        """
        if age_minutes >= self.freshness_window_minutes:
            return self.min_freshness_factor
        
        # 归一化年龄 (0-1)
        normalized_age = age_minutes / self.freshness_window_minutes
        
        if self.decay_curve_type == "linear":
            # 线性递减
            factor = 1.0 - (normalized_age * self.decay_steepness)
        elif self.decay_curve_type == "exponential":
            # 指数递减
            factor = math.exp(-normalized_age * self.decay_steepness * 3)
        elif self.decay_curve_type == "logarithmic":
            # 对数递减 (更平缓)
            factor = 1.0 - (math.log(1 + normalized_age * self.decay_steepness * 2) / math.log(3))
        else:
            # 默认平方根递减
            factor = 1.0 - (math.sqrt(normalized_age) * self.decay_steepness)
        
        return max(self.min_freshness_factor, factor)
    
    def should_auto_refresh(self, age_minutes: float) -> bool:
        """判断是否需要自动刷新数据"""
        return (self.auto_refresh_enabled and 
                age_minutes >= self.refresh_threshold_minutes)

# 全局配置实例
throughput_config = ThroughputConfig()

def update_config(**kwargs):
    """更新配置参数"""
    global throughput_config
    for key, value in kwargs.items():
        if hasattr(throughput_config, key):
            setattr(throughput_config, key, value)
            print(f"✅ 更新配置: {key} = {value}")
        else:
            print(f"❌ 未知配置项: {key}")

def get_config() -> ThroughputConfig:
    """获取当前配置"""
    return throughput_config

def reset_config():
    """重置为默认配置"""
    global throughput_config
    throughput_config = ThroughputConfig()
    print("✅ 配置已重置为默认值")