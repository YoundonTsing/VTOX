#!/usr/bin/env python3
"""
Redis Stream维护模块
负责定期清理和维护Redis Stream，防止内存无限增长
采用非侵入式设计，不影响现有业务逻辑
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Union, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import redis.asyncio as redis

logger = logging.getLogger(__name__)

@dataclass
class StreamMaintenanceConfig:
    """Stream维护配置"""
    # 基础配置
    enabled: bool = True                    # 是否启用维护
    maintenance_interval: int = 300         # 维护间隔（秒），默认5分钟
    
    # XTRIM配置
    default_max_length: int = 10000         # 默认最大长度
    approximate_trim: bool = True           # 使用近似裁剪（性能更好）
    
    # 分级维护策略
    stream_limits: Dict[str, int] = field(default_factory=lambda: {
        # 高频数据流 - 较小限制
        "motor_raw_data": 5000,
        "performance_metrics": 3000,
        
        # 结果数据流 - 中等限制  
        "fault_diagnosis_results": 8000,
        "vehicle_health_assessments": 6000,
        
        # 告警流 - 较大限制（重要数据）
        "system_alerts": 15000
    })
    
    # 维护策略
    cleanup_empty_streams: bool = False     # 是否清理空流（谨慎使用）
    monitor_consumer_groups: bool = True    # 是否监控消费者组状态
    
    # 性能保护
    max_operations_per_cycle: int = 10      # 每次维护周期最大操作数
    operation_delay: float = 0.1           # 操作间延迟（秒）

@dataclass  
class MaintenanceStats:
    """维护统计信息"""
    total_cycles: int = 0
    total_trimmed: int = 0
    total_messages_removed: int = 0
    last_maintenance: Optional[datetime] = None
    stream_stats: Dict[str, Dict] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    def add_error(self, error: str):
        """添加错误记录，保持最近50个"""
        self.errors.append(f"{datetime.now().isoformat()}: {error}")
        if len(self.errors) > 50:
            self.errors = self.errors[-50:]

class StreamMaintenanceManager:
    """
    Redis Stream维护管理器
    
    设计原则：
    1. 非侵入式：不影响现有业务逻辑
    2. 安全第一：保守的清理策略
    3. 可配置：支持灵活的维护策略
    4. 可监控：提供详细的维护统计
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 config: Optional[StreamMaintenanceConfig] = None):
        self.redis_url = redis_url
        self.config = config or StreamMaintenanceConfig()
        self.redis_client: Optional[redis.Redis] = None
        self.is_running = False
        self.maintenance_task: Optional[asyncio.Task] = None
        self.stats = MaintenanceStats()
        
        # 运行时状态
        self._last_discovery = 0
        self._discovered_streams = set()
        
    async def initialize(self) -> bool:
        """初始化维护管理器"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30
            )
            await self.redis_client.ping()
            logger.info("✅ Stream维护管理器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ Stream维护管理器初始化失败: {e}")
            self.stats.add_error(f"初始化失败: {e}")
            return False
    
    async def start_maintenance(self) -> bool:
        """启动维护任务"""
        if not self.config.enabled:
            logger.info("⏸️ Stream维护已禁用")
            return False
            
        if self.is_running:
            logger.warning("⚠️ 维护任务已在运行")
            return True
            
        if not self.redis_client:
            logger.error("❌ Redis客户端未初始化")
            return False
            
        self.is_running = True
        self.maintenance_task = asyncio.create_task(self._maintenance_loop())
        logger.info(f"🧹 Stream维护任务已启动，间隔: {self.config.maintenance_interval}秒")
        return True
    
    async def stop_maintenance(self):
        """停止维护任务"""
        self.is_running = False
        if self.maintenance_task and not self.maintenance_task.done():
            self.maintenance_task.cancel()
            try:
                await self.maintenance_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Stream维护任务已停止")
    
    async def _maintenance_loop(self):
        """维护循环"""
        while self.is_running:
            try:
                await self._perform_maintenance()
                await asyncio.sleep(self.config.maintenance_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 维护循环异常: {e}")
                self.stats.add_error(f"维护循环异常: {e}")
                # 发生异常时等待更长时间再重试
                await asyncio.sleep(self.config.maintenance_interval * 2)
    
    async def _perform_maintenance(self):
        """执行一次完整的维护"""
        start_time = time.time()
        self.stats.total_cycles += 1
        self.stats.last_maintenance = datetime.now()
        
        logger.debug("🔧 开始Stream维护...")
        
        try:
            # 1. 发现需要维护的Stream
            streams_to_maintain = await self._discover_streams()
            
            # 2. 执行XTRIM操作
            operations_count = 0
            for stream_name in streams_to_maintain:
                if operations_count >= self.config.max_operations_per_cycle:
                    logger.debug(f"⏸️ 达到单次维护操作上限: {self.config.max_operations_per_cycle}")
                    break
                
                await self._trim_stream(stream_name)
                operations_count += 1
                
                # 操作间延迟，避免对Redis造成压力
                if self.config.operation_delay > 0:
                    await asyncio.sleep(self.config.operation_delay)
            
            # 3. 监控消费者组状态（如果启用）
            if self.config.monitor_consumer_groups:
                await self._monitor_consumer_groups()
            
            elapsed = time.time() - start_time
            logger.debug(f"✅ Stream维护完成，耗时: {elapsed:.2f}秒，处理: {operations_count}个流")
            
        except Exception as e:
            logger.error(f"❌ 执行维护失败: {e}")
            self.stats.add_error(f"执行维护失败: {e}")
    
    async def _discover_streams(self) -> List[str]:
        """发现需要维护的Stream"""
        try:
            # 缓存发现结果，避免频繁扫描
            current_time = time.time()
            if current_time - self._last_discovery < 60:  # 1分钟缓存
                return list(self._discovered_streams)
            
            # 获取所有Stream
            all_keys = await self.redis_client.keys("*")
            streams = []
            
            for key in all_keys:
                try:
                    # 检查是否为Stream类型
                    key_type = await self.redis_client.type(key)
                    if key_type == "stream":
                        streams.append(key)
                except Exception as e:
                    logger.debug(f"检查key类型失败 {key}: {e}")
                    continue
            
            # 过滤出配置中的Stream或使用默认策略
            streams_to_maintain = []
            for stream in streams:
                if stream in self.config.stream_limits:
                    streams_to_maintain.append(stream)
                elif not self.config.stream_limits:  # 如果没有配置限制，维护所有Stream
                    streams_to_maintain.append(stream)
            
            self._discovered_streams = set(streams_to_maintain)
            self._last_discovery = current_time
            
            logger.debug(f"🔍 发现 {len(streams_to_maintain)} 个需要维护的Stream")
            return streams_to_maintain
            
        except Exception as e:
            logger.error(f"❌ 发现Stream失败: {e}")
            self.stats.add_error(f"发现Stream失败: {e}")
            return []
    
    async def _trim_stream(self, stream_name: str):
        """裁剪指定Stream"""
        try:
            # 获取Stream当前长度
            current_length = await self.redis_client.xlen(stream_name)
            
            # 确定裁剪限制
            max_length = self.config.stream_limits.get(
                stream_name, 
                self.config.default_max_length
            )
            
            # 只有超过限制才进行裁剪
            if current_length <= max_length:
                logger.debug(f"📊 {stream_name}: {current_length}/{max_length} - 无需裁剪")
                return
            
            # 执行XTRIM
            if self.config.approximate_trim:
                # 近似裁剪，性能更好
                trimmed = await self.redis_client.xtrim(
                    stream_name, 
                    maxlen=max_length, 
                    approximate=True
                )
            else:
                # 精确裁剪
                trimmed = await self.redis_client.xtrim(
                    stream_name, 
                    maxlen=max_length
                )
            
            # 更新统计
            self.stats.total_trimmed += 1
            self.stats.total_messages_removed += trimmed
            
            # 记录Stream统计
            if stream_name not in self.stats.stream_stats:
                self.stats.stream_stats[stream_name] = {
                    "trim_count": 0,
                    "messages_removed": 0,
                    "last_trimmed": None
                }
            
            stream_stat = self.stats.stream_stats[stream_name]
            stream_stat["trim_count"] += 1
            stream_stat["messages_removed"] += trimmed
            stream_stat["last_trimmed"] = datetime.now().isoformat()
            
            logger.info(f"🧹 {stream_name}: {current_length} → {max_length}, 删除: {trimmed}条消息")
            
        except Exception as e:
            logger.error(f"❌ 裁剪Stream {stream_name} 失败: {e}")
            self.stats.add_error(f"裁剪Stream {stream_name} 失败: {e}")
    
    async def _monitor_consumer_groups(self):
        """监控消费者组状态"""
        try:
            # 这里可以添加消费者组健康检查逻辑
            # 比如检查pending消息数量，消费者空闲时间等
            logger.debug("🔍 监控消费者组状态...")
            
        except Exception as e:
            logger.debug(f"监控消费者组失败: {e}")
    
    async def get_maintenance_stats(self) -> Dict[str, Any]:
        """获取维护统计信息"""
        return {
            "enabled": self.config.enabled,
            "running": self.is_running,
            "stats": {
                "total_cycles": self.stats.total_cycles,
                "total_trimmed": self.stats.total_trimmed,
                "total_messages_removed": self.stats.total_messages_removed,
                "last_maintenance": self.stats.last_maintenance.isoformat() if self.stats.last_maintenance else None,
                "error_count": len(self.stats.errors)
            },
            "stream_stats": self.stats.stream_stats,
            "config": {
                "maintenance_interval": self.config.maintenance_interval,
                "default_max_length": self.config.default_max_length,
                "stream_limits": self.config.stream_limits
            },
            "recent_errors": self.stats.errors[-5:] if self.stats.errors else []
        }
    
    async def manual_trim_stream(self, stream_name: str, max_length: Optional[int] = None) -> Dict[str, Any]:
        """手动裁剪指定Stream"""
        try:
            if not self.redis_client:
                return {"success": False, "error": "Redis客户端未初始化"}
            
            current_length = await self.redis_client.xlen(stream_name)
            target_length = max_length or self.config.stream_limits.get(
                stream_name, self.config.default_max_length
            )
            
            if current_length <= target_length:
                return {
                    "success": True,
                    "message": f"Stream {stream_name} 无需裁剪",
                    "current_length": current_length,
                    "target_length": target_length,
                    "trimmed": 0
                }
            
            trimmed = await self.redis_client.xtrim(
                stream_name, 
                maxlen=target_length, 
                approximate=self.config.approximate_trim
            )
            
            return {
                "success": True,
                "message": f"Stream {stream_name} 裁剪成功",
                "current_length": current_length,
                "target_length": target_length,
                "trimmed": trimmed
            }
            
        except Exception as e:
            error_msg = f"手动裁剪Stream {stream_name} 失败: {e}"
            logger.error(error_msg)
            self.stats.add_error(error_msg)
            return {"success": False, "error": str(e)}
    
    async def update_config(self, new_config: Dict[str, Any]) -> bool:
        """动态更新配置"""
        try:
            # 更新配置
            if "enabled" in new_config:
                self.config.enabled = new_config["enabled"]
            if "maintenance_interval" in new_config:
                self.config.maintenance_interval = new_config["maintenance_interval"]
            if "default_max_length" in new_config:
                self.config.default_max_length = new_config["default_max_length"]
            if "stream_limits" in new_config:
                self.config.stream_limits.update(new_config["stream_limits"])
            
            logger.info("✅ 维护配置已更新")
            return True
            
        except Exception as e:
            logger.error(f"❌ 更新配置失败: {e}")
            return False
    
    async def cleanup(self):
        """清理资源"""
        await self.stop_maintenance()
        if self.redis_client:
            await self.redis_client.close()

# 全局维护管理器实例
stream_maintenance_manager = StreamMaintenanceManager() 