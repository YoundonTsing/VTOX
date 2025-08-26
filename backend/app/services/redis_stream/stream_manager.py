import asyncio
import logging
from typing import Dict, Any, List, Optional
from .distributed_diagnosis_stream import distributed_diagnosis, FaultType

logger = logging.getLogger("stream-manager")

class StreamManager:
    """Redis Stream管理器 - 简化分布式诊断系统的使用"""
    
    def __init__(self):
        self.distributed_system = distributed_diagnosis
        self.is_initialized = False
        
        # 🆕 维护功能集成（非侵入式）
        self._maintenance_manager = None
        self._maintenance_enabled = False
        
    async def initialize(self, redis_url: str = "redis://localhost:6379", 
                        enable_maintenance: bool = True) -> bool:
        """初始化分布式诊断系统"""
        try:
            self.distributed_system.redis_url = redis_url
            success = await self.distributed_system.connect()
            self.is_initialized = success
            
            # 🆕 可选的维护功能初始化
            if success and enable_maintenance:
                await self._initialize_maintenance(redis_url)
            
            return success
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False
    
    async def _initialize_maintenance(self, redis_url: str):
        """初始化Stream维护功能（非侵入式）"""
        try:
            from .stream_maintenance import StreamMaintenanceManager, StreamMaintenanceConfig
            
            # 创建适合车联网场景的维护配置
            maintenance_config = StreamMaintenanceConfig(
                enabled=True,
                maintenance_interval=600,  # 10分钟间隔，不影响业务
                default_max_length=8000,   # 保守的默认限制
                stream_limits={
                    # 针对项目中的Stream进行优化配置
                    "motor_raw_data": 5000,           # 原始数据，高频但可以适当清理
                    "fault_diagnosis_results": 10000, # 诊断结果，重要数据保留更多
                    "vehicle_health_assessments": 8000, # 健康评估，中等重要性
                    "performance_metrics": 3000,       # 性能指标，可以较激进清理
                    "system_alerts": 15000            # 系统告警，重要数据保留最多
                },
                approximate_trim=True,      # 使用近似裁剪，性能更好
                max_operations_per_cycle=5, # 限制单次操作数，避免影响业务
                operation_delay=0.2        # 操作间延迟，更保守
            )
            
            self._maintenance_manager = StreamMaintenanceManager(redis_url, maintenance_config)
            
            # 初始化但不立即启动，由用户控制
            init_success = await self._maintenance_manager.initialize()
            if init_success:
                self._maintenance_enabled = True
                logger.info("🧹 Stream维护功能已初始化（未启动）")
                logger.info("   💡 可通过 start_stream_maintenance() 启动")
            else:
                logger.warning("⚠️ Stream维护功能初始化失败，不影响主要功能")
                
        except Exception as e:
            logger.warning(f"⚠️ Stream维护功能初始化异常: {e}")
            logger.info("   📝 主要功能不受影响，可稍后手动启用维护")
    
    # 🆕 维护功能的公共接口
    async def start_stream_maintenance(self) -> bool:
        """启动Stream维护功能"""
        if not self._maintenance_enabled or not self._maintenance_manager:
            logger.warning("⚠️ Stream维护功能未初始化")
            return False
        
        try:
            success = await self._maintenance_manager.start_maintenance()
            if success:
                logger.info("✅ Stream维护功能已启动")
            return success
        except Exception as e:
            logger.error(f"❌ 启动Stream维护失败: {e}")
            return False
    
    async def stop_stream_maintenance(self):
        """停止Stream维护功能"""
        if self._maintenance_manager:
            await self._maintenance_manager.stop_maintenance()
            logger.info("🛑 Stream维护功能已停止")
    
    async def get_maintenance_stats(self) -> Dict[str, Any]:
        """获取维护统计信息"""
        if not self._maintenance_manager:
            return {"error": "维护功能未初始化"}
        
        return await self._maintenance_manager.get_maintenance_stats()
    
    async def manual_trim_stream(self, stream_name: str, max_length: Optional[int] = None) -> Dict[str, Any]:
        """手动裁剪指定Stream"""
        if not self._maintenance_manager:
            return {"success": False, "error": "维护功能未初始化"}
        
        return await self._maintenance_manager.manual_trim_stream(stream_name, max_length)
    
    async def update_maintenance_config(self, config_updates: Dict[str, Any]) -> bool:
        """更新维护配置"""
        if not self._maintenance_manager:
            logger.warning("维护功能未初始化")
            return False
        
        return await self._maintenance_manager.update_config(config_updates)

    async def start_diagnosis_system(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """启动完整的分布式诊断系统"""
        if not self.is_initialized:
            logger.error("系统未初始化，请先调用initialize()")
            return False
        
        try:
            # 默认配置
            default_config = {
                "consumers_per_fault": 2,  # 每种故障类型的消费者数量
                "enable_aggregation": True,  # 是否启用结果聚合
                "enable_monitoring": True   # 是否启用性能监控
            }
            
            if config:
                default_config.update(config)
            
            # 启动分布式系统
            await self.distributed_system.start_distributed_system(
                num_consumers_per_fault=default_config["consumers_per_fault"]
            )
            
            logger.info("✅ 分布式诊断系统启动成功")
            
            # 🆕 可选：自动启动维护功能
            if self._maintenance_enabled and default_config.get("enable_stream_maintenance", True):
                maintenance_started = await self.start_stream_maintenance()
                if maintenance_started:
                    logger.info("🧹 Stream维护功能已自动启动")
                else:
                    logger.info("📝 Stream维护功能启动失败，可稍后手动启动")
            
            return True
            
        except Exception as e:
            logger.error(f"启动分布式系统失败: {e}")
            return False
    
    async def publish_motor_data(self, vehicle_id: str, sensor_data: Dict[str, Any],
                               location: Optional[str] = None, additional_metadata: Optional[Dict] = None) -> bool:
        """发布电机传感器数据到分布式诊断系统"""
        if not self.is_initialized:
            logger.error("系统未初始化")
            return False
        
        try:
            # 构建元数据
            metadata = {
                "location": location,
                "data_source": "vehicle_sensor",
                "data_version": "v2.0"
            }
            
            if additional_metadata:
                metadata.update(additional_metadata)
            
            # 发布数据
            success = await self.distributed_system.publish_motor_data(
                vehicle_id=vehicle_id,
                sensor_data=sensor_data,
                metadata=metadata
            )
            
            if success:
                logger.debug(f"📤 发布车辆{vehicle_id}传感器数据成功")
            
            return success
            
        except Exception as e:
            logger.error(f"发布数据失败: {e}")
            return False
    
    async def get_vehicle_health_status(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """获取车辆整体健康状态"""
        try:
            if not self.distributed_system.redis_client:
                return None
            
            # 从健康评估流中获取最新数据
            messages = await self.distributed_system.redis_client.xrevrange(
                "vehicle_health_assessments",
                count=100  # 获取最近100条记录
            )
            
            # 查找指定车辆的最新健康状态
            for message_id, fields in messages:
                if fields.get("vehicle_id") == vehicle_id:
                    import json
                    overall_health = json.loads(fields["overall_health"])
                    fault_states = json.loads(fields["fault_states"])
                    
                    return {
                        "vehicle_id": vehicle_id,
                        "overall_health": overall_health,
                        "fault_details": fault_states,
                        "last_updated": fields["timestamp"],
                        "message_id": message_id
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"获取车辆健康状态失败: {e}")
            return None
    
    async def get_critical_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最新的严重故障告警"""
        try:
            if not self.distributed_system.redis_client:
                return []
            
            # 从告警流中获取最新告警
            messages = await self.distributed_system.redis_client.xrevrange(
                self.distributed_system.streams["system_alerts"],
                count=limit
            )
            
            alerts = []
            for message_id, fields in messages:
                import json
                from datetime import datetime
                
                # 防护性处理，确保所有必需字段都存在
                alert = {
                    "alert_id": message_id,
                    "alert_type": fields.get("alert_type", "unknown"),
                    "vehicle_id": fields.get("vehicle_id", "unknown"),
                    "severity": fields.get("severity", "medium"),
                    "health_score": float(fields.get("health_score", 0.5)),
                    "critical_faults": json.loads(fields.get("critical_faults", "[]")),
                    "timestamp": fields.get("alert_timestamp", datetime.now().isoformat()),
                    "requires_action": fields.get("requires_immediate_action", "false") == "true"
                }
                alerts.append(alert)
            
            return alerts
            
        except Exception as e:
            logger.error(f"获取告警信息失败: {e}")
            return []
    
    async def get_system_performance(self) -> Dict[str, Any]:
        """获取系统性能统计"""
        try:
            # 获取分布式系统统计
            system_stats = await self.distributed_system.get_system_stats()
            
            # 获取最新性能指标
            performance_metrics = []
            if self.distributed_system.redis_client:
                messages = await self.distributed_system.redis_client.xrevrange(
                    self.distributed_system.streams["performance_metrics"],
                    count=50
                )
                
                for message_id, fields in messages:
                    metric = {
                        "fault_type": fields["fault_type"],
                        "consumer_id": fields["consumer_id"],
                        "processing_time": float(fields["processing_time"]),
                        "timestamp": fields["timestamp"]
                    }
                    performance_metrics.append(metric)
            
            # 🆕 包含维护统计信息
            result = {
                "system_stats": system_stats,
                "recent_performance": performance_metrics,
                "fault_types_supported": [ft.value for ft in FaultType]
            }
            
            # 添加维护统计（如果可用）
            if self._maintenance_manager:
                maintenance_stats = await self.get_maintenance_stats()
                result["maintenance_stats"] = maintenance_stats
            
            return result
            
        except Exception as e:
            logger.error(f"获取性能统计失败: {e}")
            return {"error": str(e)}
    
    async def scale_consumers(self, fault_type: str, new_count: int) -> bool:
        """动态扩展特定故障类型的消费者数量"""
        try:
            logger.info(f"🔄 动态扩展{fault_type}消费者数量至{new_count}")
            
            if not self.is_initialized:
                logger.error("系统未初始化，无法扩展消费者")
                return False
            
            # 验证故障类型
            valid_fault_types = [ft.value for ft in FaultType]
            if fault_type not in valid_fault_types:
                logger.error(f"无效的故障类型: {fault_type}")
                return False
            
            # 这里应该实现动态扩展逻辑
            # 由于现有架构限制，这个功能需要重构distributed_diagnosis_stream
            logger.warning("⚠️ 动态扩展功能需要架构重构，当前版本暂不支持")
            return False
            
        except Exception as e:
            logger.error(f"动态扩展失败: {e}")
            return False
    
    async def get_fault_diagnosis_history(self, vehicle_id: str, 
                                        fault_type: Optional[str] = None,
                                        hours: int = 24) -> List[Dict[str, Any]]:
        """获取车辆故障诊断历史"""
        try:
            if not self.distributed_system.redis_client:
                return []
            
            # 计算时间范围
            import time
            end_time = int(time.time() * 1000)
            start_time = end_time - (hours * 60 * 60 * 1000)
            
            # 从诊断结果流中获取历史数据
            messages = await self.distributed_system.redis_client.xrange(
                self.distributed_system.streams["fault_results"],
                min=f"{start_time}-0",
                max=f"{end_time}-0"
            )
            
            history = []
            for message_id, fields in messages:
                if fields["vehicle_id"] == vehicle_id:
                    if fault_type is None or fields["fault_type"] == fault_type:
                        import json
                        record = {
                            "message_id": message_id,
                            "vehicle_id": fields["vehicle_id"],
                            "fault_type": fields["fault_type"],
                            "status": fields["status"],
                            "score": float(fields["score"]),
                            "features": json.loads(fields["features"]),
                            "timestamp": fields["timestamp"],
                            "processing_time": float(fields["processing_time"])
                        }
                        history.append(record)
            
            # 按时间排序
            history.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return history
            
        except Exception as e:
            logger.error(f"获取诊断历史失败: {e}")
            return []
    
    async def stop_system(self) -> bool:
        """停止分布式诊断系统"""
        try:
            await self.distributed_system.stop()
            self.is_initialized = False
            logger.info("✅ 分布式系统已停止")
            return True
        except Exception as e:
            logger.error(f"停止系统失败: {e}")
            return False

    async def get_stream_info(self) -> Dict[str, Any]:
        """获取所有Stream的详细信息"""
        try:
            if not self.distributed_system.redis_client:
                return {"error": "Redis客户端未连接"}
            
            stream_info = {}
            
            # 获取项目中定义的Stream信息
            for stream_key, stream_name in self.distributed_system.streams.items():
                try:
                    # 获取Stream长度
                    length = await self.distributed_system.redis_client.xlen(stream_name)
                    
                    # 获取Stream信息
                    info = await self.distributed_system.redis_client.xinfo_stream(stream_name)
                    
                    stream_info[stream_name] = {
                        "key": stream_key,
                        "length": length,
                        "first_entry": info.get("first-entry"),
                        "last_entry": info.get("last-entry"),
                        "groups": info.get("groups", 0),
                        "max_deleted_entry_id": info.get("max-deleted-entry-id"),
                        "entries_added": info.get("entries-added", 0)
                    }
                    
                except Exception as e:
                    stream_info[stream_name] = {"error": str(e)}
            
            return {
                "streams": stream_info,
                "total_streams": len(stream_info),
                "maintenance_enabled": self._maintenance_enabled
            }
            
        except Exception as e:
            logger.error(f"获取Stream信息失败: {e}")
            return {"error": str(e)}
    
    async def cleanup(self):
        """清理资源"""
        try:
            # 停止维护功能
            if self._maintenance_manager:
                await self._maintenance_manager.cleanup()
            
            # 停止分布式系统
            if self.distributed_system.is_running:
                await self.distributed_system.stop()
            
            logger.info("✅ StreamManager资源清理完成")
            
        except Exception as e:
            logger.error(f"❌ 资源清理失败: {e}")

# 全局流管理器实例
stream_manager = StreamManager() 