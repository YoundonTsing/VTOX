"""
VTOX 分布式工作节点 (Worker Node)

核心功能:
1. 独立故障分析处理 - 专注特定故障类型
2. 自动负载报告 - 实时向协调器汇报负载状态  
3. 健康监控自检 - 监控自身资源使用情况
4. 无缝集群集成 - 自动注册和故障转移

设计特点:
- 轻量级部署 - 可独立启动和停止
- 专业化处理 - 每个节点专注1-2种故障类型
- 弹性扩展 - 支持动态加入和退出集群
- 完全兼容 - 复用现有故障分析器代码
"""

import asyncio
import json
import logging
import time
import psutil
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import redis.asyncio as redis

from .service_registry import ServiceRegistry, ServiceClient, ServiceType, create_service_info
from ..redis_stream.distributed_diagnosis_stream import DistributedDiagnosisStream, FaultType

logger = logging.getLogger("worker-node")

@dataclass
class WorkerConfig:
    """Worker节点配置"""
    worker_id: str
    host: str
    port: int
    fault_types: List[str]  # 处理的故障类型
    max_concurrent_tasks: int = 10
    resource_monitoring: bool = True
    auto_scaling: bool = True
    redis_url: str = "redis://localhost:6379"

class ResourceMonitor:
    """资源监控器"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.system_stats = {
            "cpu_usage": 0.0,
            "memory_usage": 0.0, 
            "disk_usage": 0.0,
            "network_io": 0,
            "last_updated": time.time()
        }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统资源指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 进程资源使用
            process_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            process_cpu = self.process.cpu_percent()
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 网络IO
            network = psutil.net_io_counters()
            network_total = network.bytes_sent + network.bytes_recv
            
            metrics = {
                "system_cpu_usage": cpu_percent,
                "system_memory_usage": memory_percent,
                "system_disk_usage": disk_percent,
                "process_memory_mb": process_memory,
                "process_cpu_usage": process_cpu,
                "network_io_bytes": network_total,
                "timestamp": time.time(),
                "healthy": self._calculate_health_status(cpu_percent, memory_percent)
            }
            
            self.system_stats.update(metrics)
            return metrics
            
        except Exception as e:
            logger.error(f"❌ 获取系统指标失败: {e}")
            return {
                "system_cpu_usage": 0,
                "system_memory_usage": 0,
                "healthy": False,
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _calculate_health_status(self, cpu_usage: float, memory_usage: float) -> bool:
        """计算健康状态"""
        # 简单健康检查：CPU < 90% 且 内存 < 85%
        return cpu_usage < 90 and memory_usage < 85

class WorkerLoadReporter:
    """Worker负载报告器"""
    
    def __init__(self, redis_client: redis.Redis, worker_id: str):
        self.redis = redis_client
        self.worker_id = worker_id
        self.load_key = "vtox:coordinator:worker_loads"
        
        # 负载统计
        self.load_stats = {
            "current_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "total_processing_time": 0,
            "start_time": time.time(),
            "last_report_time": time.time()
        }
        
        # 任务队列监控
        self.pending_messages = 0
        self.processing_times = []  # 保留最近100次处理时间
        
    async def report_load(self, resource_metrics: Dict[str, Any]):
        """报告负载状态到协调器"""
        try:
            current_time = time.time()
            
            # 计算平均处理时间
            avg_processing_time = (
                sum(self.processing_times) / len(self.processing_times)
                if self.processing_times else 100.0
            )
            
            # 计算成功率
            total_tasks = self.load_stats["completed_tasks"] + self.load_stats["failed_tasks"]
            success_rate = (
                self.load_stats["completed_tasks"] / total_tasks
                if total_tasks > 0 else 1.0
            )
            
            # 构建负载报告
            load_report = {
                "worker_id": self.worker_id,
                "current_tasks": self.load_stats["current_tasks"],
                "pending_messages": self.pending_messages,
                "avg_processing_time": avg_processing_time,
                "cpu_usage": resource_metrics.get("system_cpu_usage", 0),
                "memory_usage": resource_metrics.get("system_memory_usage", 0),
                "success_rate": success_rate,
                "total_completed": self.load_stats["completed_tasks"],
                "total_failed": self.load_stats["failed_tasks"],
                "uptime": current_time - self.load_stats["start_time"],
                "last_updated": current_time,
                "healthy": resource_metrics.get("healthy", True)
            }
            
            # 发送到Redis
            await self.redis.hset(
                self.load_key,
                self.worker_id,
                json.dumps(load_report)
            )
            
            self.load_stats["last_report_time"] = current_time
            
            logger.debug(f"📊 负载报告已发送: 任务{self.load_stats['current_tasks']} "
                        f"CPU{resource_metrics.get('system_cpu_usage', 0):.1f}% "
                        f"内存{resource_metrics.get('system_memory_usage', 0):.1f}%")
            
        except Exception as e:
            logger.error(f"❌ 发送负载报告失败: {e}")
    
    def start_task(self):
        """开始处理任务"""
        self.load_stats["current_tasks"] += 1
    
    def finish_task(self, processing_time: float, success: bool = True):
        """完成任务处理"""
        self.load_stats["current_tasks"] = max(0, self.load_stats["current_tasks"] - 1)
        
        if success:
            self.load_stats["completed_tasks"] += 1
        else:
            self.load_stats["failed_tasks"] += 1
        
        # 记录处理时间
        self.processing_times.append(processing_time)
        if len(self.processing_times) > 100:
            self.processing_times.pop(0)
        
        self.load_stats["total_processing_time"] += processing_time
    
    def update_pending_messages(self, count: int):
        """更新待处理消息数"""
        self.pending_messages = count

class DistributedWorkerNode:
    """分布式工作节点"""
    
    def __init__(self, config: WorkerConfig):
        self.config = config
        self.redis_client = None
        self.service_client: Optional[ServiceClient] = None
        
        # 核心组件
        self.diagnosis_stream: Optional[DistributedDiagnosisStream] = None
        self.resource_monitor = ResourceMonitor()
        self.load_reporter: Optional[WorkerLoadReporter] = None
        
        # 运行状态
        self.is_running = False
        self.worker_tasks = []
        
        # 故障类型映射
        self.fault_type_mapping = {
            "turn_fault": FaultType.TURN_FAULT,
            "insulation": FaultType.INSULATION,
            "bearing": FaultType.BEARING, 
            "eccentricity": FaultType.ECCENTRICITY,
            "broken_bar": FaultType.BROKEN_BAR
        }
    
    async def initialize(self) -> bool:
        """初始化Worker节点"""
        try:
            # 连接Redis
            self.redis_client = redis.from_url(
                self.config.redis_url,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30
            )
            await self.redis_client.ping()
            
            # 初始化分布式诊断系统
            self.diagnosis_stream = DistributedDiagnosisStream(self.config.redis_url)
            await self.diagnosis_stream.connect()
            
            # 初始化负载报告器
            self.load_reporter = WorkerLoadReporter(self.redis_client, self.config.worker_id)
            
            # 注册为服务
            await self._register_service()
            
            logger.info(f"✅ Worker节点初始化成功: {self.config.worker_id}")
            logger.info(f"   🎯 处理故障类型: {self.config.fault_types}")
            logger.info(f"   📍 服务地址: {self.config.host}:{self.config.port}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Worker节点初始化失败: {e}")
            return False
    
    async def _register_service(self):
        """注册为集群服务"""
        try:
            from .service_registry import get_service_registry
            
            # 获取服务注册表
            registry = await get_service_registry(self.redis_client)
            
            # 创建服务信息
            service_info = create_service_info(
                ServiceType.WORKER,
                f"VTOX Worker - {','.join(self.config.fault_types)}",
                self.config.host,
                self.config.port,
                self.config.fault_types,
                {
                    "worker_id": self.config.worker_id,
                    "max_concurrent_tasks": self.config.max_concurrent_tasks,
                    "resource_monitoring": self.config.resource_monitoring,
                    "auto_scaling": self.config.auto_scaling
                }
            )
            
            # 创建服务客户端
            self.service_client = ServiceClient(registry, service_info)
            await self.service_client.start()
            
            logger.info(f"🏷️ 服务注册成功: {service_info.service_id}")
            
        except Exception as e:
            logger.error(f"❌ 服务注册失败: {e}")
            raise
    
    async def start_worker(self) -> bool:
        """启动Worker节点"""
        try:
            if self.is_running:
                logger.warning("⚠️ Worker节点已在运行中")
                return True
            
            self.is_running = True
            
            # 启动各种工作任务
            self.worker_tasks = [
                asyncio.create_task(self._fault_processing_loop()),
                asyncio.create_task(self._resource_monitoring_loop()),
                asyncio.create_task(self._load_reporting_loop()),
                asyncio.create_task(self._health_check_loop())
            ]
            
            logger.info(f"🚀 Worker节点启动成功: {self.config.worker_id}")
            logger.info("   🔧 故障处理: 启动")
            logger.info("   📊 资源监控: 启动") 
            logger.info("   📈 负载报告: 启动")
            logger.info("   💓 健康检查: 启动")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动Worker节点失败: {e}")
            return False
    
    async def stop_worker(self):
        """停止Worker节点"""
        try:
            self.is_running = False
            
            # 取消所有工作任务
            for task in self.worker_tasks:
                if not task.done():
                    task.cancel()
            
            # 等待任务完成
            if self.worker_tasks:
                await asyncio.gather(*self.worker_tasks, return_exceptions=True)
            
            # 注销服务
            if self.service_client:
                await self.service_client.stop()
            
            # 清理Redis连接
            if self.redis_client:
                await self.redis_client.close()
            
            logger.info(f"🛑 Worker节点已停止: {self.config.worker_id}")
            
        except Exception as e:
            logger.error(f"❌ 停止Worker节点失败: {e}")
    
    async def _fault_processing_loop(self):
        """故障处理循环"""
        logger.info("🔧 启动故障处理循环")
        
        # 存储消费者任务
        consumer_tasks = []
        
        try:
            # 为每种故障类型启动专门的消费者（只启动一次）
            for fault_type_str in self.config.fault_types:
                if fault_type_str in self.fault_type_mapping:
                    fault_type = self.fault_type_mapping[fault_type_str]
                    
                    # 启动故障诊断消费者 (复用现有架构)
                    consumer_id = f"{self.config.worker_id}_{fault_type_str}_consumer"
                    
                    # 创建消费者任务
                    consumer_task = asyncio.create_task(
                        self._run_fault_consumer(fault_type, consumer_id)
                    )
                    consumer_tasks.append(consumer_task)
                    logger.debug(f"✅ 启动消费者: {consumer_id}")
            
            logger.info(f"✅ 已启动{len(consumer_tasks)}个故障消费者")
            
            # 监控消费者任务状态
            while self.is_running:
                # 检查是否有任务异常结束
                for i, task in enumerate(consumer_tasks[:]):
                    if task.done():
                        fault_type_str = self.config.fault_types[i % len(self.config.fault_types)]
                        logger.warning(f"⚠️ 消费者任务异常结束: {fault_type_str}")
                        
                        # 重新启动异常结束的消费者
                        if fault_type_str in self.fault_type_mapping:
                            fault_type = self.fault_type_mapping[fault_type_str]
                            consumer_id = f"{self.config.worker_id}_{fault_type_str}_consumer"
                            
                            new_task = asyncio.create_task(
                                self._run_fault_consumer(fault_type, consumer_id)
                            )
                            consumer_tasks[i] = new_task
                            logger.info(f"🔄 重新启动消费者: {consumer_id}")
                
                # 等待60秒后再次检查
                await asyncio.sleep(60)
                
        except asyncio.CancelledError:
            logger.info("🛑 故障处理循环被取消")
            # 取消所有消费者任务
            for task in consumer_tasks:
                if not task.done():
                    task.cancel()
        except Exception as e:
            logger.error(f"❌ 故障处理循环异常: {e}")
            # 取消所有消费者任务
            for task in consumer_tasks:
                if not task.done():
                    task.cancel()
    
    async def _run_fault_consumer(self, fault_type: FaultType, consumer_id: str):
        """运行故障消费者"""
        try:
            while self.is_running:
                start_time = time.time()
                
                # 开始处理任务
                self.load_reporter.start_task()
                
                try:
                    # 调用现有的故障诊断消费者 (保持兼容性)
                    await self.diagnosis_stream.start_fault_diagnosis_consumer(
                        fault_type, consumer_id
                    )
                    
                    # 处理成功
                    processing_time = time.time() - start_time
                    self.load_reporter.finish_task(processing_time, success=True)
                    
                except Exception as e:
                    # 处理失败
                    processing_time = time.time() - start_time
                    self.load_reporter.finish_task(processing_time, success=False)
                    logger.error(f"❌ 故障处理失败: {fault_type.value} - {e}")
                    
                    # 短暂休息后重试
                    await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info(f"🛑 故障消费者停止: {consumer_id}")
        except Exception as e:
            logger.error(f"❌ 故障消费者异常: {consumer_id} - {e}")
    
    async def _resource_monitoring_loop(self):
        """资源监控循环"""
        logger.info("📊 启动资源监控循环")
        
        while self.is_running:
            try:
                if self.config.resource_monitoring:
                    # 获取系统资源指标
                    metrics = self.resource_monitor.get_system_metrics()
                    
                    # 更新服务元数据
                    if self.service_client:
                        self.service_client.update_metadata({
                            "cpu_usage": metrics.get("system_cpu_usage", 0),
                            "memory_usage": metrics.get("system_memory_usage", 0),
                            "healthy": metrics.get("healthy", True),
                            "last_updated": metrics.get("timestamp", time.time())
                        })
                    
                    # 检查资源使用是否过高
                    if metrics.get("system_cpu_usage", 0) > 90:
                        logger.warning(f"⚠️ CPU使用率过高: {metrics['system_cpu_usage']:.1f}%")
                    
                    if metrics.get("system_memory_usage", 0) > 85:
                        logger.warning(f"⚠️ 内存使用率过高: {metrics['system_memory_usage']:.1f}%")
                
                await asyncio.sleep(10)  # 每10秒监控一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 资源监控异常: {e}")
                await asyncio.sleep(5)
    
    async def _load_reporting_loop(self):
        """负载报告循环"""
        logger.info("📈 启动负载报告循环")
        
        while self.is_running:
            try:
                # 获取资源指标
                resource_metrics = self.resource_monitor.get_system_metrics()
                
                # 更新待处理消息数 (从Redis Stream获取)
                await self._update_pending_messages()
                
                # 发送负载报告
                await self.load_reporter.report_load(resource_metrics)
                
                await asyncio.sleep(15)  # 每15秒报告一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 负载报告异常: {e}")
                await asyncio.sleep(5)
    
    async def _update_pending_messages(self):
        """更新待处理消息数量"""
        try:
            total_pending = 0
            
            # 检查每个故障类型的消费者组待处理消息
            for fault_type_str in self.config.fault_types:
                if fault_type_str in self.fault_type_mapping:
                    group_name = f"{fault_type_str}_diagnosis_group"
                    
                    try:
                        # 获取消费者组信息 (需要Redis Stream支持)
                        # 这里先使用模拟数据，实际需要从Redis Stream获取
                        pending_count = await self._get_consumer_group_pending(group_name)
                        total_pending += pending_count
                        
                    except Exception as e:
                        logger.debug(f"获取{group_name}待处理消息失败: {e}")
            
            self.load_reporter.update_pending_messages(total_pending)
            
        except Exception as e:
            logger.error(f"❌ 更新待处理消息数失败: {e}")
    
    async def _get_consumer_group_pending(self, group_name: str) -> int:
        """获取消费者组待处理消息数"""
        try:
            # 使用XPENDING命令获取待处理消息数
            pending_info = await self.redis_client.xpending(
                "motor_raw_data",  # Stream名称
                group_name
            )
            
            if pending_info:
                return pending_info[0]  # 总待处理消息数
            
            return 0
            
        except Exception as e:
            logger.debug(f"获取消费者组待处理消息失败: {group_name} - {e}")
            return 0
    
    async def _health_check_loop(self):
        """健康检查循环"""
        logger.info("💓 启动健康检查循环")
        
        while self.is_running:
            try:
                # 检查Redis连接
                await self.redis_client.ping()
                
                # 检查诊断系统连接
                if self.diagnosis_stream and self.diagnosis_stream.redis_client:
                    await self.diagnosis_stream.redis_client.ping()
                
                # 检查资源状态
                metrics = self.resource_monitor.get_system_metrics()
                if not metrics.get("healthy", True):
                    logger.warning("⚠️ Worker节点资源状态不健康")
                
                await asyncio.sleep(30)  # 每30秒检查一次
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 健康检查失败: {e}")
                await asyncio.sleep(10)
    
    async def get_worker_stats(self) -> Dict[str, Any]:
        """获取Worker统计信息"""
        try:
            current_time = time.time()
            uptime = current_time - self.load_reporter.load_stats["start_time"]
            
            # 获取资源指标
            resource_metrics = self.resource_monitor.get_system_metrics()
            
            # 获取负载统计
            load_stats = self.load_reporter.load_stats
            
            return {
                "worker_id": self.config.worker_id,
                "status": "running" if self.is_running else "stopped",
                "uptime_seconds": uptime,
                "fault_types": self.config.fault_types,
                "current_tasks": load_stats["current_tasks"],
                "completed_tasks": load_stats["completed_tasks"],
                "failed_tasks": load_stats["failed_tasks"],
                "pending_messages": self.load_reporter.pending_messages,
                "resource_metrics": resource_metrics,
                "service_registered": self.service_client is not None,
                "timestamp": current_time
            }
            
        except Exception as e:
            logger.error(f"❌ 获取Worker统计失败: {e}")
            return {"error": str(e)}


# 便捷函数
def create_worker_config(worker_id: str, host: str, port: int, 
                        fault_types: List[str], **kwargs) -> WorkerConfig:
    """创建Worker配置"""
    return WorkerConfig(
        worker_id=worker_id,
        host=host,
        port=port,
        fault_types=fault_types,
        **kwargs
    )

async def start_worker_node(config: WorkerConfig) -> DistributedWorkerNode:
    """启动Worker节点"""
    worker = DistributedWorkerNode(config)
    
    if await worker.initialize():
        if await worker.start_worker():
            return worker
        else:
            raise Exception("启动Worker失败")
    else:
        raise Exception("初始化Worker失败")