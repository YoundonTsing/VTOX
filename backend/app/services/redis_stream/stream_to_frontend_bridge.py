#!/usr/bin/env python3
"""
Redis Stream到前端桥接组件
轻量级数据转发，不进行复杂计算，避免负载过高
支持缓存优化模式，解决消息丢失问题
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, cast
from datetime import datetime
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class StreamToFrontendBridge:
    """
    轻量级桥接组件：将Redis Stream处理结果转发到WebSocket前端
    
    设计原则：
    - 只负责数据转发，不进行任何计算
    - 保持轻量级，避免系统负载过高
    - 确保前端收到完整的vehicle_id和health_score数据
    - 支持缓存优化模式，大幅减少消息丢失
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.websocket_manager = None
        self.is_running = False
        self.is_monitoring = False  # 增加监控状态标志，用于前端控制
        self.cache_optimization_enabled = False  # 缓存优化开关
        
        # 监听的Redis Stream
        self.streams_to_monitor = {
            "fault_diagnosis_results": "fault_results_group",
            "vehicle_health_assessments": "health_group"
        }
        
        # 🚀 缓存优化器实例
        self.cache_optimizer = None
        
        # 🔧 健康检查参数
        self.last_activity_time = None
        self.health_check_interval = 300  # 5分钟检查一次
        self.max_idle_time = 600  # 10分钟闲置超时
        self.processed_messages_count = 0
        
    async def initialize(self, websocket_manager):
        """初始化桥接组件"""
        try:
            # 连接Redis（使用与现有系统相同的配置）
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30
            )
            await self.redis_client.ping()
            
            # 保存WebSocket管理器引用
            self.websocket_manager = websocket_manager
            
            # 创建消费者组
            await self._create_consumer_groups()
            
            # 🚀 初始化缓存优化器
            await self._initialize_cache_optimizer()
            
            logger.info("✅ Redis Stream到前端桥接组件初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 桥接组件初始化失败: {e}")
            return False
    
    async def add_streams_to_monitor(self, streams_dict: Dict[str, str]):
        """动态添加需要监听的Redis Stream及其消费者组。
        参数示例: {"fault_diagnosis_results": "cluster_results_group"}
        """
        if not self.redis_client:
            logger.error("❌ 桥接器未初始化，无法添加Stream")
            return False
        try:
            redis_conn = cast(redis.Redis, self.redis_client)
            # 合并新的Stream到监听列表
            self.streams_to_monitor.update(streams_dict)
            
            # 为新增的Stream创建消费者组
            for stream_name, group_name in streams_dict.items():
                try:
                    await redis_conn.xgroup_create(
                        stream_name,
                        group_name,
                        id="0",
                        mkstream=True
                    )
                    logger.info(f"✅ 添加监听Stream: {stream_name} -> {group_name}")
                except Exception as e:
                    if "BUSYGROUP" not in str(e):
                        logger.warning(f"创建消费者组失败 {stream_name}: {e}")
            
            # 如当前已在监控，则重启标准监控以纳入新流
            if self.is_monitoring:
                self.is_running = False
                await asyncio.sleep(0.5)
                self.is_running = True
                asyncio.create_task(self._start_standard_monitoring())
                logger.info("🔄 已重启桥接器监听以包含新增Stream")
            return True
        except Exception as e:
            logger.error(f"❌ 添加监听Stream失败: {e}")
            return False
    
    async def _initialize_cache_optimizer(self):
        """初始化缓存优化器"""
        # 避免重复初始化
        if self.cache_optimizer is not None:
            logger.debug("缓存优化器已初始化，跳过重复初始化")
            return
            
        try:
            from .stream_cache_optimizer import stream_cache_optimizer
            self.cache_optimizer = stream_cache_optimizer
            
            # 检查是否已经初始化过
            if hasattr(self.cache_optimizer, '_initialized') and self.cache_optimizer._initialized:
                logger.debug("缓存优化器已在其他地方初始化")
                return
                
            # 初始化优化器但不启动
            success = await self.cache_optimizer.initialize(self.websocket_manager)
            if success:
                self.cache_optimizer._initialized = True
                logger.info("🚀 缓存优化器初始化完成，可通过API启用")
            else:
                logger.error("❌ 缓存优化器初始化失败")
                self.cache_optimizer = None
                
        except Exception as e:
            logger.error(f"❌ 缓存优化器初始化失败: {e}")
            self.cache_optimizer = None
        
    async def _create_consumer_groups(self):
        """创建消费者组"""
        if not self.redis_client:
            logger.error("❌ 桥接器未初始化(redis_client为空)，无法创建消费者组")
            return
        redis_conn = cast(redis.Redis, self.redis_client)
        for stream_name, group_name in self.streams_to_monitor.items():
            try:
                await redis_conn.xgroup_create(
                    stream_name, 
                    group_name, 
                    id="0", 
                    mkstream=True
                )
                logger.debug(f"创建消费者组: {stream_name} -> {group_name}")
            except Exception as e:
                if "BUSYGROUP" not in str(e):
                    logger.warning(f"创建消费者组失败 {stream_name}: {e}")

    async def start_monitoring(self):
        """开始监听Redis Stream并转发数据"""
        if not self.redis_client or not self.websocket_manager:
            logger.error("❌ 桥接组件未初始化")
            return
        
        # 防止重复启动监控
        if self.is_monitoring:
            logger.info("📊 Redis Stream桥接监控已在运行，跳过重复启动")
            return
            
        self.is_running = True
        self.is_monitoring = True # 开始监控时设置标志
        
        # 🚀 根据缓存优化设置选择监控模式
        if self.cache_optimization_enabled and self.cache_optimizer:
            logger.info("🚀 启动Redis Stream缓存优化监控...")
            await self.cache_optimizer.start_optimized_monitoring()
        else:
            logger.info("🚀 启动Redis Stream标准监控...")
            await self._start_standard_monitoring()

    async def _start_standard_monitoring(self):
        """启动标准监控模式"""
        # 初始化活动时间
        self.last_activity_time = asyncio.get_event_loop().time()
        
        # 启动多个监听任务
        tasks = []
        
        # 监听故障诊断结果
        tasks.append(
            asyncio.create_task(
                self._monitor_fault_results()
            )
        )
        
        # 监听车辆健康评估
        tasks.append(
            asyncio.create_task(
                self._monitor_health_assessments()
            )
        )
        
        # 🔧 添加健康检查任务
        tasks.append(
            asyncio.create_task(
                self._health_monitor_loop()
            )
        )
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"❌ 监听任务异常: {e}")
        finally:
            self.is_running = False
            self.is_monitoring = False # 停止监控时重置标志

    async def enable_cache_optimization(self):
        """启用缓存优化模式"""
        if not self.cache_optimizer:
            logger.error("❌ 缓存优化器未初始化")
            return False
            
        self.cache_optimization_enabled = True
        logger.info("✅ 缓存优化模式已启用")
        return True

    async def disable_cache_optimization(self):
        """禁用缓存优化模式"""
        self.cache_optimization_enabled = False
        if self.cache_optimizer and self.cache_optimizer.is_running:
            await self.cache_optimizer.stop_monitoring()
        logger.info("🔄 缓存优化模式已禁用，切换到标准模式")
        return True

    async def get_optimization_stats(self) -> Dict[str, Any]:
        """获取缓存优化统计信息"""
        if self.cache_optimizer:
            return self.cache_optimizer.get_optimizer_stats()
        else:
            return {"error": "缓存优化器未初始化"}

    async def _monitor_fault_results(self):
        """监听故障诊断结果流"""
        consumer_id = "frontend_bridge_fault"
        group_name = self.streams_to_monitor["fault_diagnosis_results"]
        
        if not self.redis_client:
            logger.error("❌ 桥接器未初始化(redis_client为空)，无法监听故障诊断结果")
            return
        redis_conn = cast(redis.Redis, self.redis_client)

        while self.is_running:
            try:
                # 读取故障诊断结果
                messages = await redis_conn.xreadgroup(
                    group_name,
                    consumer_id,
                    {"fault_diagnosis_results": ">"},
                    count=10,
                    block=1000
                )
                
                for stream, msgs in messages:
                    for message_id, fields in msgs:
                        await self._forward_fault_result(fields, message_id)
                        
                        # 确认消息处理完成
                        await redis_conn.xack(
                            "fault_diagnosis_results",
                            group_name,
                            message_id
                        )
                        
                        # 🔧 更新活动时间和计数
                        self.last_activity_time = asyncio.get_event_loop().time()
                        self.processed_messages_count += 1
                        
            except Exception as e:
                logger.error(f"❌ 监听故障结果失败: {e}")
                await asyncio.sleep(1)

    async def _monitor_health_assessments(self):
        """监听车辆健康评估流"""
        consumer_id = "frontend_bridge_health"
        group_name = self.streams_to_monitor["vehicle_health_assessments"]
        
        if not self.redis_client:
            logger.error("❌ 桥接器未初始化(redis_client为空)，无法监听健康评估结果")
            return
        redis_conn = cast(redis.Redis, self.redis_client)

        while self.is_running:
            try:
                # 读取健康评估结果
                messages = await redis_conn.xreadgroup(
                    group_name,
                    consumer_id,
                    {"vehicle_health_assessments": ">"},
                    count=5,
                    block=1000
                )
                
                for stream, msgs in messages:
                    for message_id, fields in msgs:
                        await self._forward_health_assessment(fields, message_id)
                        
                        # 确认消息处理完成
                        await redis_conn.xack(
                            "vehicle_health_assessments",
                            group_name,
                            message_id
                        )
                        
                        # 🔧 更新活动时间和计数
                        self.last_activity_time = asyncio.get_event_loop().time()
                        self.processed_messages_count += 1
                        
            except Exception as e:
                logger.error(f"❌ 监听健康评估失败: {e}")
                await asyncio.sleep(1)

    async def _forward_fault_result(self, fields: Dict, message_id: str):
        """转发故障诊断结果到前端（轻量级，无额外计算）"""
        try:
            vehicle_id = fields.get("vehicle_id", "unknown")
            fault_type = fields.get("fault_type", "unknown")
            timestamp = fields.get("timestamp", datetime.now().isoformat())
            status = fields.get("status", "unknown")
            score = float(fields.get("score", "0.0"))
            
            # 解析特征数据
            features = {}
            try:
                features = json.loads(fields.get("features", "{}"))
            except json.JSONDecodeError:
                features = {}
            
            # 解析传感器数据 - 检查time_series和frequency_spectrum
            sensor_data = {}
            try:
                sensor_data_raw = fields.get("sensor_data", "{}")
                sensor_data = json.loads(sensor_data_raw)
                # 🔍 只在出现问题时输出调试信息，减少日志污染
                if "time_series" not in sensor_data or not sensor_data["time_series"]:
                    logger.debug(f"⚠️  [桥接] {vehicle_id}-{fault_type} 缺少或为空的time_series字段")
                # 正常情况下不输出调试日志，提升性能
            except json.JSONDecodeError as e:
                logger.warning(f"❌ [桥接] sensor_data解析失败: {e}")
                sensor_data = {}
            
            # 解析图表数据
            charts = {}
            try:
                charts = json.loads(fields.get("charts", "{}"))
            except json.JSONDecodeError:
                charts = {}
            
            # 构建标准化前端消息，符合数据流逻辑
            frontend_message = {
                "fault_type": fault_type,
                "vehicle_id": vehicle_id,
                "timestamp": timestamp,
                "status": status,
                "score": score,  # 数值类型
                "features": features,
            }
            
            # 优先从sensor_data中提取时间序列数据（后端增强架构）
            if "time_series" in sensor_data:
                frontend_message["time_series"] = sensor_data["time_series"]
            elif "time_series" in charts:
                frontend_message["time_series"] = charts["time_series"]
            
            # 优先从sensor_data中提取频谱数据（后端增强架构）
            if "frequency_spectrum" in sensor_data:
                frontend_message["spectrum"] = sensor_data["frequency_spectrum"]
            elif "frequency_spectrum" in charts:
                frontend_message["spectrum"] = charts["frequency_spectrum"]
            elif "spectrum" in charts:
                frontend_message["spectrum"] = charts["spectrum"]
            
            # 添加图表配置
            chart_config = {}
            if "time_domain" in charts:
                chart_config["time_domain"] = charts["time_domain"]
            if "frequency_domain" in charts:
                chart_config["frequency_domain"] = charts["frequency_domain"]
            if chart_config:
                frontend_message["charts"] = chart_config
            
            # 添加位置信息
            frontend_message["location"] = self._get_location_from_vehicle_id(vehicle_id)
            
            # 计算健康评分
            if score <= 0.2:
                health_score = 95.0 - (score * 25)  # 正常范围 95-90
            elif score <= 0.5:
                health_score = 90.0 - ((score - 0.2) * 100)  # 警告范围 90-60
            else:
                health_score = 60.0 - ((score - 0.5) * 120)  # 故障范围 60-0
            
            frontend_message["health_score"] = max(0.0, min(100.0, health_score))
            
            # 转发到WebSocket前端（轻量级操作）
            if self.websocket_manager:
                await self.websocket_manager.broadcast_to_frontends(frontend_message)
                # 移除高频日志输出，提升性能
            
        except Exception as e:
            logger.error(f"❌ 转发故障结果失败: {e}")

    async def _forward_health_assessment(self, fields: Dict, message_id: str):
        """转发健康评估结果到前端（轻量级，无计算）"""
        try:
            vehicle_id = fields.get("vehicle_id", "unknown")
            timestamp = fields.get("timestamp", datetime.now().isoformat())
            
            # 解析整体健康数据
            overall_health = {}
            try:
                overall_health = json.loads(fields.get("overall_health", "{}"))
            except json.JSONDecodeError:
                overall_health = {}
            
            # 解析故障状态
            fault_states = {}
            try:
                fault_states = json.loads(fields.get("fault_states", "{}"))
            except json.JSONDecodeError:
                fault_states = {}
            
            # 构建健康评估消息
            health_message = {
                "message_type": "health_assessment",
                "vehicle_id": vehicle_id,  # 关键字段：车辆ID
                "timestamp": timestamp,
                "health_score": overall_health.get("health_score", 0.0),  # 关键字段：健康评分
                "overall_status": overall_health.get("overall_status", "unknown"),
                "active_faults": overall_health.get("active_faults", []),
                "fault_details": fault_states,
                "location": self._get_location_from_vehicle_id(vehicle_id),
                "data_source": "redis_stream",
                "message_id": message_id
            }
            
            # 转发到WebSocket前端
            if self.websocket_manager:
                await self.websocket_manager.broadcast_to_frontends(health_message)
                # 移除高频日志输出，提升性能
            
        except Exception as e:
            logger.error(f"❌ 转发健康评估失败: {e}")

    def _get_location_from_vehicle_id(self, vehicle_id: str) -> str:
        """从车辆ID推导位置信息（轻量级操作，无复杂计算）"""
        if not vehicle_id or vehicle_id == "unknown":
            return "未知位置"
        
        # 简单的字符串匹配，无复杂计算
        if "粤B" in vehicle_id or "SEAL" in vehicle_id:
            return "深圳福田区"
        elif "陕A" in vehicle_id:
            if "QIN" in vehicle_id:
                return "西安高新区"
            elif "HAN" in vehicle_id:
                return "西安高新区"
            else:
                return "西安市"
        else:
            return "未知位置"

    async def stop_monitoring(self):
        """停止监听"""
        self.is_running = False
        self.is_monitoring = False # 停止监控时重置标志
        if self.redis_client:
            await self.redis_client.close()
        logger.info("🛑 Redis Stream桥接组件已停止")

    def get_bridge_stats(self) -> Dict[str, Any]:
        """获取桥接组件统计信息（轻量级）"""
        current_time = asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0
        idle_time = (current_time - self.last_activity_time) if self.last_activity_time else 0
        
        return {
            "is_running": self.is_running,
            "is_monitoring": self.is_monitoring, # 添加监控状态
            "redis_connected": self.redis_client is not None,
            "websocket_connected": self.websocket_manager is not None,
            "monitored_streams": list(self.streams_to_monitor.keys()),
            "processed_messages": self.processed_messages_count,
            "idle_time_seconds": idle_time,
            "health_status": "healthy" if idle_time < self.max_idle_time else "unhealthy"
        }

    async def _health_monitor_loop(self):
        """健康监控循环，定期检查桥接器状态"""
        while self.is_running:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if not self.is_running:
                    break
                    
                current_time = asyncio.get_event_loop().time()
                idle_time = current_time - (self.last_activity_time or current_time)
                
                # 检查是否超时闲置
                if idle_time > self.max_idle_time:
                    logger.warning(f"⚠️ 桥接器闲置超时: {idle_time:.1f}秒 > {self.max_idle_time}秒")
                    logger.info("🔄 尝试重新启动桥接器监听...")
                    
                    # 重置状态并重启
                    await self._restart_monitoring()
                else:
                    logger.debug(f"🟢 桥接器健康检查通过: 闲置{idle_time:.1f}秒, 已处理{self.processed_messages_count}条消息")
                    
            except Exception as e:
                logger.error(f"❌ 健康监控异常: {e}")
                await asyncio.sleep(30)  # 异常时等待更长时间

    async def _restart_monitoring(self):
        """重新启动监听（内部方法）"""
        try:
            # 重置活动时间
            self.last_activity_time = asyncio.get_event_loop().time()
            
            # 检查是否有积压消息需要处理
            pending_count = await self._check_pending_messages()
            
            if pending_count > 0:
                logger.info(f"📦 发现{pending_count}条积压消息，将继续处理")
            else:
                logger.info("✅ 无积压消息，桥接器状态正常")
                
        except Exception as e:
            logger.error(f"❌ 重启监听失败: {e}")

    async def _check_pending_messages(self) -> int:
        """检查积压消息数量"""
        total_pending = 0
        try:
            if not self.redis_client:
                logger.error("❌ 桥接器未初始化(redis_client为空)，无法检查积压消息")
                return 0
            redis_conn = cast(redis.Redis, self.redis_client)
            for stream_name, group_name in self.streams_to_monitor.items():
                try:
                    # 获取消费者组信息
                    consumers = await redis_conn.xinfo_consumers(stream_name, group_name)
                    for consumer in consumers:
                        if consumer['name'] in ['frontend_bridge_fault', 'frontend_bridge_health']:
                            pending = consumer['pending']
                            total_pending += pending
                            if pending > 0:
                                logger.info(f"📦 {consumer['name']}: {pending}条积压消息")
                except Exception as e:
                    logger.debug(f"检查{stream_name}积压消息失败: {e}")
                    
        except Exception as e:
            logger.error(f"检查积压消息失败: {e}")
            
        return total_pending

# 全局桥接组件实例
stream_bridge = StreamToFrontendBridge() 