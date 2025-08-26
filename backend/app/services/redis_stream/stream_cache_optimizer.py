#!/usr/bin/env python3
"""
Redis Stream缓存优化组件
利用Redis Stream的缓存特性优化消息处理性能，解决消息丢失问题
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
import redis.asyncio as redis
from collections import defaultdict
import time

logger = logging.getLogger(__name__)

class StreamCacheOptimizer:
    """
    Redis Stream缓存优化器
    
    核心特性：
    1. 消息持久化：利用Redis Stream持久化特性
    2. 智能降采样：高频数据智能采样，减少前端压力
    3. 批量处理：优化批处理策略，提高吞吐量
    4. 消息重试：失败消息自动重试机制
    5. 缓存管理：智能缓存清理和内存优化
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.websocket_manager = None
        self.is_running = False
        self._initialized = False  # 添加初始化状态标志
        
        # 🚀 高性能配置
        self.max_batch_size = 100          # 增加批处理大小
        self.processing_interval = 0.05    # 50ms处理间隔，20fps
        self.cache_ttl = 3600             # 缓存TTL 1小时
        self.max_pending_messages = 10000  # 最大待处理消息数
        
        # 🧠 智能降采样配置
        self.sampling_rates = {
            "high_frequency": 0.1,    # 高频数据10%采样率
            "medium_frequency": 0.3,  # 中频数据30%采样率
            "low_frequency": 1.0,     # 低频数据100%保留
            "critical_alerts": 1.0    # 关键警报100%保留
        }
        
        # 📊 性能统计
        self.stats = {
            "total_received": 0,
            "total_processed": 0,
            "total_cached": 0,
            "total_sampled": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "retry_count": 0,
            "error_count": 0,
            "start_time": None
        }
        
        # 🔄 消息处理队列
        self.processing_queue = asyncio.Queue(maxsize=self.max_pending_messages)
        self.retry_queue = asyncio.Queue(maxsize=1000)
        
        # 📦 缓存管理
        self.message_cache = {}
        self.vehicle_cache = defaultdict(dict)
        self.last_sent_timestamps = defaultdict(float)
        
        # 🎯 采样过滤器
        self.vehicle_message_counts = defaultdict(int)
        self.sampling_counters = defaultdict(int)
        
    async def initialize(self, websocket_manager):
        """初始化缓存优化器"""
        # 避免重复初始化
        if self._initialized:
            logger.debug("缓存优化器已初始化，跳过重复初始化")
            return True
            
        try:
            # 连接Redis
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30,
                socket_keepalive=True
                # 移除socket_keepalive_options以避免类型错误
            )
            await self.redis_client.ping()
            
            self.websocket_manager = websocket_manager
            self.stats["start_time"] = time.time()
            
            # 创建优化后的消费者组
            await self._create_optimized_consumer_groups()
            
            # 设置初始化状态
            self._initialized = True
            logger.info("✅ Redis Stream缓存优化器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 缓存优化器初始化失败: {e}")
            # 打印更详细的错误信息，帮助诊断
            import traceback
            logger.debug(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    async def _create_optimized_consumer_groups(self):
        """创建优化的消费者组"""
        optimized_streams = {
            "fault_diagnosis_results": "optimized_fault_group",
            "vehicle_health_assessments": "optimized_health_group",
            "cached_messages": "cached_message_group"  # 新增缓存消息流
        }
        
        for stream_name, group_name in optimized_streams.items():
            try:
                await self.redis_client.xgroup_create(
                    stream_name, 
                    group_name, 
                    id="0", 
                    mkstream=True
                )
                logger.debug(f"🔧 创建优化消费者组: {stream_name} -> {group_name}")
            except Exception as e:
                if "BUSYGROUP" not in str(e):
                    logger.warning(f"创建消费者组失败 {stream_name}: {e}")

    async def start_optimized_monitoring(self):
        """启动优化的监控系统"""
        if not self.redis_client or not self.websocket_manager:
            logger.error("❌ 缓存优化器未初始化")
            return
            
        # 防止重复启动
        if self.is_running:
            logger.info("📊 缓存优化监控已在运行，跳过重复启动")
            return
            
        self.is_running = True
        logger.info("🚀 启动Redis Stream缓存优化监控...")
        
        # 启动多个优化任务
        tasks = [
            # 消息接收任务
            asyncio.create_task(self._optimized_message_receiver()),
            # 消息处理任务
            asyncio.create_task(self._optimized_message_processor()),
            # 重试处理任务
            asyncio.create_task(self._retry_processor()),
            # 缓存清理任务
            asyncio.create_task(self._cache_cleaner()),
            # 性能监控任务
            asyncio.create_task(self._performance_monitor())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"❌ 优化监控任务异常: {e}")
        finally:
            self.is_running = False

    async def _optimized_message_receiver(self):
        """优化的消息接收器 - 大批量读取"""
        consumer_id = "cache_optimizer_receiver"
        
        while self.is_running:
            try:
                # 🚀 大批量读取消息，提高吞吐量
                messages = await self.redis_client.xreadgroup(
                    "optimized_fault_group",
                    consumer_id,
                    {
                        "fault_diagnosis_results": ">",
                        "vehicle_health_assessments": ">"
                    },
                    count=50,  # 增加到50条
                    block=500   # 减少阻塞时间到500ms
                )
                
                for stream, msgs in messages:
                    for message_id, fields in msgs:
                        self.stats["total_received"] += 1
                        
                        # 🧠 智能过滤和采样
                        if await self._should_process_message(fields):
                            try:
                                # 非阻塞加入处理队列
                                self.processing_queue.put_nowait((stream, message_id, fields))
                            except asyncio.QueueFull:
                                # 队列满时，加入重试队列
                                try:
                                    self.retry_queue.put_nowait((stream, message_id, fields, time.time()))
                                    logger.warning("📦 处理队列已满，消息加入重试队列")
                                except asyncio.QueueFull:
                                    logger.error("❌ 重试队列也已满，丢弃消息")
                                    self.stats["error_count"] += 1
                        
                        # 确认消息处理
                        await self.redis_client.xack(stream, "optimized_fault_group", message_id)
                        
            except Exception as e:
                logger.error(f"❌ 优化消息接收失败: {e}")
                await asyncio.sleep(1)

    async def _should_process_message(self, fields: Dict) -> bool:
        """智能消息过滤和采样"""
        vehicle_id = fields.get("vehicle_id", "unknown")
        message_type = fields.get("message_type", "fault_diagnosis")
        
        # 🎯 增加消息计数
        self.vehicle_message_counts[vehicle_id] += 1
        self.sampling_counters[vehicle_id] += 1
        
        # 🚨 关键警报始终处理
        if self._is_critical_alert(fields):
            return True
        
        # 🔄 根据消息频率智能采样
        message_count = self.vehicle_message_counts[vehicle_id]
        sampling_rate = self._get_sampling_rate(message_count)
        
        # 采样决策
        if self.sampling_counters[vehicle_id] % int(1 / sampling_rate) == 0:
            self.stats["total_sampled"] += 1
            return True
        
        return False
    
    def _is_critical_alert(self, fields: Dict) -> bool:
        """判断是否为关键警报"""
        try:
            # 修复字符串转整数问题
            score_str = fields.get("score", "0")
            health_score_str = fields.get("health_score", "100")
            
            # 安全转换为浮点数
            score = float(score_str) if score_str and isinstance(score_str, (str, int, float)) else 0
            health_score = float(health_score_str) if health_score_str and isinstance(health_score_str, (str, int, float)) else 100
            
            # 严重故障或健康度过低
            if score > 80 or health_score < 30:
                return True
            
            # 状态为危险
            if fields.get("status") in ["danger", "critical", "fault"]:
                return True
                
        except (ValueError, TypeError) as e:
            logger.warning(f"解析警报数值失败: {e}, 原始值: score={fields.get('score')}, health_score={fields.get('health_score')}")
            
        return False
    
    def _get_sampling_rate(self, message_count: int) -> float:
        """根据消息频率获取采样率"""
        if message_count > 1000:  # 高频
            return self.sampling_rates["high_frequency"]
        elif message_count > 100:  # 中频
            return self.sampling_rates["medium_frequency"]
        else:  # 低频
            return self.sampling_rates["low_frequency"]

    async def _optimized_message_processor(self):
        """优化的消息处理器 - 批量处理"""
        batch = []
        last_process_time = time.time()
        
        while self.is_running:
            try:
                # 🚀 收集批量消息
                timeout = self.processing_interval
                try:
                    stream, message_id, fields = await asyncio.wait_for(
                        self.processing_queue.get(), timeout=timeout
                    )
                    batch.append((stream, message_id, fields))
                except asyncio.TimeoutError:
                    pass
                
                # 批量处理条件
                current_time = time.time()
                should_process = (
                    len(batch) >= self.max_batch_size or
                    (batch and current_time - last_process_time >= self.processing_interval)
                )
                
                if should_process and batch:
                    await self._process_message_batch(batch)
                    batch.clear()
                    last_process_time = current_time
                    
            except Exception as e:
                logger.error(f"❌ 优化消息处理失败: {e}")
                await asyncio.sleep(0.1)

    async def _process_message_batch(self, batch: List):
        """批量处理消息"""
        if not batch:
            return
            
        processed_count = 0
        frontend_messages = []
        
        for stream, message_id, fields in batch:
            try:
                # 🔧 处理消息并缓存
                processed_message = await self._process_and_cache_message(fields)
                if processed_message:
                    frontend_messages.append(processed_message)
                    processed_count += 1
                    
            except Exception as e:
                logger.error(f"❌ 处理单条消息失败: {e}")
                self.stats["error_count"] += 1
        
        # 🚀 批量发送到前端
        if frontend_messages:
            await self._batch_send_to_frontend(frontend_messages)
        
        self.stats["total_processed"] += processed_count
        logger.debug(f"📦 批量处理完成: {processed_count}/{len(batch)} 条消息")

    async def _process_and_cache_message(self, fields: Dict) -> Optional[Dict]:
        """处理消息并实现智能缓存"""
        vehicle_id = fields.get("vehicle_id", "unknown")
        
        # 🔄 检查缓存
        cache_key = f"{vehicle_id}:{fields.get('fault_type', 'unknown')}"
        cached_message = self.message_cache.get(cache_key)
        
        if cached_message:
            # 🎯 缓存命中，检查是否需要更新
            last_update = cached_message.get("timestamp", 0)
            current_time = time.time()
            
            if current_time - last_update < 1:  # 1秒内不重复发送
                self.stats["cache_hits"] += 1
                return None
        
        self.stats["cache_misses"] += 1
        
        # 🔧 构建优化后的消息
        try:
            # 修复字符串转整数问题
            score = fields.get("score", "0")
            health_score = fields.get("health_score", "100")
            
            # 安全转换为浮点数
            score_float = float(score) if score and isinstance(score, (str, int, float)) else 0
            health_score_float = float(health_score) if health_score and isinstance(health_score, (str, int, float)) else 100
            
            optimized_message = {
                "vehicle_id": vehicle_id,
                "fault_type": fields.get("fault_type", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "score": score_float,
                "health_score": health_score_float,
                "status": fields.get("status", "unknown"),
                "location": self._get_location_from_vehicle_id(vehicle_id),
                "processing_time": time.time(),
                "cache_optimized": True
            }
            
            # 📦 缓存消息
            self.message_cache[cache_key] = optimized_message.copy()
            self.stats["total_cached"] += 1
            
            # 🔄 更新车辆缓存
            self.vehicle_cache[vehicle_id].update({
                "last_update": time.time(),
                "message_count": self.vehicle_message_counts[vehicle_id],
                "last_score": optimized_message["score"],
                "last_health_score": optimized_message["health_score"]
            })
            
            return optimized_message
        except Exception as e:
            logger.error(f"❌ 处理消息格式失败: {e}, 原始字段: score={fields.get('score')}, health_score={fields.get('health_score')}")
            return None

    async def _batch_send_to_frontend(self, messages: List[Dict]):
        """批量发送消息到前端"""
        if not messages or not self.websocket_manager:
            return
            
        try:
            # 🚀 批量发送，减少WebSocket调用次数
            for message in messages:
                await self.websocket_manager.broadcast_to_frontends(message)
                
            logger.debug(f"📡 批量发送到前端: {len(messages)} 条消息")
            
        except Exception as e:
            logger.error(f"❌ 批量发送到前端失败: {e}")
            # 发送失败的消息加入重试队列
            for message in messages:
                try:
                    self.retry_queue.put_nowait(("frontend", None, message, time.time()))
                except asyncio.QueueFull:
                    logger.error("❌ 重试队列已满，无法重试发送")

    async def _retry_processor(self):
        """重试处理器"""
        while self.is_running:
            try:
                # 处理重试队列
                try:
                    stream, message_id, fields, retry_time = await asyncio.wait_for(
                        self.retry_queue.get(), timeout=1.0
                    )
                    
                    # 检查重试时间间隔
                    if time.time() - retry_time > 5:  # 5秒后重试
                        if stream == "frontend":
                            # 重试发送到前端
                            await self.websocket_manager.broadcast_to_frontends(fields)
                        else:
                            # 重试处理消息
                            processed_message = await self._process_and_cache_message(fields)
                            if processed_message:
                                await self._batch_send_to_frontend([processed_message])
                        
                        self.stats["retry_count"] += 1
                        logger.debug("🔄 消息重试成功")
                    else:
                        # 重新加入重试队列
                        self.retry_queue.put_nowait((stream, message_id, fields, retry_time))
                        
                except asyncio.TimeoutError:
                    continue
                    
            except Exception as e:
                logger.error(f"❌ 重试处理失败: {e}")
                await asyncio.sleep(1)

    async def _cache_cleaner(self):
        """缓存清理器"""
        while self.is_running:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次
                
                current_time = time.time()
                
                # 🧹 清理过期缓存
                expired_keys = []
                for key, message in self.message_cache.items():
                    if current_time - message.get("processing_time", 0) > self.cache_ttl:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.message_cache[key]
                
                # 🧹 清理车辆缓存
                expired_vehicles = []
                for vehicle_id, cache_data in self.vehicle_cache.items():
                    if current_time - cache_data.get("last_update", 0) > self.cache_ttl:
                        expired_vehicles.append(vehicle_id)
                
                for vehicle_id in expired_vehicles:
                    del self.vehicle_cache[vehicle_id]
                    if vehicle_id in self.vehicle_message_counts:
                        del self.vehicle_message_counts[vehicle_id]
                    if vehicle_id in self.sampling_counters:
                        del self.sampling_counters[vehicle_id]
                
                if expired_keys or expired_vehicles:
                    logger.info(f"🧹 缓存清理完成: 消息缓存-{len(expired_keys)}, 车辆缓存-{len(expired_vehicles)}")
                    
            except Exception as e:
                logger.error(f"❌ 缓存清理失败: {e}")

    async def _performance_monitor(self):
        """性能监控器"""
        while self.is_running:
            try:
                await asyncio.sleep(10)  # 每10秒统计一次
                
                current_time = time.time()
                if self.stats["start_time"]:
                    elapsed_time = current_time - self.stats["start_time"]
                    
                    # 计算性能指标
                    receive_rate = self.stats["total_received"] / elapsed_time
                    process_rate = self.stats["total_processed"] / elapsed_time
                    cache_hit_rate = (
                        self.stats["cache_hits"] / 
                        (self.stats["cache_hits"] + self.stats["cache_misses"])
                        if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0 else 0
                    )
                    
                    # 计算消息丢失率
                    total_input = self.stats["total_received"]
                    total_output = self.stats["total_processed"]
                    loss_rate = (
                        (total_input - total_output) / total_input 
                        if total_input > 0 else 0
                    )
                    
                    logger.info(
                        f"📊 缓存优化器性能统计:\n"
                        f"   📈 接收速率: {receive_rate:.1f} msg/s\n"
                        f"   ⚡ 处理速率: {process_rate:.1f} msg/s\n"
                        f"   💾 缓存命中率: {cache_hit_rate:.1%}\n"
                        f"   📉 消息丢失率: {loss_rate:.1%}\n"
                        f"   🔄 重试次数: {self.stats['retry_count']}\n"
                        f"   📦 缓存消息数: {len(self.message_cache)}\n"
                        f"   🚗 活跃车辆数: {len(self.vehicle_cache)}"
                    )
                    
            except Exception as e:
                logger.error(f"❌ 性能监控失败: {e}")

    def _get_location_from_vehicle_id(self, vehicle_id: str) -> str:
        """从车辆ID获取位置信息"""
        if not vehicle_id or vehicle_id == "unknown":
            return "未知位置"
        
        # 简化的位置映射
        if "粤B" in vehicle_id or "SEAL" in vehicle_id:
            return "深圳福田区"
        elif "陕A" in vehicle_id:
            return "西安高新区"
        else:
            return "未知位置"

    async def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.redis_client:
            await self.redis_client.close()
        
        # 清理缓存
        self.message_cache.clear()
        self.vehicle_cache.clear()
        
        logger.info("🛑 Redis Stream缓存优化器已停止")

    def get_optimizer_stats(self) -> Dict[str, Any]:
        """获取优化器统计信息"""
        current_time = time.time()
        elapsed_time = current_time - self.stats["start_time"] if self.stats["start_time"] else 0
        
        return {
            "is_running": self.is_running,
            "elapsed_time": elapsed_time,
            "total_received": self.stats["total_received"],
            "total_processed": self.stats["total_processed"],
            "total_cached": self.stats["total_cached"],
            "cache_hit_rate": (
                self.stats["cache_hits"] / 
                (self.stats["cache_hits"] + self.stats["cache_misses"])
                if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0 else 0
            ),
            "loss_rate": (
                (self.stats["total_received"] - self.stats["total_processed"]) / 
                self.stats["total_received"]
                if self.stats["total_received"] > 0 else 0
            ),
            "active_vehicles": len(self.vehicle_cache),
            "cached_messages": len(self.message_cache),
            "retry_count": self.stats["retry_count"],
            "error_count": self.stats["error_count"],
            "queue_sizes": {
                "processing": self.processing_queue.qsize(),
                "retry": self.retry_queue.qsize()
            }
        }

# 全局缓存优化器实例
stream_cache_optimizer = StreamCacheOptimizer() 