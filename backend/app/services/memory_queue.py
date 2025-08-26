"""
纯Python内存队列服务
无外部依赖的轻量级消息队列
"""
import asyncio
import json
import logging
from typing import Dict, Any, Callable, List
from datetime import datetime
from collections import defaultdict, deque
import threading

logger = logging.getLogger(__name__)

class MemoryQueue:
    def __init__(self, max_size: int = 10000):
        """初始化内存队列"""
        self.max_size = max_size
        self._queues = defaultdict(lambda: deque(maxlen=max_size))
        self._consumers = defaultdict(list)
        self._running = True
        self._lock = threading.Lock()
        self._stats = defaultdict(lambda: {'sent': 0, 'consumed': 0, 'errors': 0})
        
        logger.info(f"✅ 内存队列初始化完成，最大容量: {max_size}")

    async def send_message(self, topic: str, message: Dict[str, Any]) -> bool:
        """发送消息到队列"""
        try:
            message_data = {
                'id': f"{topic}_{datetime.now().timestamp()}",
                'timestamp': datetime.now().isoformat(),
                'topic': topic,
                'data': message
            }
            
            with self._lock:
                if len(self._queues[topic]) >= self.max_size:
                    # 队列满时，移除最老的消息
                    self._queues[topic].popleft()
                    logger.warning(f"⚠️  队列 {topic} 已满，移除最老消息")
                
                self._queues[topic].append(message_data)
                self._stats[topic]['sent'] += 1
            
            logger.debug(f"📤 消息已发送到内存队列 {topic}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 发送消息失败: {e}")
            self._stats[topic]['errors'] += 1
            return False

    def subscribe(self, topic: str, handler: Callable[[Dict], None]):
        """订阅主题"""
        with self._lock:
            self._consumers[topic].append(handler)
        logger.info(f"📢 订阅主题: {topic}")

    async def start_consuming(self):
        """开始消费所有队列的消息"""
        logger.info("🔄 开始消费内存队列消息...")
        
        while self._running:
            try:
                await self._process_all_queues()
                await asyncio.sleep(0.01)  # 10ms 检查间隔
            except Exception as e:
                logger.error(f"❌ 队列处理异常: {e}")
                await asyncio.sleep(1)

    async def _process_all_queues(self):
        """处理所有队列的消息"""
        for topic in list(self._queues.keys()):
            if self._queues[topic] and self._consumers[topic]:
                with self._lock:
                    if self._queues[topic]:
                        message = self._queues[topic].popleft()
                        handlers = self._consumers[topic].copy()
                
                # 处理消息
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(message['data'])
                        else:
                            handler(message['data'])
                        self._stats[topic]['consumed'] += 1
                    except Exception as e:
                        logger.error(f"❌ 消息处理失败: {e}")
                        self._stats[topic]['errors'] += 1

    def get_queue_length(self, topic: str) -> int:
        """获取队列长度"""
        with self._lock:
            return len(self._queues[topic])

    def get_stats(self, topic: str = None) -> Dict:
        """获取队列统计信息"""
        with self._lock:
            if topic:
                return dict(self._stats[topic])
            return {t: dict(stats) for t, stats in self._stats.items()}

    def clear_queue(self, topic: str):
        """清空指定队列"""
        with self._lock:
            self._queues[topic].clear()
            logger.info(f"🗑️  队列 {topic} 已清空")

    def stop(self):
        """停止队列服务"""
        self._running = False
        logger.info("🛑 内存队列服务已停止")

# 全局内存队列实例
memory_queue = MemoryQueue()

# 消息主题
class Topics:
    FAULT_DATA = 'fault_data'
    ANALYSIS_RESULTS = 'analysis_results'
    REAL_TIME_DIAGNOSIS = 'real_time_diagnosis'
    SYSTEM_STATUS = 'system_status' 