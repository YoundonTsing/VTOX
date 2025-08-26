"""
VTOX 分布式诊断协调器

核心功能:
1. 智能任务分发 - 基于Worker能力和负载状态
2. 动态负载均衡 - 实时调整任务分配策略
3. 故障转移处理 - Worker节点故障时自动重新分配
4. 性能监控统计 - 收集和分析系统性能指标
"""

import asyncio
import json
import logging
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import redis.asyncio as redis
from collections import defaultdict, deque

from .service_registry import ServiceRegistry, ServiceType, ServiceStatus, get_service_registry

logger = logging.getLogger("diagnosis-coordinator")

class TaskPriority(Enum):
    """任务优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class LoadBalanceStrategy(Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections" 
    SMART_PREDICTION = "smart_prediction"

@dataclass
class TaskInfo:
    """任务信息"""
    task_id: str
    fault_type: str
    vehicle_id: str
    priority: TaskPriority
    data_size: int
    estimated_processing_time: float
    created_at: float
    assigned_worker: Optional[str] = None

@dataclass 
class WorkerLoad:
    """Worker负载信息"""
    worker_id: str
    service_name: str
    host: str
    port: int
    capabilities: List[str]
    current_tasks: int
    pending_messages: int
    avg_processing_time: float
    cpu_usage: float
    memory_usage: float
    success_rate: float
    last_updated: float
    health_score: float = 1.0

class IntelligentLoadBalancer:
    """智能负载均衡器"""
    
    def __init__(self):
        self.strategy = LoadBalanceStrategy.SMART_PREDICTION
        self.performance_weights = {
            "response_time": 0.3,
            "success_rate": 0.25, 
            "cpu_usage": 0.2,
            "memory_usage": 0.15,
            "queue_length": 0.1
        }
    
    def calculate_worker_score(self, worker_load: WorkerLoad, task_info: TaskInfo) -> float:
        """计算Worker适合度评分"""
        try:
            # 基础能力检查
            if task_info.fault_type not in worker_load.capabilities:
                return 0.0
            
            # 健康状态检查
            if worker_load.health_score < 0.5:
                return 0.0
            
            # 多维度评分
            scores = {}
            
            # 1. 响应时间评分 (越低越好)
            normalized_time = min(worker_load.avg_processing_time / 1000.0, 1.0)
            scores["response_time"] = 1.0 - normalized_time
            
            # 2. 成功率评分
            scores["success_rate"] = worker_load.success_rate
            
            # 3. CPU使用率评分 (越低越好)  
            scores["cpu_usage"] = 1.0 - min(worker_load.cpu_usage / 100.0, 1.0)
            
            # 4. 内存使用率评分 (越低越好)
            scores["memory_usage"] = 1.0 - min(worker_load.memory_usage / 100.0, 1.0)
            
            # 5. 队列长度评分 (越短越好)
            max_queue = 100
            normalized_queue = min(worker_load.pending_messages / max_queue, 1.0)
            scores["queue_length"] = 1.0 - normalized_queue
            
            # 加权综合评分
            total_score = sum(
                scores[metric] * weight 
                for metric, weight in self.performance_weights.items()
            )
            
            # 应用健康状态权重
            final_score = total_score * worker_load.health_score
            return final_score
            
        except Exception as e:
            logger.error(f"❌ 计算Worker评分失败: {e}")
            return 0.0
    
    def select_best_worker(self, available_workers: List[WorkerLoad],
                          task_info: TaskInfo) -> Optional[WorkerLoad]:
        """选择最佳Worker"""
        if not available_workers:
            return None
        
        try:
            # 过滤有能力处理该故障类型的Worker
            capable_workers = [
                worker for worker in available_workers
                if task_info.fault_type in worker.capabilities
            ]
            
            if not capable_workers:
                logger.warning(f"⚠️ 没有Worker能处理故障类型: {task_info.fault_type}")
                return None
            
            if self.strategy == LoadBalanceStrategy.SMART_PREDICTION:
                # 智能预测策略
                worker_scores = []
                for worker in capable_workers:
                    score = self.calculate_worker_score(worker, task_info)
                    worker_scores.append((worker, score))
                
                # 选择评分最高的Worker
                best_worker = max(worker_scores, key=lambda x: x[1])
                logger.debug(f"🎯 选择Worker: {best_worker[0].service_name} (评分: {best_worker[1]:.3f})")
                return best_worker[0]
            
            elif self.strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
                return min(capable_workers, key=lambda w: w.current_tasks)
            
            else:
                return random.choice(capable_workers)
                
        except Exception as e:
            logger.error(f"❌ 选择Worker失败: {e}")
            return random.choice(capable_workers) if capable_workers else None

class DiagnosisCoordinator:
    """分布式诊断协调器"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.registry: Optional[ServiceRegistry] = None
        self.load_balancer = IntelligentLoadBalancer()
        
        # Redis键定义
        self.task_queue_key = "vtox:coordinator:tasks"
        self.worker_loads_key = "vtox:coordinator:worker_loads"
        self.assignments_key = "vtox:coordinator:assignments"
        
        # 协调器状态
        self.is_running = False
        self.coordination_tasks = []
        
        # 性能统计
        self.stats = {
            "tasks_assigned": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_assignment_time": 0,
            "start_time": None
        }
    
    async def initialize(self) -> bool:
        """初始化协调器"""
        try:
            self.registry = await get_service_registry(self.redis)
            self.registry.add_event_listener("service_registered", self._on_service_registered)
            self.registry.add_event_listener("service_deregistered", self._on_service_deregistered)
            
            logger.info("✅ 诊断协调器初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 协调器初始化失败: {e}")
            return False
    
    async def start_coordination(self) -> bool:
        """启动协调服务"""
        try:
            if self.is_running:
                return True
            
            self.is_running = True
            self.stats["start_time"] = time.time()
            
            # 启动监控任务
            self.coordination_tasks = [
                asyncio.create_task(self._task_assignment_loop()),
                asyncio.create_task(self._worker_monitoring_loop()),
                asyncio.create_task(self._performance_monitoring_loop())
            ]
            
            logger.info("🚀 分布式诊断协调器启动成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动协调器失败: {e}")
            return False
    
    async def stop_coordination(self):
        """停止协调服务"""
        try:
            self.is_running = False
            
            for task in self.coordination_tasks:
                if not task.done():
                    task.cancel()
            
            if self.coordination_tasks:
                await asyncio.gather(*self.coordination_tasks, return_exceptions=True)
            
            logger.info("🛑 分布式诊断协调器已停止")
            
        except Exception as e:
            logger.error(f"❌ 停止协调器失败: {e}")
    
    async def submit_task(self, fault_type: str, vehicle_id: str,
                         message_data: Dict[str, Any],
                         priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """提交诊断任务"""
        try:
            task_id = f"task_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
            
            task_info = TaskInfo(
                task_id=task_id,
                fault_type=fault_type,
                vehicle_id=vehicle_id,
                priority=priority,
                data_size=len(json.dumps(message_data)),
                estimated_processing_time=self._estimate_processing_time(fault_type, message_data),
                created_at=time.time()
            )
            
            task_data = {
                **task_info.__dict__,
                "message_data": message_data,
                "priority": priority.value
            }
            
            await self.redis.lpush(
                self.task_queue_key,
                json.dumps(task_data)
            )
            
            logger.debug(f"📋 任务已提交: {task_id} ({fault_type})")
            return task_id
            
        except Exception as e:
            logger.error(f"❌ 提交任务失败: {e}")
            raise
    
    async def _task_assignment_loop(self):
        """任务分配循环"""
        logger.info("📋 启动任务分配循环")
        
        while self.is_running:
            try:
                task_data = await self.redis.brpop(self.task_queue_key, timeout=1)
                if task_data:
                    _, task_json = task_data
                    await self._assign_task(json.loads(task_json))
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 任务分配循环异常: {e}")
                await asyncio.sleep(1)
    
    async def _assign_task(self, task_data: Dict[str, Any]):
        """分配单个任务"""
        try:
            start_time = time.time()
            
            task_info = TaskInfo(
                task_id=task_data["task_id"],
                fault_type=task_data["fault_type"],
                vehicle_id=task_data["vehicle_id"],
                priority=TaskPriority(task_data["priority"]),
                data_size=task_data["data_size"],
                estimated_processing_time=task_data["estimated_processing_time"],
                created_at=task_data["created_at"]
            )
            
            # 获取可用Worker
            available_workers = await self._get_available_workers()
            
            if not available_workers:
                await self.redis.lpush(self.task_queue_key, json.dumps(task_data))
                logger.warning(f"⚠️ 没有可用Worker，任务重新入队: {task_info.task_id}")
                return
            
            # 选择最佳Worker
            selected_worker = self.load_balancer.select_best_worker(
                available_workers, task_info
            )
            
            if not selected_worker:
                logger.error(f"❌ 无法为任务选择Worker: {task_info.task_id}")
                return
            
            # 发送任务到Redis Stream (兼容现有架构)
            await self._dispatch_to_redis_stream(task_data, selected_worker)
            
            # 更新统计
            assignment_time = time.time() - start_time
            self.stats["tasks_assigned"] += 1
            self.stats["average_assignment_time"] = (
                (self.stats["average_assignment_time"] * (self.stats["tasks_assigned"] - 1) + assignment_time) /
                self.stats["tasks_assigned"]
            )
            
            logger.debug(f"✅ 任务分配成功: {task_info.task_id} → {selected_worker.service_name}")
            
        except Exception as e:
            logger.error(f"❌ 任务分配失败: {e}")
    
    async def _dispatch_to_redis_stream(self, task_data: Dict[str, Any], 
                                      selected_worker: WorkerLoad):
        """将任务分发到Redis Stream (保持兼容性)"""
        try:
            # 构建与现有架构兼容的消息格式
            message = {
                "vehicle_id": task_data["vehicle_id"],
                "timestamp": datetime.now().isoformat(),
                "sensor_data": json.dumps(task_data["message_data"]),
                "metadata": json.dumps({
                    "coordinator_assigned": True,
                    "assigned_worker": selected_worker.worker_id,
                    "task_id": task_data["task_id"],
                    "priority": task_data["priority"]
                }),
                "data_type": "motor_sensor_data"
            }
            
            # 发布到原始数据流 (现有架构会自动处理)
            message_id = await self.redis.xadd(
                "motor_raw_data",  # 使用现有的Stream名称
                message,
                maxlen=50000
            )
            
            logger.debug(f"📤 任务已发送到Redis Stream: {message_id}")
            
        except Exception as e:
            logger.error(f"❌ 发送任务到Redis Stream失败: {e}")
            raise
    
    async def _get_available_workers(self) -> List[WorkerLoad]:
        """获取可用的Worker列表"""
        try:
            worker_services = await self.registry.get_services(
                service_type=ServiceType.WORKER,
                status=ServiceStatus.HEALTHY
            )
            
            worker_loads = []
            current_time = time.time()
            
            for service in worker_services:
                try:
                    load_data = await self.redis.hget(self.worker_loads_key, service.service_id)
                    
                    if load_data:
                        load_info = json.loads(load_data)
                        if current_time - load_info["last_updated"] < 60:
                            worker_load = WorkerLoad(
                                worker_id=service.service_id,
                                service_name=service.service_name,
                                host=service.host,
                                port=service.port,
                                capabilities=service.capabilities,
                                current_tasks=load_info.get("current_tasks", 0),
                                pending_messages=load_info.get("pending_messages", 0),
                                avg_processing_time=load_info.get("avg_processing_time", 100),
                                cpu_usage=load_info.get("cpu_usage", 50),
                                memory_usage=load_info.get("memory_usage", 50),
                                success_rate=load_info.get("success_rate", 0.95),
                                last_updated=load_info["last_updated"],
                                health_score=self._calculate_health_score(load_info)
                            )
                            worker_loads.append(worker_load)
                    else:
                        # 使用默认值
                        worker_load = WorkerLoad(
                            worker_id=service.service_id,
                            service_name=service.service_name,
                            host=service.host,
                            port=service.port,
                            capabilities=service.capabilities,
                            current_tasks=0,
                            pending_messages=0,
                            avg_processing_time=100,
                            cpu_usage=30,
                            memory_usage=40,
                            success_rate=1.0,
                            last_updated=current_time,
                            health_score=1.0
                        )
                        worker_loads.append(worker_load)
                
                except Exception as e:
                    logger.warning(f"⚠️ 获取Worker负载失败: {service.service_id} - {e}")
                    continue
            
            return worker_loads
            
        except Exception as e:
            logger.error(f"❌ 获取可用Worker失败: {e}")
            return []
    
    def _calculate_health_score(self, load_info: Dict[str, Any]) -> float:
        """计算Worker健康评分"""
        try:
            health_factors = {
                "cpu_ok": 1.0 if load_info.get("cpu_usage", 0) < 80 else 0.5,
                "memory_ok": 1.0 if load_info.get("memory_usage", 0) < 80 else 0.5,
                "success_rate": load_info.get("success_rate", 0.95),
                "response_time": 1.0 if load_info.get("avg_processing_time", 100) < 200 else 0.8
            }
            
            weights = {"cpu_ok": 0.25, "memory_ok": 0.25, "success_rate": 0.3, "response_time": 0.2}
            health_score = sum(health_factors[k] * weights[k] for k in weights)
            
            return max(0.0, min(1.0, health_score))
            
        except Exception as e:
            logger.error(f"❌ 计算健康评分失败: {e}")
            return 0.5
    
    def _estimate_processing_time(self, fault_type: str, message_data: Dict[str, Any]) -> float:
        """估算处理时间"""
        try:
            base_times = {
                "turn_fault": 50, "insulation": 40, "bearing": 60,
                "eccentricity": 45, "broken_bar": 55
            }
            
            base_time = base_times.get(fault_type, 50)
            data_size = len(json.dumps(message_data))
            size_factor = 1.0 + (data_size / 10000)
            
            return base_time * size_factor
            
        except Exception as e:
            return 100.0
    
    async def _worker_monitoring_loop(self):
        """Worker监控循环"""
        while self.is_running:
            try:
                await self._update_worker_loads()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Worker监控异常: {e}")
                await asyncio.sleep(5)
    
    async def _update_worker_loads(self):
        """更新Worker负载信息"""
        try:
            worker_services = await self.registry.get_services(
                service_type=ServiceType.WORKER,
                status=ServiceStatus.HEALTHY
            )
            
            for service in worker_services:
                try:
                    # 模拟负载数据，实际部署时需要Worker提供负载API
                    load_info = {
                        "worker_id": service.service_id,
                        "current_tasks": random.randint(0, 10),
                        "pending_messages": random.randint(0, 50),
                        "avg_processing_time": random.uniform(50, 200),
                        "cpu_usage": random.uniform(20, 80),
                        "memory_usage": random.uniform(30, 70),
                        "success_rate": random.uniform(0.90, 1.0),
                        "last_updated": time.time()
                    }
                    
                    await self.redis.hset(
                        self.worker_loads_key,
                        service.service_id,
                        json.dumps(load_info)
                    )
                    
                except Exception as e:
                    logger.warning(f"⚠️ 更新Worker负载失败: {service.service_id}")
                    
        except Exception as e:
            logger.error(f"❌ 更新Worker负载信息失败: {e}")
    
    async def _performance_monitoring_loop(self):
        """性能监控循环"""
        while self.is_running:
            try:
                await self._collect_performance_metrics()
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 性能监控异常: {e}")
                await asyncio.sleep(10)
    
    async def _collect_performance_metrics(self):
        """收集性能指标"""
        try:
            current_time = time.time()
            queue_length = await self.redis.llen(self.task_queue_key)
            
            worker_services = await self.registry.get_services(ServiceType.WORKER)
            healthy_workers = len([s for s in worker_services if s.status == ServiceStatus.HEALTHY])
            
            metrics = {
                "timestamp": current_time,
                "queue_length": queue_length,
                "total_workers": len(worker_services),
                "healthy_workers": healthy_workers,
                "tasks_assigned": self.stats["tasks_assigned"],
                "average_assignment_time": self.stats["average_assignment_time"]
            }
            
            await self.redis.xadd(
                "vtox:coordinator:metrics",
                {k: str(v) for k, v in metrics.items()},
                maxlen=1000
            )
            
        except Exception as e:
            logger.error(f"❌ 收集性能指标失败: {e}")
    
    async def _on_service_registered(self, service_data: Dict[str, Any]):
        """服务注册事件处理"""
        if service_data.get("service_type") == ServiceType.WORKER.value:
            logger.info(f"🆕 新Worker服务注册: {service_data['service_name']}")
    
    async def _on_service_deregistered(self, service_data: Dict[str, Any]):
        """服务注销事件处理"""
        if service_data.get("service_type") == ServiceType.WORKER.value:
            logger.info(f"👋 Worker服务注销: {service_data['service_name']}")
    
    async def get_coordinator_stats(self) -> Dict[str, Any]:
        """获取协调器统计信息"""
        try:
            current_time = time.time()
            uptime = current_time - self.stats["start_time"] if self.stats["start_time"] else 0
            
            # 获取当前队列状态
            queue_length = await self.redis.llen(self.task_queue_key)
            
            # 获取Worker状态
            worker_services = await self.registry.get_services(ServiceType.WORKER)
            healthy_workers = len([s for s in worker_services if s.status == ServiceStatus.HEALTHY])
            
            return {
                "coordinator_status": "running" if self.is_running else "stopped",
                "uptime_seconds": uptime,
                "tasks_assigned": self.stats["tasks_assigned"],
                "tasks_completed": self.stats["tasks_completed"],
                "tasks_failed": self.stats["tasks_failed"],
                "average_assignment_time": self.stats["average_assignment_time"],
                "current_queue_length": queue_length,
                "total_workers": len(worker_services),
                "healthy_workers": healthy_workers,
                "load_balance_strategy": self.load_balancer.strategy.value,
                "timestamp": current_time
            }
            
        except Exception as e:
            logger.error(f"❌ 获取协调器统计失败: {e}")
            return {"error": str(e)}


# 全局协调器实例
diagnosis_coordinator: Optional[DiagnosisCoordinator] = None

async def get_diagnosis_coordinator(redis_client: redis.Redis) -> DiagnosisCoordinator:
    """获取全局协调器实例"""
    global diagnosis_coordinator
    
    if diagnosis_coordinator is None:
        diagnosis_coordinator = DiagnosisCoordinator(redis_client)
        await diagnosis_coordinator.initialize()
    
    return diagnosis_coordinator