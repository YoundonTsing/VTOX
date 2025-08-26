"""
简单内存队列服务
完全不依赖Redis、Kafka等外部服务的纯Python实现
"""
import asyncio
import logging
from typing import Dict, Any, Callable, List
from collections import deque
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class SimpleQueue:
    """简单的内存队列，专注于故障诊断数据处理"""
    
    def __init__(self):
        # 内存队列存储
        self.queues = {
            'fault_data': deque(maxlen=1000),
            'analysis_results': deque(maxlen=1000)
        }
        
        # 消息处理器
        self.handlers = {}
        
        # 统计信息
        self.stats = {
            'total_sent': 0,
            'total_processed': 0,
            'queue_lengths': {},
            'start_time': datetime.now()
        }
        
        # 消费任务
        self.consumer_tasks = []
        self.is_running = False
        
        logger.info("✅ 简单内存队列服务初始化完成")

    async def send_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """发送消息到队列"""
        try:
            if topic not in self.queues:
                logger.warning(f"⚠️  未知队列主题: {topic}")
                return False
            
            # 添加时间戳
            enriched_message = {
                'timestamp': datetime.now().isoformat(),
                'data': message
            }
            
            self.queues[topic].append(enriched_message)
            self.stats['total_sent'] += 1
            
            logger.debug(f"📤 消息已发送到队列 {topic}, 当前长度: {len(self.queues[topic])}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 发送消息失败: {e}")
            return False

    def subscribe(self, topic: str, handler: Callable):
        """订阅队列主题"""
        if topic not in self.queues:
            logger.warning(f"⚠️  未知队列主题: {topic}")
            return
        
        self.handlers[topic] = handler
        logger.info(f"📬 已订阅队列主题: {topic}")

    async def start_consuming(self):
        """开始消费所有队列"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("🔄 开始消费队列...")
        
        # 为每个队列启动消费任务
        for topic in self.queues.keys():
            if topic in self.handlers:
                task = asyncio.create_task(self._consume_queue(topic))
                self.consumer_tasks.append(task)
                logger.info(f"🎯 队列 {topic} 消费者已启动")

    async def _consume_queue(self, topic: str):
        """消费指定队列的消息"""
        handler = self.handlers.get(topic)
        if not handler:
            return
        
        while self.is_running:
            try:
                queue = self.queues[topic]
                if queue:
                    message = queue.popleft()
                    
                    # 调用处理器
                    if asyncio.iscoroutinefunction(handler):
                        await handler(message['data'])
                    else:
                        handler(message['data'])
                    
                    self.stats['total_processed'] += 1
                    logger.debug(f"✅ 处理了来自 {topic} 的消息")
                else:
                    # 队列为空，短暂休眠
                    await asyncio.sleep(0.01)
                    
            except Exception as e:
                logger.error(f"❌ 处理队列 {topic} 消息时出错: {e}")
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
        
        self.consumer_tasks.clear()
        logger.info("🛑 队列消费已停止")

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        # 更新队列长度统计
        for topic, queue in self.queues.items():
            self.stats['queue_lengths'][topic] = len(queue)
        
        return {
            'type': 'simple_memory_queue',
            'running': self.is_running,
            'uptime_seconds': (datetime.now() - self.stats['start_time']).total_seconds(),
            'total_sent': self.stats['total_sent'],
            'total_processed': self.stats['total_processed'],
            'queue_lengths': self.stats['queue_lengths'],
            'handlers_count': len(self.handlers)
        }

    def clear_queue(self, topic: str):
        """清空指定队列"""
        if topic in self.queues:
            self.queues[topic].clear()
            logger.info(f"🗑️  队列 {topic} 已清空")

    def get_queue_length(self, topic: str) -> int:
        """获取队列长度"""
        return len(self.queues.get(topic, []))

# 全局队列实例
simple_queue = SimpleQueue()

# 主题常量
TOPICS = {
    'FAULT_DATA': 'fault_data',
    'ANALYSIS_RESULTS': 'analysis_results'
} 