import asyncio
import logging
from typing import Dict, Any, Callable, List
import json
from datetime import datetime
import redis.asyncio as redis
from ..simple_queue import TOPICS

logger = logging.getLogger(__name__)

class RedisQueue:
    """基于Redis的队列服务，保持与SimpleQueue相似的接口"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """初始化Redis队列"""
        self.redis_url = redis_url
        self.redis_client = None
        self.handlers = {}
        self.consumer_tasks = []
        self.is_running = False
        self.connection_retry_count = 0
        self.max_connection_retries = 5
        self.connection_retry_delay = 2  # 秒
        
        # 统计信息
        self.stats = {
            'total_sent': 0,
            'total_processed': 0,
            'total_errors': 0,
            'connection_retries': 0,
            'queue_lengths': {},
            'start_time': datetime.now()
        }
        
        logger.info(f"✅ Redis队列服务初始化完成，连接地址: {redis_url}")

    async def connect(self):
        """建立Redis连接，带重试机制"""
        retry_count = 0
        while retry_count < self.max_connection_retries:
            try:
                self.redis_client = redis.from_url(
                    self.redis_url, 
                    decode_responses=True,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                await self.redis_client.ping()
                logger.info("✅ Redis连接成功")
                self.connection_retry_count = 0  # 重置重试计数
                return True
            except Exception as e:
                retry_count += 1
                self.connection_retry_count += 1
                self.stats['connection_retries'] += 1
                logger.warning(f"⚠️  Redis连接失败 (尝试 {retry_count}/{self.max_connection_retries}): {e}")
                
                if retry_count < self.max_connection_retries:
                    await asyncio.sleep(self.connection_retry_delay * retry_count)  # 指数退避
                else:
                    logger.error(f"❌ Redis连接最终失败，已尝试 {retry_count} 次")
                    return False

    async def send_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """发送消息到Redis队列"""
        try:
            if not self.redis_client:
                logger.warning("⚠️  Redis客户端未初始化")
                # 尝试重新连接
                if not await self.connect():
                    return False
            
            # 添加时间戳和元数据
            enriched_message = {
                'timestamp': datetime.now().isoformat(),
                'data': message
            }
            
            # 将消息推送到Redis列表
            queue_key = f"queue:{topic}"
            await self.redis_client.lpush(queue_key, json.dumps(enriched_message))
            
            self.stats['total_sent'] += 1
            logger.debug(f"📤 消息已发送到Redis队列 {topic}")
            return True
            
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis连接错误: {e}")
            # 尝试重新连接
            if await self.connect():
                # 重新尝试发送消息
                try:
                    queue_key = f"queue:{topic}"
                    await self.redis_client.lpush(queue_key, json.dumps(enriched_message))
                    self.stats['total_sent'] += 1
                    logger.debug(f"📤 消息已重新发送到Redis队列 {topic}")
                    return True
                except Exception as retry_error:
                    logger.error(f"❌ 重新发送消息失败: {retry_error}")
            self.stats['total_errors'] += 1
            return False
        except Exception as e:
            logger.error(f"❌ 发送消息失败: {e}")
            self.stats['total_errors'] += 1
            return False

    def subscribe(self, topic: str, handler: Callable):
        """订阅队列主题"""
        self.handlers[topic] = handler
        logger.info(f"📬 已订阅队列主题: {topic}")

    async def start_consuming(self):
        """开始消费所有队列"""
        if self.is_running:
            return
        
        if not self.redis_client:
            logger.warning("⚠️  Redis客户端未初始化")
            return
            
        self.is_running = True
        logger.info("🔄 开始消费Redis队列...")
        
        # 为每个订阅的主题启动消费任务
        for topic in self.handlers.keys():
            task = asyncio.create_task(self._consume_queue(topic))
            self.consumer_tasks.append(task)
            logger.info(f"🎯 Redis队列 {topic} 消费者已启动")

    async def _consume_queue(self, topic: str):
        """消费指定队列的消息"""
        handler = self.handlers.get(topic)
        if not handler:
            return
        
        queue_key = f"queue:{topic}"
        
        while self.is_running:
            try:
                # 检查连接状态
                if not self.redis_client:
                    logger.warning("⚠️  Redis客户端未连接，尝试重新连接...")
                    if not await self.connect():
                        await asyncio.sleep(1)
                        continue
                
                # 从Redis队列中阻塞式获取消息
                result = await self.redis_client.brpop(queue_key, timeout=1)
                
                if result:
                    # 解析消息
                    _, message_json = result
                    message = json.loads(message_json)
                    
                    # 调用处理器
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(message['data'])
                        else:
                            handler(message['data'])
                        
                        self.stats['total_processed'] += 1
                        logger.debug(f"✅ 处理了来自 {topic} 的消息")
                    except Exception as e:
                        logger.error(f"❌ 处理消息时出错: {e}")
                        self.stats['total_errors'] += 1
                else:
                    # 超时，继续循环
                    await asyncio.sleep(0.01)
                    
            except redis.ConnectionError as e:
                logger.error(f"❌ Redis连接错误: {e}")
                # 尝试重新连接
                await self.connect()
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"❌ 处理Redis队列 {topic} 消息时出错: {e}")
                await asyncio.sleep(0.1)

    async def stop(self):
        """停止消费"""
        self.is_running = False
        
        # 取消所有消费任务
        for task in self.consumer_tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # 关闭Redis连接
        if self.redis_client:
            await self.redis_client.close()
            
        self.consumer_tasks.clear()
        logger.info("🛑 Redis队列消费已停止")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            # 更新队列长度统计
            for topic in self.handlers.keys():
                queue_key = f"queue:{topic}"
                if self.redis_client:
                    queue_length = self.redis_client.llen(queue_key)
                    self.stats['queue_lengths'][topic] = queue_length
        except Exception as e:
            logger.error(f"获取队列长度时出错: {e}")
        
        return {
            'type': 'redis_queue',
            'running': self.is_running,
            'uptime_seconds': (datetime.now() - self.stats['start_time']).total_seconds(),
            'total_sent': self.stats['total_sent'],
            'total_processed': self.stats['total_processed'],
            'total_errors': self.stats['total_errors'],
            'connection_retries': self.stats['connection_retries'],
            'queue_lengths': self.stats['queue_lengths'],
            'handlers_count': len(self.handlers)
        }

    async def clear_queue(self, topic: str):
        """清空指定队列"""
        try:
            if not self.redis_client:
                logger.warning("⚠️  Redis客户端未初始化")
                return
                
            queue_key = f"queue:{topic}"
            await self.redis_client.delete(queue_key)
            logger.info(f"🗑️  Redis队列 {topic} 已清空")
        except Exception as e:
            logger.error(f"清空队列 {topic} 时出错: {e}")

    async def get_queue_length(self, topic: str) -> int:
        """获取队列长度"""
        try:
            if not self.redis_client:
                logger.warning("⚠️  Redis客户端未初始化")
                return 0
                
            queue_key = f"queue:{topic}"
            return await self.redis_client.llen(queue_key)
        except Exception as e:
            logger.error(f"获取队列 {topic} 长度时出错: {e}")
            return 0

# 全局Redis队列实例
redis_queue = RedisQueue()

# 保持与TOPICS常量的兼容性
REDIS_TOPICS = TOPICS